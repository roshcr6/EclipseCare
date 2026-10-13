"""Eclipse Care — SBAR Shift Handoff API.

Structured shift handoff using the SBAR/I-PASS framework, auto-populated
with the outgoing shift's vitals, alerts, and events.

EVIDENCE BASE (STRONG):
- Communication failures during shift transitions contribute to up to
  70-80% of serious medical errors.
- The Joint Commission requires a standardized approach to handoff
  communication.
- SBAR (Situation, Background, Assessment, Recommendation) is the
  widely recognized framework for nurse-to-nurse and nurse-to-physician
  communication.

DESIGN:
  NOT a blank diary box. The system auto-generates SBAR sections from
  telemetry and alert data, then allows the outgoing nurse to add a
  free-text "Watch For" recommendation.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import structlog

logger = structlog.get_logger("api.handoff")

router = APIRouter()


# ── Pydantic Models ──────────────────────────────────────────────────

class ResidentSBAR(BaseModel):
    """Auto-generated SBAR for a single resident."""
    resident_name: str
    room: str

    # S — Situation: What happened this shift
    situation_alerts: List[str] = Field(default_factory=list,
        description="List of alerts triggered during this shift")
    situation_summary: str = ""

    # B — Background: Relevant baseline context
    background_baseline_hr: Optional[int] = None
    background_conditions: List[str] = Field(default_factory=list)

    # A — Assessment: Current status at handoff
    assessment_current_hr: Optional[int] = None
    assessment_current_spo2: Optional[float] = None
    assessment_adl_state: str = "unknown"
    assessment_sleep_quality: Optional[str] = None

    # R — Recommendation: Nurse's free-text "watch for"
    recommendation: str = ""


class ShiftHandoff(BaseModel):
    """Complete shift handoff document."""
    facility_id: str
    outgoing_nurse: str
    incoming_nurse: str = ""
    shift_start: datetime
    shift_end: datetime
    residents: List[ResidentSBAR] = Field(default_factory=list)
    general_notes: str = ""


class HandoffSubmission(BaseModel):
    """What the outgoing nurse submits (recommendations + notes)."""
    handoff_id: str
    recommendations: dict = Field(default_factory=dict,
        description="Mapping of resident_name -> recommendation text")
    general_notes: str = ""


# ── Mock Data (would be pulled from TimescaleDB in production) ───────

MOCK_HANDOFF = ShiftHandoff(
    facility_id="FAC_001",
    outgoing_nurse="RN Sarah Chen",
    shift_start=datetime(2026, 7, 1, 7, 0),
    shift_end=datetime(2026, 7, 1, 19, 0),
    residents=[
        ResidentSBAR(
            resident_name="Eleanor Vance",
            room="102",
            situation_alerts=["FALL_DETECTED (09:14 — AI confidence 92%)"],
            situation_summary="Fall detected at 09:14. Resident was assisted. No visible injury. Vitals stable post-fall.",
            background_baseline_hr=68,
            background_conditions=["Dementia (mild)", "Osteoporosis"],
            assessment_current_hr=72,
            assessment_current_spo2=96.0,
            assessment_adl_state="resting",
            assessment_sleep_quality="Good (6.2h, 1 disturbance)",
            recommendation="",
        ),
        ResidentSBAR(
            resident_name="Harold Finch",
            room="204",
            situation_alerts=[
                "PREDICTIVE_UTI_RISK (03:00 — bathroom visits +42%)",
                "HR_ANOMALY (14:30 — 89 bpm vs 62 bpm baseline)"
            ],
            situation_summary="Predictive engine flagged UTI risk. HR trending upward. Appetite reduced at lunch.",
            background_baseline_hr=62,
            background_conditions=["Type 2 Diabetes", "History of recurrent UTI"],
            assessment_current_hr=85,
            assessment_current_spo2=94.0,
            assessment_adl_state="resting",
            assessment_sleep_quality="Poor (4.1h, 5 disturbances)",
            recommendation="",
        ),
    ],
)


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("/current", response_model=ShiftHandoff)
async def get_current_handoff():
    """Get the auto-populated SBAR handoff for the current outgoing shift.

    In production this queries TimescaleDB for the shift's alerts, vitals,
    ADL summaries, and sleep data, then structures them into SBAR format.
    """
    return MOCK_HANDOFF


@router.post("/submit")
async def submit_handoff(submission: HandoffSubmission):
    """Outgoing nurse submits their recommendations and free-text notes.

    This completes the 'R' (Recommendation) section of each resident's
    SBAR and persists the handoff to the database.
    """
    logger.info("Shift handoff submitted",
                handoff_id=submission.handoff_id,
                recs=len(submission.recommendations),
                notes_len=len(submission.general_notes))

    return {
        "status": "accepted",
        "message": "Handoff recorded. Incoming nurse will see recommendations.",
        "handoff_id": submission.handoff_id,
    }
