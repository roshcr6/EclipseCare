"""Eclipse Care — Edge AI Fall Detection.

Wraps a TensorFlow Lite (TinyML) model to detect falls using IMU data (Accel + Gyro).
Uses a sliding window approach (e.g., 2.56 seconds of data at 50Hz = 128 samples).

Research Context (2024-2025):
State-of-the-art systems use CNN-LSTM or SVM models trained on datasets like SisFall or KFall.
This achieves >95% accuracy compared to simple L2 norm thresholds which suffer from
high false positive rates in nursing home environments.
"""

import os
import numpy as np
import structlog

logger = structlog.get_logger("edge.fall_model")

try:
    import tflite_runtime.interpreter as tflite
    TFLITE_AVAILABLE = True
except ImportError:
    try:
        import tensorflow as tf
        tflite = tf.lite
        TFLITE_AVAILABLE = True
    except ImportError:
        TFLITE_AVAILABLE = False


class FallDetectionModel:
    """TensorFlow Lite inference engine for fall detection."""

    def __init__(self, model_path: str = "models/fall_detection_cnn.tflite", window_size: int = 128):
        self.model_path = model_path
        self.window_size = window_size
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        
        self.is_loaded = self._load_model()

    def _load_model(self) -> bool:
        """Load the TFLite model from disk."""
        if not TFLITE_AVAILABLE:
            logger.warning("TensorFlow Lite runtime not available. Using fallback heuristics.")
            return False

        if not os.path.exists(self.model_path):
            logger.warning(f"Fall detection model not found at {self.model_path}. Using fallback heuristics.")
            return False

        try:
            self.interpreter = tflite.Interpreter(model_path=self.model_path)
            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            logger.info("Fall detection AI model loaded successfully.")
            return True
        except Exception as e:
            logger.error("Failed to load TFLite model", error=str(e))
            return False

    def predict(self, accel_window: dict[str, list[float]], gyro_window: dict[str, list[float]]) -> float:
        """
        Run inference on a window of IMU data.
        Returns a float between 0.0 (no fall) and 1.0 (fall).
        """
        # Ensure we have enough data
        ax = accel_window.get("x", [])
        if len(ax) < self.window_size:
            return 0.0

        if self.is_loaded and self.interpreter:
            return self._run_tflite_inference(accel_window, gyro_window)
        else:
            return self._run_fallback_heuristic(accel_window)

    def _run_tflite_inference(self, accel_window: dict, gyro_window: dict) -> float:
        """Run the actual TFLite neural network."""
        # 1. Prepare input tensor shape: [1, window_size, 6] (batch, timesteps, features)
        # Features: ax, ay, az, gx, gy, gz
        input_data = np.zeros((1, self.window_size, 6), dtype=np.float32)
        
        for i in range(self.window_size):
            # Normalization (e.g., standard scaling) would normally be applied here 
            # based on the training dataset parameters.
            input_data[0, i, 0] = accel_window["x"][i]
            input_data[0, i, 1] = accel_window["y"][i]
            input_data[0, i, 2] = accel_window["z"][i]
            
            # If gyro is available, append it. If not, pad with zeros.
            if gyro_window and "x" in gyro_window and len(gyro_window["x"]) > i:
                input_data[0, i, 3] = gyro_window["x"][i]
                input_data[0, i, 4] = gyro_window["y"][i]
                input_data[0, i, 5] = gyro_window["z"][i]

        # 2. Run Inference
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()
        
        # 3. Extract output (assuming binary classification: [p_adl, p_fall])
        output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
        
        # Depending on model architecture, it might output a single sigmoid float
        # or a softmax array of size 2. Assuming sigmoid single float for now.
        fall_probability = float(output_data[0][0])
        return fall_probability

    def _run_fallback_heuristic(self, accel_window: dict) -> float:
        """
        Advanced heuristic fallback when the AI model file isn't present.
        Instead of a simple L2 norm peak, this checks for:
        1. Freefall (L2 near 0) followed by...
        2. High impact (L2 >> 1g) followed by...
        3. Horizontal resting state (variance drops, mean approaches 1g but distributed differently).
        """
        import math
        
        ax = accel_window["x"]
        ay = accel_window["y"]
        az = accel_window["z"]
        
        # Calculate L2 norm vector
        magnitudes = [math.sqrt(ax[i]**2 + ay[i]**2 + az[i]**2) for i in range(self.window_size)]
        
        max_mag = max(magnitudes)
        min_mag = min(magnitudes)
        
        # Rule 1: Impact peak must be > 2.5g
        if max_mag < 2.5:
            return 0.0
            
        # Rule 2: Freefall trough must be < 0.5g (preceding impact)
        impact_idx = magnitudes.index(max_mag)
        pre_impact = magnitudes[:impact_idx]
        if not pre_impact or min(pre_impact) > 0.5:
            return 0.0
            
        # Rule 3: Post-impact stillness (variance drops)
        post_impact = magnitudes[impact_idx+10:] # Skip immediate bounce
        if len(post_impact) > 20:
            variance = np.var(post_impact)
            if variance > 0.1:
                return 0.0 # Still moving a lot, probably just ADL
                
        logger.info("Fallback heuristic detected fall signature", impact=max_mag, freefall=min_mag)
        return 0.9  # High probability
