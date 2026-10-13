"""Eclipse Care — Early Infection Detection (Cloud Predictive Engine).

Detects early signs of UTI, sepsis, and other infections using personal
baseline deviation, NOT population-wide vital thresholds.

EVIDENCE BASE:
- Signs/symptoms of infection in frail elderly are ATYPICAL — one study
  found mental status changes were the sole documented symptom in 36% of
  suspected UTI episodes.
- The EDIS (Early Detection of Infection Scale) instrument identified
  these signals as relevant for infection detection in frail elderly
  (published research, not validated on THIS system):
    * Body temperature changes
    * Changes in feeding behavior
    * Changes in emotion
    * Disengaged gaze / decreased eye reactivity
    * Changes in movement patterns
  Built on the everyday nursing observation: "he/she is not as usual."
- Some commercial products (e.g. ADL-tracking wearables) claim to detect
  UTIs days in advance using ADL patterns. [Assumption — specific vendor
  accuracy figures are unverified by us.]

APPROACH:
  Track deviation from each resident's PERSONAL baseline across:
  1. Nocturnal bathroom visits (via Geofence RSSI)
  2. Activity level (from ADL classifier daily summaries)
  3. Sleep disturbances (from Sleep Tracker nightly summaries)
  4. Resting heart rate trend (subtle elevation)

  Each signal is individually weak but combined they form a robust
  early warning when multiple signals deviate simultaneously.
  Uses a weighted composite score, NOT a black-box ML model.
"""

import os
import structlog
from typing import Dict, Any, List, Optional

logger = structlog.get_logger("engine.infection_detector")


class InfectionDetector:
    """Detects early signs of infection using personal baseline deviation.

    Each resident has their own baseline built over 14 days. The detector
    fires when multiple behavioral signals deviate simultaneously.
    """

    # Weights for composite scoring (sum = 1.0)
    WEIGHTS = {
        "bathroom_visits": 0.30,   # Strongest single predictor for UTI
        "activity_decline": 0.25,  # "Not as usual" — EDIS literature-informed
        "sleep_disruption": 0.20,  # Nighttime restlessness
        "hr_elevation": 0.15,      # Subtle resting HR rise
        "feeding_decline": 0.10,   # Reduced meal engagement
    }

    # Thresholds
    COMPOSITE_WARNING_THRESHOLD = 0.45   # Moderate concern
    COMPOSITE_CRITICAL_THRESHOLD = 0.70  # High confidence infection risk

    def __init__(self):
        pass

    def evaluate_resident(self, resident_id: str,
                          baseline: Dict[str, float],
                          current: Dict[str, float]) -> Dict[str, Any]:
        """Evaluate a single resident for infection risk.

        Args:
            resident_id: Patient identifier
            baseline: 14-day rolling averages per signal
            current: Last 3-day averages per signal

        Returns:
            Dict with risk_score, risk_level, contributing_factors
        """
        scores = {}
        factors = []

        # 1. Nocturnal Bathroom Visits
        bl_bath = baseline.get("nocturnal_bathroom_visits", 0)
        cur_bath = current.get("nocturnal_bathroom_visits", 0)
        if bl_bath > 0:
            pct_change = (cur_bath - bl_bath) / bl_bath
            if pct_change > 0.30:
                scores["bathroom_visits"] = min(1.0, pct_change)
                factors.append(f"Nocturnal bathroom visits +{pct_change*100:.0f}%")
            else:
                scores["bathroom_visits"] = 0.0
        else:
            scores["bathroom_visits"] = 0.0

        # 2. Activity Level Decline
        bl_active = baseline.get("daily_active_minutes", 1)
        cur_active = current.get("daily_active_minutes", 0)
        if bl_active > 0:
            decline = (bl_active - cur_active) / bl_active
            if decline > 0.20:
                scores["activity_decline"] = min(1.0, decline)
                factors.append(f"Activity declined {decline*100:.0f}%")
            else:
                scores["activity_decline"] = 0.0
        else:
            scores["activity_decline"] = 0.0

        # 3. Sleep Disruption
        bl_disturb = baseline.get("sleep_disturbances", 0)
        cur_disturb = current.get("sleep_disturbances", 0)
        if bl_disturb > 0:
            increase = (cur_disturb - bl_disturb) / bl_disturb
            if increase > 0.25:
                scores["sleep_disruption"] = min(1.0, increase)
                factors.append(f"Sleep disturbances +{increase*100:.0f}%")
            else:
                scores["sleep_disruption"] = 0.0
        elif cur_disturb > 3:  # No baseline but absolute count is high
            scores["sleep_disruption"] = 0.5
            factors.append(f"Sleep disturbances elevated ({cur_disturb}/night)")
        else:
            scores["sleep_disruption"] = 0.0

        # 4. Resting HR Elevation
        bl_hr = baseline.get("resting_hr", 0)
        cur_hr = current.get("resting_hr", 0)
        if bl_hr > 0:
            hr_rise = cur_hr - bl_hr
            if hr_rise > 5:  # >5 bpm above personal baseline
                scores["hr_elevation"] = min(1.0, hr_rise / 15.0)
                factors.append(f"Resting HR +{hr_rise:.0f} bpm above baseline")
            else:
                scores["hr_elevation"] = 0.0
        else:
            scores["hr_elevation"] = 0.0

        # 5. Feeding Decline (from ADL "eating" duration)
        bl_eating = baseline.get("eating_minutes", 1)
        cur_eating = current.get("eating_minutes", 0)
        if bl_eating > 0:
            decline = (bl_eating - cur_eating) / bl_eating
            if decline > 0.25:
                scores["feeding_decline"] = min(1.0, decline)
                factors.append(f"Eating time declined {decline*100:.0f}%")
            else:
                scores["feeding_decline"] = 0.0
        else:
            scores["feeding_decline"] = 0.0

        # Compute weighted composite score
        composite = sum(scores.get(k, 0) * w for k, w in self.WEIGHTS.items())

        # Determine risk level
        if composite >= self.COMPOSITE_CRITICAL_THRESHOLD:
            risk_level = "HIGH"
        elif composite >= self.COMPOSITE_WARNING_THRESHOLD:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"

        result = {
            "resident_id": resident_id,
            "risk_score": round(composite, 3),
            "risk_level": risk_level,
            "contributing_factors": factors,
            "signal_scores": scores,
        }

        if risk_level != "LOW":
            logger.warning("Infection risk detected",
                           resident=resident_id,
                           level=risk_level,
                           score=composite,
                           factors=factors)

        return result
