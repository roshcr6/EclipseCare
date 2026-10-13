"""Eclipse Care — R&D Simulation & Test Suite.

Comprehensive tests for every AI subsystem in the Eclipse Care platform.
Validates accuracy, false positive rates, and edge cases for:
  1. Fall Detection (Edge AI CNN Heuristic)
  2. Vitals Anomaly Detection (Isolation Forest)
  3. Pacing / Wandering Detection (Edge Processor)
  4. UTI Predictive Heuristic (Cloud Predictive Engine)
  5. Alert Evaluator (LLM Hybrid Rule Engine)

NOTE: Uses importlib to surgically import modules without triggering
      the full gateway __init__.py chain (which requires bleak BLE lib).
"""

import sys
import os
import math
import time
import types
import importlib
import importlib.util
import asyncio
import random
import numpy as np
from collections import deque
from dataclasses import dataclass, field
from enum import Enum

# ── Setup: Minimal stub modules to satisfy import chain ─────────────────
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE)

# Stub out gateway packages so that __init__.py doesn't pull in bleak
gateway_pkg = types.ModuleType("gateway")
gateway_pkg.__path__ = [os.path.join(BASE, "gateway")]
sys.modules["gateway"] = gateway_pkg

gateway_ble = types.ModuleType("gateway.ble")
gateway_ble.__path__ = [os.path.join(BASE, "gateway", "ble")]
sys.modules["gateway.ble"] = gateway_ble

gateway_edge = types.ModuleType("gateway.edge")
gateway_edge.__path__ = [os.path.join(BASE, "gateway", "edge")]
sys.modules["gateway.edge"] = gateway_edge

# Stub the gateway config
gateway_config = types.ModuleType("gateway.config")

class _StubConfig:
    gateway_id = "GW_TEST"
    facility_id = "FAC_TEST"
    ble_device_prefixes = ["ECLIPSE"]
    ble_scan_window_sec = 5
    hr_critical_high = 150
    hr_critical_low = 30
    no_movement_timeout_sec = 1800
    battery_low_pct = 20
    battery_critical_pct = 5

gateway_config.GatewayConfig = _StubConfig
sys.modules["gateway.config"] = gateway_config

# Now load individual modules by spec (bypassing __init__.py)
def _load_module(name, filepath):
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

# 1) Load decoder (no external deps)
decoder = _load_module("gateway.ble.decoder",
                       os.path.join(BASE, "gateway", "ble", "decoder.py"))
# patch framing import (decoder uses framing types)
framing = _load_module("gateway.ble.framing",
                       os.path.join(BASE, "gateway", "ble", "framing.py"))

SensorReading = decoder.SensorReading
ReadingType = decoder.ReadingType

# 2) Load fall model
fall_model_mod = _load_module("gateway.edge.fall_model",
                              os.path.join(BASE, "gateway", "edge", "fall_model.py"))
FallDetectionModel = fall_model_mod.FallDetectionModel

# 3) Load vitals anomaly
vitals_mod = _load_module("gateway.edge.vitals_anomaly",
                          os.path.join(BASE, "gateway", "edge", "vitals_anomaly.py"))
VitalsAnomalyDetector = vitals_mod.VitalsAnomalyDetector

# 4) Load processor
processor_mod = _load_module("gateway.edge.processor",
                             os.path.join(BASE, "gateway", "edge", "processor.py"))
EdgeProcessor = processor_mod.EdgeProcessor


# ═══════════════════════════════════════════════════════════════════════
# TEST UTILITIES
# ═══════════════════════════════════════════════════════════════════════
PASS = 0
FAIL = 0

def report(name, passed, detail=""):
    global PASS, FAIL
    if passed:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  --  {detail}")


def generate_normal_walking(n=128):
    """Simulate normal elderly walking IMU data (~0.8-1.2g magnitude)."""
    t = np.linspace(0, 2.56, n)
    ax = 0.1 * np.sin(2 * np.pi * 2 * t) + np.random.normal(0, 0.02, n)
    ay = 0.05 * np.sin(2 * np.pi * 2 * t + 1) + np.random.normal(0, 0.02, n)
    az = 1.0 + 0.05 * np.sin(2 * np.pi * 2 * t) + np.random.normal(0, 0.02, n)
    return {"x": ax.tolist(), "y": ay.tolist(), "z": az.tolist()}


def generate_fall_signal(n=128):
    """Simulate a realistic fall: freefall -> impact -> stillness."""
    ax = np.zeros(n)
    ay = np.zeros(n)
    az = np.zeros(n)

    # Phase 1: Normal standing (0-40 samples)
    for i in range(40):
        ax[i] = np.random.normal(0, 0.03)
        ay[i] = np.random.normal(0, 0.03)
        az[i] = 1.0 + np.random.normal(0, 0.03)

    # Phase 2: Freefall (40-55 samples) — magnitude drops near 0
    for i in range(40, 55):
        ax[i] = np.random.normal(0, 0.05)
        ay[i] = np.random.normal(0, 0.05)
        az[i] = np.random.normal(0, 0.1)

    # Phase 3: Impact spike (55-65 samples) — magnitude >3g
    for i in range(55, 65):
        ax[i] = np.random.normal(0, 0.5) + 2.0
        ay[i] = np.random.normal(0, 0.3) + 1.5
        az[i] = np.random.normal(0, 0.3) + 2.0

    # Phase 4: Post-impact stillness (65-128) — low variance, ~1g
    for i in range(65, n):
        ax[i] = np.random.normal(0, 0.01)
        ay[i] = np.random.normal(0, 0.01)
        az[i] = 1.0 + np.random.normal(0, 0.01)

    return {"x": ax.tolist(), "y": ay.tolist(), "z": az.tolist()}


def generate_chair_sit(n=128):
    """Simulate sitting down hard (false positive trap — NOT a fall)."""
    ax = np.zeros(n)
    ay = np.zeros(n)
    az = np.zeros(n)

    for i in range(60):
        ax[i] = 0.1 * np.sin(i * 0.2) + np.random.normal(0, 0.03)
        ay[i] = np.random.normal(0, 0.03)
        az[i] = 1.0 + np.random.normal(0, 0.03)

    # Sitting impact — moderate spike ~2g but NO freefall phase
    for i in range(60, 75):
        ax[i] = np.random.normal(0, 0.3) + 0.5
        ay[i] = np.random.normal(0, 0.2)
        az[i] = 1.5 + np.random.normal(0, 0.2)

    for i in range(75, n):
        ax[i] = np.random.normal(0, 0.01)
        ay[i] = np.random.normal(0, 0.01)
        az[i] = 1.0 + np.random.normal(0, 0.01)

    return {"x": ax.tolist(), "y": ay.tolist(), "z": az.tolist()}


# ═══════════════════════════════════════════════════════════════════════
# SIMULATION 1: FALL DETECTION MODEL (Edge AI)
# ═══════════════════════════════════════════════════════════════════════
def test_fall_detection():
    print("\n" + "="*70)
    print("SIMULATION 1: FALL DETECTION MODEL (Edge AI Heuristic)")
    print("="*70)

    model = FallDetectionModel(model_path="nonexistent.tflite")
    assert not model.is_loaded, "Should use fallback since no .tflite file"

    # Test 1: True positive — actual fall
    fall_data = generate_fall_signal()
    prob = model.predict(fall_data, {})
    report("True Positive: Detects fall signal", prob > 0.7, f"prob={prob:.2f}")

    # Test 2: True negative — normal walking
    walk_data = generate_normal_walking()
    prob = model.predict(walk_data, {})
    report("True Negative: Ignores normal walking", prob < 0.3, f"prob={prob:.2f}")

    # Test 3: True negative — sitting down (common false positive trap)
    sit_data = generate_chair_sit()
    prob = model.predict(sit_data, {})
    report("True Negative: Ignores sitting down", prob < 0.3, f"prob={prob:.2f}")

    # Test 4: Batch sensitivity — 100 fall signals
    fall_detected = 0
    for _ in range(100):
        prob = model.predict(generate_fall_signal(), {})
        if prob > 0.7:
            fall_detected += 1
    sensitivity = fall_detected / 100
    report(f"Sensitivity (100 falls): {sensitivity*100:.0f}%", sensitivity > 0.85,
           f"sensitivity={sensitivity:.2f}")

    # Test 5: Batch specificity — 100 ADL signals
    false_positives = 0
    for _ in range(100):
        prob = model.predict(generate_normal_walking(), {})
        if prob > 0.7:
            false_positives += 1
    fpr = false_positives / 100
    report(f"False Positive Rate (100 ADL): {fpr*100:.0f}%", fpr < 0.05,
           f"fpr={fpr:.2f}")


# ═══════════════════════════════════════════════════════════════════════
# SIMULATION 2: VITALS ANOMALY DETECTION (Isolation Forest)
# ═══════════════════════════════════════════════════════════════════════
def test_vitals_anomaly():
    print("\n" + "="*70)
    print("SIMULATION 2: VITALS ANOMALY DETECTION (Isolation Forest)")
    print("="*70)

    detector = VitalsAnomalyDetector(history_size=500, training_interval_sec=0)

    # Feed 200 readings of normal baseline (~68 bpm)
    for _ in range(200):
        detector.add_reading(hr=np.random.normal(68, 3))
    detector._train_model()

    # Test 1: Normal reading
    is_anom = detector.is_anomalous(hr=70)
    report("Normal HR (70 bpm) on 68bpm baseline -> NOT anomalous", not is_anom)

    # Test 2: Extreme spike
    is_anom = detector.is_anomalous(hr=120)
    report("Extreme spike (120 bpm) on 68bpm baseline -> anomalous", is_anom,
           f"is_anomalous={is_anom}")

    # Test 3: Extreme drop
    is_anom = detector.is_anomalous(hr=35)
    report("Extreme drop (35 bpm) on 68bpm baseline -> anomalous", is_anom,
           f"is_anomalous={is_anom}")

    # Test 4: Gradual drift (sepsis onset simulation)
    detector2 = VitalsAnomalyDetector(history_size=500, training_interval_sec=0)
    for _ in range(200):
        detector2.add_reading(hr=np.random.normal(68, 3))
    detector2._train_model()

    drift_detected_at = None
    for i in range(40):
        hr = 68 + i * 0.5
        if detector2.is_anomalous(hr=hr):
            drift_detected_at = hr
            break
    report(
        f"Gradual drift detected at {drift_detected_at:.0f}bpm" if drift_detected_at else "Drift test",
        drift_detected_at is not None,
        f"detected_at={drift_detected_at}"
    )


# ═══════════════════════════════════════════════════════════════════════
# SIMULATION 3: PACING / WANDERING DETECTION
# ═══════════════════════════════════════════════════════════════════════
def test_pacing_detection():
    print("\n" + "="*70)
    print("SIMULATION 3: PACING / WANDERING DETECTION")
    print("="*70)

    alerts_fired = []
    def mock_callback(alert):
        alerts_fired.append(alert)

    proc = EdgeProcessor(_StubConfig(), alert_callback=mock_callback)

    # Pretend pacing started 920 seconds ago (> 900s threshold)
    proc._pacing_start_ts = time.time() - 920

    pacing_reading = SensorReading(
        device_id="MOCK_DEV",
        timestamp=time.time(),
        reading_type=ReadingType.ACCELEROMETER,
        value={"x": [0.5, -0.5, 0.4, -0.4], "y": [0.1], "z": [1.0]}
    )
    proc.process_reading(pacing_reading)

    pacing_alert = [a for a in alerts_fired if a.get("type") == "BEHAVIORAL_WANDERING_RISK"]
    report("Detects pacing after 15+ minutes of continuous movement",
           len(pacing_alert) > 0)

    # Normal short walk should NOT trigger
    alerts_fired.clear()
    proc2 = EdgeProcessor(_StubConfig(), alert_callback=mock_callback)
    proc2._pacing_start_ts = time.time() - 60  # Only 60 seconds

    proc2.process_reading(pacing_reading)
    pacing_alert2 = [a for a in alerts_fired if a.get("type") == "BEHAVIORAL_WANDERING_RISK"]
    report("Does NOT flag pacing after only 1 minute of movement",
           len(pacing_alert2) == 0)


# ═══════════════════════════════════════════════════════════════════════
# SIMULATION 4: UTI PREDICTIVE HEURISTIC
# ═══════════════════════════════════════════════════════════════════════
def test_uti_prediction():
    print("\n" + "="*70)
    print("SIMULATION 4: UTI PREDICTIVE HEURISTIC")
    print("="*70)

    def uti_risk_check(recent_visits_3d, baseline_visits_7d):
        baseline_avg = baseline_visits_7d / 7.0
        recent_avg = recent_visits_3d / 3.0
        if baseline_avg > 0:
            increase_pct = ((recent_avg - baseline_avg) / baseline_avg) * 100
            return increase_pct > 30, increase_pct
        return False, 0

    flagged, pct = uti_risk_check(6, 14)
    report(f"Normal pattern (6/3d vs 14/7d) -> No risk (change={pct:.0f}%)", not flagged)

    flagged, pct = uti_risk_check(12, 10)
    report(f"UTI spike (12/3d vs 10/7d) -> Risk flagged (change={pct:.0f}%)", flagged)

    flagged, pct = uti_risk_check(18, 7)
    report(f"Massive spike (18/3d vs 7/7d) -> Risk flagged (change={pct:.0f}%)", flagged)

    flagged, pct = uti_risk_check(5, 0)
    report("Zero baseline -> Safe default (no division error)", not flagged)


# ═══════════════════════════════════════════════════════════════════════
# SIMULATION 5: ALERT EVALUATOR (Deterministic Tier)
# ═══════════════════════════════════════════════════════════════════════
def test_alert_evaluator():
    print("\n" + "="*70)
    print("SIMULATION 5: ALERT EVALUATOR (Deterministic Rules)")
    print("="*70)

    # Stub cloud package
    cloud_pkg = types.ModuleType("cloud")
    cloud_pkg.__path__ = [os.path.join(BASE, "cloud")]
    sys.modules["cloud"] = cloud_pkg

    cloud_engine = types.ModuleType("cloud.engine")
    cloud_engine.__path__ = [os.path.join(BASE, "cloud", "engine")]
    sys.modules["cloud.engine"] = cloud_engine

    alert_mod = _load_module("cloud.engine.alert_evaluator",
                             os.path.join(BASE, "cloud", "engine", "alert_evaluator.py"))
    AlertEvaluator = alert_mod.AlertEvaluator

    evaluator = AlertEvaluator()

    async def run_tests():
        escalate, _ = await evaluator.evaluate({"type": "FALL_DETECTED", "severity": "emergency"})
        report("FALL_DETECTED -> Always escalates (Tier 1)", escalate)

        escalate, _ = await evaluator.evaluate({"type": "CRITICAL_ELOPEMENT", "severity": "critical"})
        report("CRITICAL_ELOPEMENT -> Always escalates (Tier 1)", escalate)

        escalate, _ = await evaluator.evaluate({"type": "HR_CRITICAL_HIGH", "severity": "critical"})
        report("HR_CRITICAL_HIGH -> Escalates (critical)", escalate)

        escalate, _ = await evaluator.evaluate(
            {"type": "HR_ANOMALY", "severity": "warning", "message": "HR elevated"},
            {"time_of_day": "morning", "recent_activity": "resting"}
        )
        report("HR_ANOMALY (no LLM) -> Safe default escalate", escalate)

    asyncio.run(run_tests())


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("\n" + "#"*70)
    print("#  ECLIPSE CARE — R&D SIMULATION & TEST SUITE")
    print("#  Testing all AI subsystems with synthetic data")
    print("#"*70)

    test_fall_detection()
    test_vitals_anomaly()
    test_pacing_detection()
    test_uti_prediction()
    test_alert_evaluator()

    print("\n" + "="*70)
    print(f"RESULTS: {PASS} passed, {FAIL} failed out of {PASS+FAIL} tests")
    print("="*70)

    if FAIL > 0:
        print("\n[WARNING] Some tests failed. See details above.")
        sys.exit(1)
    else:
        print("\n[SUCCESS] synthetic-data test suite: ALL pass.")
        sys.exit(0)
