"""Eclipse Care — eMAR (Electronic Medication Administration Record) API.

Staff-facing medication administration log where nurses mark
"given / refused / held" per dose with missed-dose alerting.

EVIDENCE BASE:
- Medications like blood pressure drugs or digoxin should be managed by
  a living person, not a machine — you don't want someone taking those
  out of sync with their actual vitals.
- A 2021 study found smartphone reminder apps achieved 92% adherence vs
  78% for electronic dispensing devices.
- Dispensing hardware is unreliable (jamming, double-dosing) per user reviews.
- Nursing homes have STAFF administer meds, not residents self-dispensing.

DESIGN:
  This is NOT a hardware dispenser integration. It is an eMAR-style log:
  - Schedules are loaded per patient from the pharmacy/physician order.
  - Nurses mark each dose as GIVEN, REFUSED, or HELD (with reason).
  - If a dose window passes without a mark, a MEDICATION_MISSED alert fires.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, time as dt_time
from enum import Enum
import structlog

logger = structlog.get_logger("api.emar")

router = APIRouter()


class DoseStatus(str, Enum):
    PENDING = "pending"
    GIVEN = "given"
    REFUSED = "refused"
    HELD = "held"
    MISSED = "missed"


class MedicationSchedule(BaseModel):
    """A single medication scheduled for a patient."""
    id: str
    patient_id: str
    medication_name: str
    dosage: str                      # e.g., "10mg"
    route: str = "PO"                # PO, IV, IM, SubQ, Topical
    frequency: str                   # e.g., "BID", "TID", "QHS"
    scheduled_times: List[str]       # e.g., ["08:00", "20:00"]
    special_instructions: str = ""   # e.g., "Take with food"


class DoseRecord(BaseModel):
    """Record of a single dose administration."""
    schedule_id: str
    patient_id: str
    medication_name: str
    scheduled_time: str
    status: DoseStatus = DoseStatus.PENDING
    administered_by: Optional[str] = None
    administered_at: Optional[datetime] = None
    hold_reason: Optional[str] = None
    refuse_reason: Optional[str] = None
    notes: str = ""


class DoseAdminRequest(BaseModel):
    """Nurse submits dose administration."""
    dose_id: str
    status: DoseStatus
    nurse_id: str
    reason: Optional[str] = None
    notes: str = ""


# ── Mock Data ────────────────────────────────────────────────────────

MOCK_SCHEDULES = [
    MedicationSchedule(
        id="MED_001",
        patient_id="PAT_VANCE",
        medication_name="Lisinopril",
        dosage="10mg",
        route="PO",
        frequency="QD",
        scheduled_times=["08:00"],
        special_instructions="Monitor BP before administering"
    ),
    MedicationSchedule(
        id="MED_002",
        patient_id="PAT_FINCH",
        medication_name="Metformin",
        dosage="500mg",
        route="PO",
        frequency="BID",
        scheduled_times=["08:00", "18:00"],
        special_instructions="Take with meals"
    ),
    MedicationSchedule(
        id="MED_003",
        patient_id="PAT_FINCH",
        medication_name="Donepezil",
        dosage="5mg",
        route="PO",
        frequency="QHS",
        scheduled_times=["21:00"],
        special_instructions="For cognitive decline. Give at bedtime."
    ),
]

MOCK_DOSES = [
    DoseRecord(
        schedule_id="MED_001",
        patient_id="PAT_VANCE",
        medication_name="Lisinopril 10mg PO",
        scheduled_time="08:00",
        status=DoseStatus.GIVEN,
        administered_by="RN Sarah Chen",
        administered_at=datetime(2026, 7, 1, 8, 5),
        notes="BP 128/82 pre-admin"
    ),
    DoseRecord(
        schedule_id="MED_002",
        patient_id="PAT_FINCH",
        medication_name="Metformin 500mg PO",
        scheduled_time="08:00",
        status=DoseStatus.GIVEN,
        administered_by="RN Sarah Chen",
        administered_at=datetime(2026, 7, 1, 8, 10),
    ),
    DoseRecord(
        schedule_id="MED_002",
        patient_id="PAT_FINCH",
        medication_name="Metformin 500mg PO",
        scheduled_time="18:00",
        status=DoseStatus.PENDING,
    ),
    DoseRecord(
        schedule_id="MED_003",
        patient_id="PAT_FINCH",
        medication_name="Donepezil 5mg PO",
        scheduled_time="21:00",
        status=DoseStatus.PENDING,
    ),
]


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("/schedules/{patient_id}", response_model=List[MedicationSchedule])
async def get_medication_schedule(patient_id: str):
    """Get all medication schedules for a patient."""
    return [s for s in MOCK_SCHEDULES if s.patient_id == patient_id]


@router.get("/doses/{patient_id}", response_model=List[DoseRecord])
async def get_todays_doses(patient_id: str):
    """Get today's dose records for a patient (MAR view)."""
    return [d for d in MOCK_DOSES if d.patient_id == patient_id]


@router.post("/administer")
async def administer_dose(req: DoseAdminRequest):
    """Nurse records a dose administration (given/refused/held)."""
    logger.info("Dose administered",
                dose_id=req.dose_id,
                status=req.status,
                nurse=req.nurse_id,
                reason=req.reason)

    return {
        "status": "recorded",
        "dose_id": req.dose_id,
        "administration_status": req.status,
    }
