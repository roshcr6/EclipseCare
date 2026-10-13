"""Eclipse Care Gateway — Configuration."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


@dataclass
class GatewayConfig:
    """All gateway configuration from environment or defaults."""

    # --- Identity ---
    gateway_id: str = os.getenv("ECLIPSE_GATEWAY_ID", "gw-001")
    facility_id: str = os.getenv("ECLIPSE_FACILITY_ID", "facility-001")
    building: str = os.getenv("ECLIPSE_BUILDING", "Main")
    floor: str = os.getenv("ECLIPSE_FLOOR", "1")

    # --- BLE ---
    ble_scan_interval_sec: float = float(os.getenv("ECLIPSE_BLE_SCAN_INTERVAL", "1.0"))
    ble_scan_window_sec: float = float(os.getenv("ECLIPSE_BLE_SCAN_WINDOW", "5.0"))
    # Known wearable MAC prefixes or service UUIDs to filter scans
    ble_device_prefixes: list[str] = field(default_factory=lambda: 
        os.getenv("ECLIPSE_BLE_PREFIXES", "EC:CA:RE").split(","))
    # WHOOP custom service UUID (from verified FINDINGS.md)
    whoop_service_uuid: str = "61080001-8d6d-82b8-614a-1c8cb0f8dcc6"
    # Standard BLE Heart Rate service (works without bonding)
    standard_hr_service: str = "0000180d-0000-1000-8000-00805f9b34fb"

    # --- Edge Processing ---
    # Heart rate thresholds for elderly (evidence: AHA guidelines)
    hr_critical_low: int = int(os.getenv("ECLIPSE_HR_CRIT_LOW", "40"))
    hr_warning_low: int = int(os.getenv("ECLIPSE_HR_WARN_LOW", "50"))
    hr_warning_high: int = int(os.getenv("ECLIPSE_HR_WARN_HIGH", "100"))
    hr_critical_high: int = int(os.getenv("ECLIPSE_HR_CRIT_HIGH", "120"))
    # SpO2 thresholds (evidence: WHO/clinical guidelines)
    spo2_critical: int = int(os.getenv("ECLIPSE_SPO2_CRIT", "90"))
    spo2_warning: int = int(os.getenv("ECLIPSE_SPO2_WARN", "94"))
    # Temperature thresholds in °C (evidence: clinical fever definition)
    temp_critical_high: float = float(os.getenv("ECLIPSE_TEMP_CRIT_HIGH", "39.0"))
    temp_warning_high: float = float(os.getenv("ECLIPSE_TEMP_WARN_HIGH", "37.8"))
    temp_critical_low: float = float(os.getenv("ECLIPSE_TEMP_CRIT_LOW", "35.0"))
    # No-movement alert after N seconds
    no_movement_timeout_sec: int = int(os.getenv("ECLIPSE_NO_MOVE_TIMEOUT", "1800"))  # 30 min
    # Fall detection — accelerometer threshold in g
    fall_accel_threshold_g: float = float(os.getenv("ECLIPSE_FALL_THRESHOLD_G", "3.0"))
    # Battery low threshold %
    battery_low_pct: float = float(os.getenv("ECLIPSE_BATTERY_LOW", "15.0"))
    battery_critical_pct: float = float(os.getenv("ECLIPSE_BATTERY_CRIT", "5.0"))

    # --- Local Storage ---
    db_path: str = os.getenv("ECLIPSE_DB_PATH",
                             str(Path.home() / ".eclipse_care" / "gateway.db"))

    # --- Cloud Sync ---
    cloud_url: str = os.getenv("ECLIPSE_CLOUD_URL", "http://localhost:8080")
    cloud_api_key: str = os.getenv("ECLIPSE_CLOUD_API_KEY", "")
    mqtt_broker: str = os.getenv("ECLIPSE_MQTT_BROKER", "localhost")
    mqtt_port: int = int(os.getenv("ECLIPSE_MQTT_PORT", "1883"))
    mqtt_topic_prefix: str = os.getenv("ECLIPSE_MQTT_TOPIC", "eclipse/care")
    sync_interval_sec: int = int(os.getenv("ECLIPSE_SYNC_INTERVAL", "30"))

    # --- Logging ---
    log_level: str = os.getenv("ECLIPSE_LOG_LEVEL", "INFO")
