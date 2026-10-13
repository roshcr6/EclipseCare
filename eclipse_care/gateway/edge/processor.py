"""Eclipse Care — Edge Processor (AI-Powered).

Processes raw sensor data at the edge (Gateway).
Responsible for:
  - Anomaly detection (HR deviations via Isolation Forest)
  - Absolute threshold alerts (Critical HR limits)
  - AI Fall detection (TFLite CNN/SVM inference on IMU windows)
  - No-movement / prolonged stillness alerts
  - Generating Alert events
"""

import math
import time
from typing import Any
from collections import deque
from ..ble.decoder import SensorReading, ReadingType
from ..config import GatewayConfig

from .fall_model import FallDetectionModel
from .vitals_anomaly import VitalsAnomalyDetector

import structlog
logger = structlog.get_logger("edge.processor")


class EdgeProcessor:
    """Processes sensor readings in real-time on the gateway using Edge AI."""

    def __init__(self, config: GatewayConfig, alert_callback=None):
        self.config = config
        self.alert_callback = alert_callback
        
        # ML Models
        self.fall_model = FallDetectionModel(window_size=128)
        self.vitals_anomaly = VitalsAnomalyDetector()
        
        # State tracking for falls (sliding window buffer)
        self.accel_window_x = deque(maxlen=128)
        self.accel_window_y = deque(maxlen=128)
        self.accel_window_z = deque(maxlen=128)
        self.gyro_window_x = deque(maxlen=128)
        self.gyro_window_y = deque(maxlen=128)
        self.gyro_window_z = deque(maxlen=128)
        
        self._last_movement_ts = time.time()
        self._pacing_start_ts = None
        self._is_worn = True
        self._active_alerts = set()

    def process_reading(self, reading: SensorReading) -> None:
        """Process a single reading and generate alerts if needed."""
        try:
            if reading.reading_type == ReadingType.HEART_RATE:
                self._process_heart_rate(reading)
            elif reading.reading_type == ReadingType.ACCELEROMETER:
                self._buffer_accel(reading)
            elif reading.reading_type == ReadingType.GYROSCOPE:
                self._buffer_gyro(reading)
            elif reading.reading_type == ReadingType.BATTERY:
                self._check_battery(reading)
            elif reading.reading_type == ReadingType.RSSI:
                # RSSI is tracked via the Cloud Geofence mapping, but edge can log it
                pass
            elif reading.reading_type == ReadingType.SKIN_CONTACT:
                self._is_worn = reading.value
                if not self._is_worn:
                    self._trigger_alert(reading.device_id, "DEVICE_REMOVED", "critical", "Device taken off")
            
            # Check fall inference if buffer is full
            self._check_fall_inference(reading.device_id)
                
        except Exception as e:
            logger.error("Error processing reading", error=str(e), reading=reading)

    def check_timeouts(self, device_id: str):
        """Called periodically to check time-based alerts."""
        now = time.time()
        if self._is_worn and (now - self._last_movement_ts > self.config.no_movement_timeout_sec):
            alert_key = f"{device_id}_NO_MOVEMENT"
            if alert_key not in self._active_alerts:
                self._trigger_alert(
                    device_id, 
                    "NO_MOVEMENT", 
                    "warning", 
                    f"No movement detected for {self.config.no_movement_timeout_sec // 60} minutes"
                )
                self._active_alerts.add(alert_key)

    def _process_heart_rate(self, reading: SensorReading):
        hr = reading.value
        device_id = reading.device_id
        
        # 1. Update baseline model
        self.vitals_anomaly.add_reading(hr=hr)
        
        # 2. Check AI Anomaly (Deterioration warning)
        if self.vitals_anomaly.is_anomalous(hr=hr):
            alert_key = f"{device_id}_HR_ANOMALY"
            if alert_key not in self._active_alerts:
                self._trigger_alert(device_id, "HR_ANOMALY", "warning", f"Heart rate deviated significantly from resident baseline ({hr} bpm)")
                self._active_alerts.add(alert_key)
        
        # 3. Check hard clinical thresholds (Emergency)
        alert_type = None
        severity = None
        msg = None
        
        if hr >= self.config.hr_critical_high:
            alert_type = "HR_CRITICAL_HIGH"
            severity = "critical"
            msg = f"Critical High Heart Rate: {hr} bpm"
        elif hr <= self.config.hr_critical_low:
            alert_type = "HR_CRITICAL_LOW"
            severity = "critical"
            msg = f"Critical Low Heart Rate: {hr} bpm"
            
        if alert_type:
            alert_key = f"{device_id}_{alert_type}"
            if alert_key not in self._active_alerts:
                self._trigger_alert(device_id, alert_type, severity, msg)
                self._active_alerts.add(alert_key)

    def _buffer_accel(self, reading: SensorReading):
        """Buffer raw accelerometer data for sliding window inference."""
        data = reading.value
        self.accel_window_x.extend(data.get("x", []))
        self.accel_window_y.extend(data.get("y", []))
        self.accel_window_z.extend(data.get("z", []))
        
        # Update movement timestamp for stillness and pacing tracking
        xs = data.get("x", [])
        if xs and (max(xs) - min(xs) > 0.1):
            now = time.time()
            self._last_movement_ts = now
            
            if self._pacing_start_ts is None:
                self._pacing_start_ts = now
            elif now - self._pacing_start_ts > 900: # 15 minutes of continuous movement
                alert_key = f"{reading.device_id}_PACING"
                if alert_key not in self._active_alerts:
                    self._trigger_alert(
                        reading.device_id, 
                        "BEHAVIORAL_WANDERING_RISK", 
                        "warning", 
                        "Resident has been pacing continuously for > 15 minutes."
                    )
                    self._active_alerts.add(alert_key)
            
            alert_key = f"{reading.device_id}_NO_MOVEMENT"
            if alert_key in self._active_alerts:
                self._active_alerts.remove(alert_key)
                logger.info("Movement resumed", device=reading.device_id)
        else:
            # If they stop moving, reset pacing tracker
            self._pacing_start_ts = None

    def _buffer_gyro(self, reading: SensorReading):
        """Buffer raw gyroscope data."""
        data = reading.value
        self.gyro_window_x.extend(data.get("x", []))
        self.gyro_window_y.extend(data.get("y", []))
        self.gyro_window_z.extend(data.get("z", []))

    def _check_fall_inference(self, device_id: str):
        """Run the AI fall detection model on the sliding window."""
        if len(self.accel_window_x) >= self.fall_model.window_size:
            
            accel_dict = {
                "x": list(self.accel_window_x)[-self.fall_model.window_size:],
                "y": list(self.accel_window_y)[-self.fall_model.window_size:],
                "z": list(self.accel_window_z)[-self.fall_model.window_size:]
            }
            gyro_dict = {
                "x": list(self.gyro_window_x)[-self.fall_model.window_size:] if len(self.gyro_window_x) >= self.fall_model.window_size else [],
                "y": list(self.gyro_window_y)[-self.fall_model.window_size:] if len(self.gyro_window_y) >= self.fall_model.window_size else [],
                "z": list(self.gyro_window_z)[-self.fall_model.window_size:] if len(self.gyro_window_z) >= self.fall_model.window_size else []
            }
            
            prob = self.fall_model.predict(accel_dict, gyro_dict)
            
            if prob > 0.8: # High confidence fall
                logger.warning("AI detected fall signature", confidence=prob)
                self._trigger_alert(
                    device_id, 
                    "FALL_DETECTED", 
                    "emergency", 
                    f"Fall detected (AI confidence: {prob*100:.0f}%)"
                )
                
                # Clear buffer to prevent double-alerting on the same fall
                self.accel_window_x.clear()
                self.accel_window_y.clear()
                self.accel_window_z.clear()

    def _check_battery(self, reading: SensorReading):
        soc = reading.value
        if soc is None:
            return
            
        if soc <= self.config.battery_critical_pct:
            alert_key = f"{reading.device_id}_BATTERY_CRIT"
            if alert_key not in self._active_alerts:
                self._trigger_alert(reading.device_id, "BATTERY_CRITICAL", "critical", f"Battery critically low: {soc:.1f}%")
                self._active_alerts.add(alert_key)
        elif soc <= self.config.battery_low_pct:
            alert_key = f"{reading.device_id}_BATTERY_LOW"
            if alert_key not in self._active_alerts:
                self._trigger_alert(reading.device_id, "BATTERY_LOW", "warning", f"Battery low: {soc:.1f}%")
                self._active_alerts.add(alert_key)

    def _trigger_alert(self, device_id: str, alert_type: str, severity: str, message: str):
        """Generate and emit an alert."""
        logger.error("ALERT GENERATED", device=device_id, type=alert_type, severity=severity, message=message)
        
        alert_data = {
            "device_id": device_id,
            "gateway_id": self.config.gateway_id,
            "facility_id": self.config.facility_id,
            "type": alert_type,
            "severity": severity,
            "message": message,
            "timestamp": time.time()
        }
        
        if self.alert_callback:
            self.alert_callback(alert_data)
