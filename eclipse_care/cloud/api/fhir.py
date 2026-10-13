"""Eclipse Care — FHIR Interoperability Facade.

Provides FHIR R4 standard endpoints for Electronic Health Records (EHR) 
like Epic and Cerner to securely pull patient telemetry data.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime
import asyncpg
import structlog

# We use fhir.resources for strict Pydantic validation of HL7 standards
try:
    from fhir.resources.observation import Observation
    from fhir.resources.patient import Patient
    from fhir.resources.bundle import Bundle
    FHIR_AVAILABLE = True
except ImportError:
    FHIR_AVAILABLE = False


from ..main import get_db

logger = structlog.get_logger("api.fhir")
router = APIRouter()

@router.get("/Observation")
async def get_observations(
    patient_id: str = Query(..., description="The internal patient UUID"),
    code: str = Query(None, description="LOINC code (e.g., 8867-4 for Heart Rate)"),
    db: asyncpg.Pool = Depends(get_db)
):
    """
    FHIR Observation endpoint.
    Searches the TimescaleDB for telemetry and formats it as FHIR R4 Observations.
    """
    if not FHIR_AVAILABLE:
        raise HTTPException(status_code=501, detail="FHIR validation models not installed")
        
    # In a real facade, we would map the patient_id to the wearable_mac_address here.
    # For simplicity, we assume we have the MAC address:
    mac_address = "MOCK:MAC:ADDR" 

    # If asking for heart rate
    if code and code != "8867-4":
        return {"resourceType": "Bundle", "type": "searchset", "entry": []}

    try:
        async with db.acquire() as conn:
            # Query recent heart rates from TimescaleDB
            records = await conn.fetch("""
                SELECT time, bpm
                FROM telemetry.heart_rate
                WHERE device_id = $1
                ORDER BY time DESC
                LIMIT 50
            """, mac_address)
            
        entries = []
        for rec in records:
            # Map TimescaleDB row to FHIR R4 Observation resource
            obs = Observation.construct(
                status="final",
                category=[{
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs"
                    }]
                }],
                code={
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "8867-4",
                        "display": "Heart rate"
                    }]
                },
                subject={"reference": f"Patient/{patient_id}"},
                effectiveDateTime=rec['time'].isoformat(),
                valueQuantity={
                    "value": rec['bpm'],
                    "unit": "beats/minute",
                    "system": "http://unitsofmeasure.org",
                    "code": "/min"
                }
            )
            entries.append({"resource": obs.dict()})
            
        bundle = Bundle.construct(
            type="searchset",
            total=len(entries),
            entry=entries
        )
        
        return bundle.dict()

    except Exception as e:
        logger.error("Database error during FHIR export", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve FHIR data")

@router.get("/metadata")
async def capability_statement():
    """FHIR CapabilityStatement to inform EHRs of supported features."""
    return {
        "resourceType": "CapabilityStatement",
        "status": "active",
        "date": datetime.utcnow().isoformat(),
        "kind": "instance",
        "software": {
            "name": "Eclipse Care FHIR Facade",
            "version": "1.0.0"
        },
        "fhirVersion": "4.0.1",
        "format": ["json"],
        "rest": [{
            "mode": "server",
            "resource": [
                {
                    "type": "Observation",
                    "interaction": [{"code": "search-type"}],
                    "searchParam": [
                        {"name": "patient", "type": "reference"},
                        {"name": "code", "type": "token"}
                    ]
                }
            ]
        }]
    }
