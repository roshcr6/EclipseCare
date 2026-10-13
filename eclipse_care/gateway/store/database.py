"""Eclipse Care — Gateway Local Storage (Offline-First).

Stores sensor readings and alerts locally using aiosqlite.
When the internet drops, the gateway continues functioning, evaluating rules,
and storing data. The sync engine pulls from here when connectivity is restored.
"""

import json
import asyncio
import aiosqlite
from pathlib import Path

from ..ble.decoder import SensorReading, ReadingType
from ..config import GatewayConfig

import structlog
logger = structlog.get_logger("store.database")


class LocalStore:
    """Async SQLite local store for the gateway."""

    def __init__(self, config: GatewayConfig):
        self.db_path = config.db_path
        self._db: aiosqlite.Connection | None = None

    async def init_db(self):
        """Initialize database schema."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        
        # Readings Table (high volume, simple values)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                reading_type TEXT NOT NULL,
                timestamp REAL NOT NULL,
                value_json TEXT NOT NULL,
                metadata_json TEXT,
                synced BOOLEAN DEFAULT 0
            )
        """)
        
        # Alerts Table (low volume, critical)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp REAL NOT NULL,
                synced BOOLEAN DEFAULT 0
            )
        """)
        
        # Indexes for fast sync queries
        await self._db.execute("CREATE INDEX IF NOT EXISTS idx_readings_sync ON sensor_readings(synced, timestamp)")
        await self._db.execute("CREATE INDEX IF NOT EXISTS idx_alerts_sync ON alerts(synced, timestamp)")
        
        await self._db.commit()
        logger.info("Local database initialized", path=self.db_path)

    async def save_reading(self, reading: SensorReading):
        """Save a sensor reading to local storage."""
        if not self._db:
            return
            
        try:
            # We don't save raw IMU arrays to DB continuously (too much data).
            # Fall alerts trigger off the stream, but we don't need gigabytes of raw accel data in SQLite.
            # In a real system, we'd log them to rolling binary files if needed for research.
            if reading.reading_type in (ReadingType.ACCELEROMETER, ReadingType.GYROSCOPE):
                return
                
            await self._db.execute(
                "INSERT INTO sensor_readings (device_id, reading_type, timestamp, value_json, metadata_json) VALUES (?, ?, ?, ?, ?)",
                (
                    reading.device_id,
                    reading.reading_type.value,
                    reading.timestamp,
                    json.dumps(reading.value),
                    json.dumps(reading.metadata)
                )
            )
            await self._db.commit()
        except Exception as e:
            logger.error("Failed to save reading", error=str(e))

    async def save_alert(self, alert_data: dict):
        """Save a generated alert to local storage."""
        if not self._db:
            return
            
        try:
            await self._db.execute(
                "INSERT INTO alerts (device_id, alert_type, severity, message, timestamp) VALUES (?, ?, ?, ?, ?)",
                (
                    alert_data["device_id"],
                    alert_data["type"],
                    alert_data["severity"],
                    alert_data["message"],
                    alert_data["timestamp"]
                )
            )
            await self._db.commit()
        except Exception as e:
            logger.error("Failed to save alert", error=str(e))

    async def get_unsynced_readings(self, limit=1000) -> list[dict]:
        """Fetch readings that haven't been synced to the cloud yet."""
        if not self._db:
            return []
            
        async with self._db.execute(
            "SELECT * FROM sensor_readings WHERE synced = 0 ORDER BY timestamp ASC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_unsynced_alerts(self, limit=100) -> list[dict]:
        """Fetch alerts that haven't been synced to the cloud yet."""
        if not self._db:
            return []
            
        async with self._db.execute(
            "SELECT * FROM alerts WHERE synced = 0 ORDER BY timestamp ASC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def mark_readings_synced(self, ids: list[int]):
        """Mark readings as successfully synced."""
        if not self._db or not ids:
            return
            
        # SQLite IN clause limits, so chunk if necessary (keep simple here)
        placeholders = ",".join("?" * len(ids))
        await self._db.execute(f"UPDATE sensor_readings SET synced = 1 WHERE id IN ({placeholders})", ids)
        await self._db.commit()

    async def mark_alerts_synced(self, ids: list[int]):
        """Mark alerts as successfully synced."""
        if not self._db or not ids:
            return
            
        placeholders = ",".join("?" * len(ids))
        await self._db.execute(f"UPDATE alerts SET synced = 1 WHERE id IN ({placeholders})", ids)
        await self._db.commit()

    async def prune_synced_data(self, days_old=7):
        """Delete old synced data to save space on the Raspberry Pi."""
        if not self._db:
            return
            
        cutoff = time.time() - (days_old * 86400)
        await self._db.execute("DELETE FROM sensor_readings WHERE synced = 1 AND timestamp < ?", (cutoff,))
        await self._db.execute("DELETE FROM alerts WHERE synced = 1 AND timestamp < ?", (cutoff,))
        await self._db.commit()

    async def close(self):
        if self._db:
            await self._db.close()
