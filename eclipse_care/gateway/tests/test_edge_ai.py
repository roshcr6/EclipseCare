"""Tests for the Eclipse Care Edge AI Pipeline."""

import time
import math
import unittest
import numpy as np

from eclipse_care.gateway.edge.fall_model import FallDetectionModel
from eclipse_care.gateway.edge.vitals_anomaly import VitalsAnomalyDetector


class TestEdgeAI(unittest.TestCase):
    
    def setUp(self):
        self.fall_model = FallDetectionModel(window_size=128)
        self.vitals_detector = VitalsAnomalyDetector(training_interval_sec=0) # force train

    def test_fall_detection_adl_suppression(self):
        """Verify that Activities of Daily Living (ADL) don't trigger false positives."""
        # Synthetic walking data: roughly 1g magnitude with small variance
        walking_ax = [1.0 + math.sin(i * 0.1) * 0.2 for i in range(128)]
        walking_ay = [math.cos(i * 0.1) * 0.2 for i in range(128)]
        walking_az = [math.sin(i * 0.2) * 0.1 for i in range(128)]
        
        accel_window = {"x": walking_ax, "y": walking_ay, "z": walking_az}
        
        prob = self.fall_model.predict(accel_window, gyro_window={})
        
        # Should be near 0 probability of a fall
        self.assertLess(prob, 0.5)

    def test_fall_detection_impact_signature(self):
        """Verify that a fall signature (freefall -> impact -> stillness) is detected."""
        ax = [1.0] * 128
        ay = [0.0] * 128
        az = [0.0] * 128
        
        # 1. Freefall (L2 approaches 0)
        for i in range(40, 60):
            ax[i] = 0.1
            
        # 2. Impact (L2 spikes > 2.5g)
        ax[60] = 3.5
        ay[60] = 2.0
        
        # 3. Rest (Orientation changes, variance drops)
        for i in range(65, 128):
            ax[i] = 0.0
            ay[i] = 1.0 # lying on side
            az[i] = 0.0
            
        accel_window = {"x": ax, "y": ay, "z": az}
        
        prob = self.fall_model.predict(accel_window, gyro_window={})
        
        # Fall probability should be high
        self.assertGreater(prob, 0.8)

    def test_vital_sign_anomaly(self):
        """Verify Isolation Forest learns a baseline and catches deviations."""
        # Resident normally has HR around 60-70
        for _ in range(100):
            self.vitals_detector.add_reading(hr=np.random.normal(65, 2))
            
        # 1. Normal reading should not alert
        normal_reading = 66
        self.assertFalse(self.vitals_detector.is_anomalous(hr=normal_reading))
        
        # 2. Gradual deterioration (e.g. approaching 95, normally not a hard alert)
        # But for this resident whose norm is 65, this is a massive anomaly.
        deteriorating_reading = 95
        
        # This will either trigger the ML model (if sklearn installed) or the Z-score fallback.
        # Mean = ~65, Std = ~2. Z-score for 95 = (95-65)/2 = 15.0 (Way > 3.0)
        is_anomalous = self.vitals_detector.is_anomalous(hr=deteriorating_reading)
        self.assertTrue(is_anomalous)


if __name__ == "__main__":
    unittest.main()
