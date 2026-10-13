"""Eclipse Care — Activities of Daily Living (ADL) Classifier (Edge).

Classifies resident activity into clinically meaningful states using a
lightweight state machine over IMU (accelerometer) and heart rate data.

EVIDENCE BASE:
- ADL-tracking wearables in elder care (e.g. wrist-worn accelerometer devices)
  have been used to autonomously track eating, sleeping, bathing, and mobility
  without manual input. [Likely — based on published product descriptions,
  not independently verified by us.]
- ADL patterns are the foundation for: depression detection (2-week advance),
  UTI prediction, malnutrition risk, and fall risk scoring.
- EDIS (Early Detection of Infection Scale) identifies changes in feeding,
  movement, and emotion as relevant infection signals in frail elderly
  (published research).

STATES:
  RESTING   — Minimal movement, HR near baseline, extended duration
  WALKING   — Rhythmic moderate movement, elevated HR
  EATING    — Seated (low movement) with subtle arm gestures, at meal hours
  BATHING   — Movement in bathroom zone (requires RSSI from bathroom gateway)
  SLEEPING  — Delegated to SleepTracker (nighttime, very low movement)
  ACTIVE    — Catch-all for non-rhythmic movement (e.g., wheelchair, PT)

DESIGN NOTE:
  This is a deterministic state machine, NOT a deep learning model.
  We avoid black-box classifiers because:
  1. No validated training dataset exists for this specific wearable.
  2. Deterministic rules are auditable (critical for clinical settings).
  3. Edge compute budget on Raspberry Pi is limited.
"""

import time
import numpy as np
import structlog
from enum import Enum
from collections import deque

logger = structlog.get_logger("edge.adl_classifier")


class ADLState(str, Enum):
    RESTING = "resting"
    WALKING = "walking"
    EATING = "eating"
    BATHING = "bathing"
    SLEEPING = "sleeping"
    ACTIVE = "active"
    UNKNOWN = "unknown"


class ADLClassifier:
    """Lightweight ADL classifier using IMU magnitude, HR, time-of-day, and zone.

    Produces a rolling activity log that feeds Cloud-side predictive models
    for depression, malnutrition, and infection detection.
    """

    # Movement thresholds (in g)
    RESTING_THRESHOLD = 0.05
    WALKING_THRESHOLD = 0.12
    ACTIVE_THRESHOLD = 0.25

    # Walking detection: rhythmic acceleration in 1.5-3.0 Hz band
    WALKING_CADENCE_MIN_HZ = 1.2
    WALKING_CADENCE_MAX_HZ = 3.5

    # Meal windows (facility schedule — configurable)
    MEAL_WINDOWS = [
        (7, 9),    # Breakfast
        (11, 13),  # Lunch
        (17, 19),  # Dinner
    ]

    # Minimum duration to confirm state transition (debounce)
    STATE_CONFIRM_SEC = 15

    def __init__(self, resting_hr: float = 68.0):
        self.resting_hr = resting_hr

        # Current confirmed state
        self.current_state = ADLState.UNKNOWN
        self._pending_state = None
        self._pending_since = 0.0

        # Sensor buffers
        self._accel_mag_buffer = deque(maxlen=256)  # ~5 sec at 50 Hz
        self._hr_buffer = deque(maxlen=30)

        # Daily ADL log: list of (state, start_ts, duration_sec)
        self._daily_log = []
        self._state_start_ts = time.time()

        # Zone awareness (set by RSSI updates from processor)
        self.current_zone = None  # e.g., "Bathroom", "Dining Hall"

    def update(self, accel_magnitude: float = None, hr: float = None,
               current_hour: int = None, zone: str = None) -> dict | None:
        """Feed sensor data. Returns state change dict if state transitions."""
        if accel_magnitude is not None:
            self._accel_mag_buffer.append(accel_magnitude)
        if hr is not None:
            self._hr_buffer.append(hr)
        if zone is not None:
            self.current_zone = zone

        new_state = self._classify(current_hour)

        # Debounce: require STATE_CONFIRM_SEC of consistent new state
        now = time.time()
        if new_state != self.current_state:
            if self._pending_state == new_state:
                if now - self._pending_since >= self.STATE_CONFIRM_SEC:
                    return self._transition(new_state, now)
            else:
                self._pending_state = new_state
                self._pending_since = now
        else:
            self._pending_state = None

        return None

    def _classify(self, current_hour: int = None) -> ADLState:
        """Core classification logic."""
        if len(self._accel_mag_buffer) < 10:
            return self.current_state

        recent = list(self._accel_mag_buffer)[-50:]
        avg_mag = np.mean(recent)
        std_mag = np.std(recent)

        avg_hr = np.mean(list(self._hr_buffer)[-10:]) if len(self._hr_buffer) >= 3 else None

        # === ZONE-BASED OVERRIDES ===
        if self.current_zone and "bathroom" in self.current_zone.lower():
            if avg_mag > self.RESTING_THRESHOLD:
                return ADLState.BATHING

        # === MOVEMENT-BASED CLASSIFICATION ===

        # Very still = Resting or Sleeping
        if avg_mag < self.RESTING_THRESHOLD:
            if current_hour is not None and (current_hour >= 21 or current_hour < 7):
                return ADLState.SLEEPING
            return ADLState.RESTING

        # Rhythmic moderate movement = Walking
        if self.WALKING_THRESHOLD <= avg_mag <= self.ACTIVE_THRESHOLD:
            # Check for rhythmic cadence (walking has regular acceleration peaks)
            if self._detect_walking_cadence(recent):
                return ADLState.WALKING

        # During meal windows + seated (low-moderate movement) = Eating
        if current_hour is not None:
            for start, end in self.MEAL_WINDOWS:
                if start <= current_hour < end:
                    if avg_mag < self.WALKING_THRESHOLD and avg_mag > self.RESTING_THRESHOLD:
                        return ADLState.EATING

        # High movement = general Active
        if avg_mag > self.ACTIVE_THRESHOLD:
            return ADLState.ACTIVE

        # Moderate non-rhythmic movement
        if avg_mag > self.RESTING_THRESHOLD:
            return ADLState.ACTIVE

        return self.current_state

    def _detect_walking_cadence(self, signal: list) -> bool:
        """Detect rhythmic walking pattern via zero-crossing rate."""
        if len(signal) < 30:
            return False

        arr = np.array(signal)
        mean = np.mean(arr)
        centered = arr - mean

        # Count zero crossings
        crossings = np.sum(np.diff(np.sign(centered)) != 0)
        duration_sec = len(signal) / 50.0  # Assuming ~50 Hz sample rate

        if duration_sec <= 0:
            return False

        crossing_rate_hz = crossings / (2.0 * duration_sec)

        return self.WALKING_CADENCE_MIN_HZ <= crossing_rate_hz <= self.WALKING_CADENCE_MAX_HZ

    def _transition(self, new_state: ADLState, now: float) -> dict:
        """Record state transition and return change event."""
        duration = now - self._state_start_ts

        # Log the completed state
        if self.current_state != ADLState.UNKNOWN:
            self._daily_log.append({
                "state": self.current_state,
                "start_ts": self._state_start_ts,
                "duration_sec": round(duration, 1),
            })

        prev = self.current_state
        self.current_state = new_state
        self._state_start_ts = now
        self._pending_state = None

        logger.info("ADL state changed", prev=prev, new=new_state, duration=f"{duration:.0f}s")

        return {
            "prev_state": prev,
            "new_state": new_state,
            "duration_prev_sec": round(duration, 1),
        }

    def get_daily_summary(self) -> dict:
        """Generate daily ADL summary for Cloud upload.

        Returns time spent in each state (minutes) — this is the input
        for depression/malnutrition/infection detection models.
        """
        totals = {state.value: 0.0 for state in ADLState}

        for entry in self._daily_log:
            state = entry["state"]
            if isinstance(state, ADLState):
                totals[state.value] += entry["duration_sec"]
            else:
                totals[state] += entry["duration_sec"]

        # Convert to minutes
        return {k: round(v / 60.0, 1) for k, v in totals.items()}

    def reset_daily(self):
        """Reset daily log for the next 24-hour period."""
        self._daily_log.clear()
