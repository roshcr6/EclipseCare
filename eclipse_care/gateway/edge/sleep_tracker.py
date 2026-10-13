"""Eclipse Care — Sleep Quality Tracker (Edge).

Classifies sleep periods and detects nighttime disturbances using
accelerometer (movement magnitude) and heart rate data.

EVIDENCE BASE:
- Sleep quality is a key clinical indicator of overall health in elderly.
- Nighttime restlessness and increased bathroom visits are validated early
  signals for UTI, depression, and general decline (EDIS framework).
- This tracker runs on the Edge Gateway using simple threshold-based
  state machines (not deep learning) to minimize compute and battery.

APPROACH:
  Uses a sliding window of IMU magnitude + HR to classify periods as:
  - AWAKE: Movement > threshold OR HR elevated above sleep baseline
  - LIGHT_SLEEP: Low movement, HR near resting baseline
  - DEEP_SLEEP: Very low movement, HR at/below resting baseline
  - DISTURBED: Transition from sleep -> brief movement -> sleep

  Nighttime disturbance count and total sleep time are the primary
  outputs surfaced to the Cloud for predictive analytics.
"""

import time
import numpy as np
import structlog
from collections import deque
from enum import Enum

logger = structlog.get_logger("edge.sleep_tracker")


class SleepState(str, Enum):
    AWAKE = "awake"
    LIGHT_SLEEP = "light_sleep"
    DEEP_SLEEP = "deep_sleep"
    DISTURBED = "disturbed"


class SleepTracker:
    """Edge-based sleep quality classifier using IMU + HR data.

    Designed for continuous operation on the Gateway. Produces nightly
    summaries that are pushed to the Cloud for predictive analytics.
    """

    # Thresholds calibrated for elderly population
    MOVEMENT_AWAKE_THRESHOLD = 0.15    # g — above this, resident is moving/awake
    MOVEMENT_RESTLESS_THRESHOLD = 0.08 # g — between this and awake = restless
    HR_SLEEP_DROP_PCT = 0.10           # HR drops ~10% during sleep vs baseline
    NIGHT_START_HOUR = 21              # 9 PM
    NIGHT_END_HOUR = 7                 # 7 AM
    DISTURBANCE_MIN_DURATION_SEC = 30  # Must be awake > 30s to count as disturbance

    def __init__(self, resting_hr_baseline: float = 68.0):
        self.resting_hr = resting_hr_baseline
        self.sleep_hr_threshold = self.resting_hr * (1 - self.HR_SLEEP_DROP_PCT)

        # Current state
        self.current_state = SleepState.AWAKE
        self._state_start_ts = time.time()

        # Rolling buffers (last 2 minutes for smoothing)
        self._movement_buffer = deque(maxlen=120)  # 1 sample/sec for 2 min
        self._hr_buffer = deque(maxlen=30)          # ~1 sample/2sec

        # Nightly accumulator
        self._night_active = False
        self._disturbance_count = 0
        self._total_sleep_sec = 0.0
        self._deep_sleep_sec = 0.0
        self._sleep_onset_ts = None
        self._last_state_change_ts = time.time()

    def update(self, movement_magnitude: float = None, hr: float = None,
               current_hour: int = None) -> dict:
        """Feed new sensor data. Returns state change dict if state changed."""
        if movement_magnitude is not None:
            self._movement_buffer.append(movement_magnitude)
        if hr is not None:
            self._hr_buffer.append(hr)

        # Determine if it's "nighttime" (when sleep tracking is most meaningful)
        if current_hour is not None:
            self._night_active = (current_hour >= self.NIGHT_START_HOUR or
                                  current_hour < self.NIGHT_END_HOUR)

        # Classify current state
        new_state = self._classify_state()
        result = None

        if new_state != self.current_state:
            now = time.time()
            duration_in_prev = now - self._last_state_change_ts

            # Track sleep accumulation
            if self.current_state in (SleepState.LIGHT_SLEEP, SleepState.DEEP_SLEEP):
                self._total_sleep_sec += duration_in_prev
                if self.current_state == SleepState.DEEP_SLEEP:
                    self._deep_sleep_sec += duration_in_prev

            # Detect disturbances (was asleep, now briefly awake)
            if (self.current_state in (SleepState.LIGHT_SLEEP, SleepState.DEEP_SLEEP)
                    and new_state == SleepState.AWAKE
                    and self._night_active):
                self._disturbance_count += 1
                logger.info("Sleep disturbance detected",
                            count=self._disturbance_count,
                            prev_state=self.current_state)

            # Track sleep onset
            if (new_state in (SleepState.LIGHT_SLEEP, SleepState.DEEP_SLEEP)
                    and self._sleep_onset_ts is None):
                self._sleep_onset_ts = now

            result = {
                "prev_state": self.current_state,
                "new_state": new_state,
                "duration_prev_sec": duration_in_prev,
                "disturbance_count": self._disturbance_count,
            }

            self.current_state = new_state
            self._last_state_change_ts = now
            logger.debug("Sleep state changed", new_state=new_state)

        return result

    def _classify_state(self) -> SleepState:
        """Classify current sleep state from buffered sensor data."""
        if len(self._movement_buffer) < 5:
            return self.current_state  # Not enough data yet

        avg_movement = np.mean(list(self._movement_buffer)[-30:])  # Last 30s
        avg_hr = np.mean(list(self._hr_buffer)[-10:]) if len(self._hr_buffer) >= 3 else None

        # High movement = awake
        if avg_movement > self.MOVEMENT_AWAKE_THRESHOLD:
            return SleepState.AWAKE

        # Low movement but HR available
        if avg_hr is not None:
            if avg_movement < self.MOVEMENT_RESTLESS_THRESHOLD and avg_hr <= self.sleep_hr_threshold:
                return SleepState.DEEP_SLEEP
            elif avg_movement < self.MOVEMENT_AWAKE_THRESHOLD and avg_hr <= self.resting_hr * 1.05:
                return SleepState.LIGHT_SLEEP

        # Low movement, no HR data — assume light sleep
        if avg_movement < self.MOVEMENT_RESTLESS_THRESHOLD:
            return SleepState.DEEP_SLEEP if not self._night_active else SleepState.LIGHT_SLEEP

        return SleepState.AWAKE

    def get_nightly_summary(self) -> dict:
        """Generate the nightly sleep summary for Cloud upload.

        Should be called at NIGHT_END_HOUR (7 AM) by the main loop.
        """
        summary = {
            "total_sleep_min": round(self._total_sleep_sec / 60, 1),
            "deep_sleep_min": round(self._deep_sleep_sec / 60, 1),
            "disturbance_count": self._disturbance_count,
            "sleep_efficiency_pct": 0.0,
        }

        # Sleep efficiency = time asleep / time in bed
        if self._sleep_onset_ts:
            time_in_bed = time.time() - self._sleep_onset_ts
            if time_in_bed > 0:
                summary["sleep_efficiency_pct"] = round(
                    (self._total_sleep_sec / time_in_bed) * 100, 1
                )

        return summary

    def reset_nightly(self):
        """Reset accumulators for the next night."""
        self._disturbance_count = 0
        self._total_sleep_sec = 0.0
        self._deep_sleep_sec = 0.0
        self._sleep_onset_ts = None
