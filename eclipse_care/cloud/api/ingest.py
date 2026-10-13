"""Eclipse Care — Gateway Ingestion API.

Endpoints for Edge Gateways to push bulk telemetry and critical alerts.
Optimized for high-throughput inserts into TimescaleDB.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime
import asyncpg
import structlog

from ..engine.alert_evaluator import AlertEvaluator
from ..main import get_db

logger = structlog.get_logger("api.ingest")
router = APIRouter()
evaluator = AlertEvaluator()

# --- Pydantic Models ---

class ReadingPayload(BaseModel):
    device_id: str
    type: str
    ts: float
    value: Any
    meta: Dict[str, Any] = {}

class BatchIngestPayload(BaseModel):
    gateway_id: str
    facility_id: str
    readings: List[ReadingPayload]

class AlertPayload(BaseModel):
    device_id: str
    gateway_id: str
    type: str
    severity: str
    message: str
    timestamp: float


# --- Endpoints ---

@router.post("/readings", status_code=201)
async def ingest_readings(payload: BatchIngestPayload, db: asyncpg.Pool = Depends(get_db)):
    """Bulk ingest telemetry from a gateway into TimescaleDB hypertables."""
    if not payload.readings:
        return {"status": "ok", "inserted": 0}

    # Extract heart rate readings specifically (most common vital)
    hr_records = []
    for r in payload.readings:
        if r.type == "heart_rate":
            # Convert unix timestamp to postgres timestamptz
            dt = datetime.fromtimestamp(r.ts)
            hr_records.append((dt, r.device_id, payload.gateway_id, int(r.value), 100))
            
    if hr_records:
        try:
            # High-performance bulk insert using asyncpg executemany
            async with db.acquire() as conn:
                await conn.executemany(
                    "INSERT INTO telemetry.heart_rate (time, device_id, gateway_id, bpm, confidence) VALUES ($1, $2, $3, $4, $5)",
                    hr_records
                )
        except Exception as e:
            logger.error("Failed to insert telemetry batch", error=str(e))
            raise HTTPException(status_code=500, detail="Database insertion failed")

    return {"status": "ok", "inserted": len(hr_records)}


@router.post("/alerts", status_code=201)
async def ingest_alerts(alerts: List[AlertPayload], background_tasks: BackgroundTasks, db: asyncpg.Pool = Depends(get_db)):
    """Ingest alerts from a gateway. Triggers the LLM Hybrid Engine."""
    if not alerts:
        return {"status": "ok"}
        
    for alert in alerts:
        # 1. Run the LLM Evaluator to check if we should suppress this alert
        context = {
            "time_of_day": datetime.fromtimestamp(alert.timestamp).strftime("%H:%M:%S"),
            # In a real system, we would query the database here for recent activity/location
            "recent_activity": "Unknown" 
        }
        
        should_escalate, reasoning = await evaluator.evaluate(alert.dict(), context)
        
        # 2. Store the alert with the LLM's reasoning
        dt = datetime.fromtimestamp(alert.timestamp)
        try:
            async with db.acquire() as conn:
                await conn.execute("""
                    INSERT INTO incidents.alerts 
                    (time, device_id, alert_type, severity, message, llm_suppressed, llm_reasoning)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, 
                dt, alert.device_id, alert.type, alert.severity, alert.message, not should_escalate, reasoning)
        except Exception as e:
            logger.error("Failed to store alert", error=str(e))
            
        # 3. If escalate is True, we would trigger a background task to push to caregiver devices/pagers
        if should_escalate:
            logger.warning("ESCALATING ALERT TO STAFF", alert_type=alert.type, device=alert.device_id)
            # background_tasks.add_task(send_push_notification, alert)
        else:
            logger.info("Alert suppressed by LLM", alert_type=alert.type, reason=reasoning)

    return {"status": "ok", "processed": len(alerts)}
