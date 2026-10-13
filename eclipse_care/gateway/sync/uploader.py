"""Eclipse Care — Gateway Sync Engine.

Synchronizes local offline-first SQLite database with the Cloud backend via REST.
"""

import aiohttp
import asyncio
import json
from ..store.database import LocalStore
from ..config import GatewayConfig

import structlog
logger = structlog.get_logger("sync.uploader")


class SyncEngine:
    """Handles background synchronization of local data to the cloud."""
    
    def __init__(self, config: GatewayConfig, store: LocalStore):
        self.config = config
        self.store = store
        self._running = False
        self._task = None

    async def start(self):
        """Start the background sync loop."""
        self._running = True
        self._task = asyncio.create_task(self._sync_loop())
        logger.info("Sync engine started", interval=self.config.sync_interval_sec)

    async def stop(self):
        """Stop the background sync loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Sync engine stopped")

    async def trigger_immediate_alert_sync(self, alert_data: dict):
        """Try to send a critical alert immediately, bypassing the polling interval."""
        try:
            headers = {}
            if self.config.cloud_api_key:
                headers["Authorization"] = f"Bearer {self.config.cloud_api_key}"
                
            async with aiohttp.ClientSession() as session:
                url = f"{self.config.cloud_url}/v1/ingest/alerts"
                async with session.post(url, json=[alert_data], headers=headers, timeout=5) as response:
                    if response.status in (200, 201):
                        logger.info("Immediate alert sync successful")
                        return True
        except Exception as e:
            logger.warning("Immediate alert sync failed (will retry via local store loop)", error=str(e))
        return False

    async def _sync_loop(self):
        """Periodic loop pulling from local SQLite and pushing to Cloud."""
        while self._running:
            try:
                await self._sync_batch()
            except Exception as e:
                logger.error("Sync batch failed", error=str(e))
                
            # Sleep until next interval, but check self._running frequently
            for _ in range(self.config.sync_interval_sec):
                if not self._running:
                    break
                await asyncio.sleep(1)

    async def _sync_batch(self):
        headers = {"Content-Type": "application/json"}
        if self.config.cloud_api_key:
            headers["Authorization"] = f"Bearer {self.config.cloud_api_key}"
            
        async with aiohttp.ClientSession(headers=headers) as session:
            
            # 1. Sync Alerts first (Priority)
            alerts = await self.store.get_unsynced_alerts(limit=50)
            if alerts:
                logger.debug("Syncing alerts to cloud", count=len(alerts))
                # The DB returns rows as dicts. 
                # Need to prep them for the API.
                payload = []
                for a in alerts:
                    payload.append({
                        "device_id": a["device_id"],
                        "gateway_id": self.config.gateway_id,
                        "type": a["alert_type"],
                        "severity": a["severity"],
                        "message": a["message"],
                        "timestamp": a["timestamp"]
                    })
                
                url = f"{self.config.cloud_url}/v1/ingest/alerts"
                async with session.post(url, json=payload, timeout=10) as response:
                    if response.status in (200, 201):
                        alert_ids = [a["id"] for a in alerts]
                        await self.store.mark_alerts_synced(alert_ids)
                        logger.info("Synced alerts", count=len(alert_ids))
                    else:
                        logger.error("Failed to sync alerts", status=response.status, text=await response.text())

            # 2. Sync Readings
            readings = await self.store.get_unsynced_readings(limit=500)
            if readings:
                logger.debug("Syncing readings to cloud", count=len(readings))
                payload = []
                for r in readings:
                    payload.append({
                        "device_id": r["device_id"],
                        "type": r["reading_type"],
                        "ts": r["timestamp"],
                        "value": json.loads(r["value_json"]),
                        "meta": json.loads(r["metadata_json"]) if r["metadata_json"] else {}
                    })
                
                url = f"{self.config.cloud_url}/v1/ingest/readings"
                
                batch_payload = {
                    "gateway_id": self.config.gateway_id,
                    "facility_id": self.config.facility_id,
                    "readings": payload
                }
                
                async with session.post(url, json=batch_payload, timeout=30) as response:
                    if response.status in (200, 201):
                        reading_ids = [r["id"] for r in readings]
                        await self.store.mark_readings_synced(reading_ids)
                        logger.info("Synced readings", count=len(reading_ids))
                    else:
                        logger.error("Failed to sync readings", status=response.status, text=await response.text())
