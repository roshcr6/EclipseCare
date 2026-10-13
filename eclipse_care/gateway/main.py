"""Eclipse Care — Gateway Entry Point.

This script runs on the Raspberry Pi / Edge device.
It orchestrates:
1. Local SQLite Database initialization.
2. Cloud Sync Engine startup.
3. Edge Processor (Alert generation).
4. BLE Scanner (Device discovery & connection).
"""

import asyncio
import signal
import sys
import argparse

import structlog
from .config import GatewayConfig
from .store.database import LocalStore
from .sync.uploader import SyncEngine
from .edge.processor import EdgeProcessor
from .ble.scanner import BLEScanner

# Setup structured logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ]
)
logger = structlog.get_logger("gateway.main")


class GatewayApp:
    def __init__(self, target_mac: str | None = None):
        self.config = GatewayConfig()
        self.store = LocalStore(self.config)
        self.sync_engine = SyncEngine(self.config, self.store)
        
        # Edge processor handles the readings and generates alerts
        self.processor = EdgeProcessor(self.config, alert_callback=self._handle_alert)
        
        # BLE Scanner connects to the device and streams readings to the edge processor
        self.scanner = BLEScanner(self.config, target_mac=target_mac)
        self.scanner.on_reading = self._handle_reading
        
        self._running = False

    async def _handle_reading(self, reading):
        """Callback from BLE Scanner. Pass to edge processor, then save to DB."""
        # 1. Evaluate for immediate edge alerts (falls, vitals)
        self.processor.process_reading(reading)
        
        # 2. Persist to local store for background cloud sync
        await self.store.save_reading(reading)

    def _handle_alert(self, alert_data: dict):
        """Callback from Edge Processor when a critical condition is met."""
        # We need to run the async save in the background since this might be called synchronously
        asyncio.create_task(self.store.save_alert(alert_data))
        
        # Attempt immediate cloud sync for emergencies
        if alert_data.get("severity") in ("critical", "emergency"):
            asyncio.create_task(self.sync_engine.trigger_immediate_alert_sync(alert_data))

    async def _periodic_checks(self):
        """Run periodic background tasks on the gateway."""
        while self._running:
            try:
                if self.scanner.is_connected and self.scanner.client:
                    # Check for no-movement timeouts
                    self.processor.check_timeouts(self.scanner.client.address)
                
                # Daily database maintenance
                await self.store.prune_synced_data(days_old=7)
            except Exception as e:
                logger.error("Periodic check failed", error=str(e))
                
            await asyncio.sleep(60)  # Check every minute

    async def _run_ble_loop(self):
        """Main connection loop. Reconnects if connection drops."""
        while self._running:
            if not self.scanner.is_connected:
                success = await self.scanner.scan_and_connect()
                if success:
                    logger.info("Gateway monitoring active")
                    # Wait until disconnected
                    await self.scanner.wait_until_disconnected()
                else:
                    logger.debug("Scan completed, no device found. Retrying in 10s...")
                    await asyncio.sleep(10)
            else:
                await asyncio.sleep(1)

    async def run(self):
        """Start the gateway."""
        logger.info("Starting Eclipse Care Gateway...", 
                    gateway_id=self.config.gateway_id, 
                    facility=self.config.facility_id)
        
        self._running = True
        
        # Init DB
        await self.store.init_db()
        
        # Start Sync Engine
        await self.sync_engine.start()
        
        # Start periodic checks
        asyncio.create_task(self._periodic_checks())
        
        # Start BLE connection loop
        await self._run_ble_loop()

    async def shutdown(self):
        """Gracefully stop the gateway."""
        logger.info("Shutting down gateway...")
        self._running = False
        
        await self.scanner.disconnect()
        await self.sync_engine.stop()
        await self.store.close()
        
        logger.info("Shutdown complete")


async def main():
    parser = argparse.ArgumentParser(description="Eclipse Care Gateway")
    parser.add_argument("--mac", type=str, help="Target wearable MAC address (optional)")
    args = parser.parse_args()

    app = GatewayApp(target_mac=args.mac)
    
    # Handle shutdown signals
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(app.shutdown()))
        
    try:
        await app.run()
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
