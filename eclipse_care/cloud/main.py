"""Eclipse Care — Cloud Backend API.

FastAPI application that serves as the central hub for the Eclipse Care platform.
Provides:
- Ingestion endpoints for Gateways to push telemetry and alerts.
- FHIR Facade endpoints for EHR (Epic/Cerner) integration.
- LLM Hybrid Rule Engine hooks for intelligent alert routing.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .engine.predictive_analytics import PredictiveEngine

logger = structlog.get_logger("cloud.main")

# Database connection pool
db_pool: asyncpg.Pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown resources."""
    global db_pool
    scheduler = AsyncIOScheduler()
    engine = PredictiveEngine()
    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://eclipse_admin:secure_dev_password_123@localhost:5432/eclipse_care")
    
    try:
        # Note: In production with asyncpg, standard DSN is used
        db_dsn = db_url.replace("postgresql+asyncpg://", "postgresql://")
        db_pool = await asyncpg.create_pool(dsn=db_dsn)
        logger.info("Database connection pool established")
        
        # Schedule the Predictive Engine
        scheduler.add_job(engine.run_daily_predictions, 'cron', hour=3, minute=0)
        scheduler.start()
        logger.info("Predictive Engine APScheduler started (Next run at 03:00 AM)")
    except Exception as e:
        logger.error("Failed to connect to database or start scheduler", error=str(e))
        
    yield
    
    if db_pool:
        await db_pool.close()
        logger.info("Database connection pool closed")
    scheduler.shutdown()
    logger.info("APScheduler stopped")

app = FastAPI(
    title="Eclipse Care Cloud API",
    description="HIPAA-compliant backend for elderly care wearable monitoring",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to dashboard/EHR domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db() -> asyncpg.Pool:
    """Dependency to inject DB pool into routes."""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")
    return db_pool

@app.get("/healthz")
async def health_check():
    """Liveness probe."""
    return {"status": "healthy"}

from .api.ingest import router as ingest_router
from .api.fhir import router as fhir_router
from .api.handoff import router as handoff_router
from .api.emar import router as emar_router
app.include_router(ingest_router, prefix="/v1/ingest", tags=["Ingestion"])
app.include_router(fhir_router, prefix="/fhir", tags=["FHIR Integration"])
app.include_router(handoff_router, prefix="/v1/handoff", tags=["SBAR Shift Handoff"])
app.include_router(emar_router, prefix="/v1/emar", tags=["eMAR Medication"])

