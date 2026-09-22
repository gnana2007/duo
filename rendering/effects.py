"""
Visual Effects Renderer v2
──────────────────────────
Camera flash, particle bursts — all drawn with anti-aliased OpenCV.
"""
import numpy as np
import cv2
from config import settings


class EffectsRenderer:

    def apply_flash(self, canvas: np.ndarray, intensity: float = 0.85) -> np.ndarray:
        """Bright white camera-flash overlay fading by intensity."""
        flash = np.full_like(canvas, 255)
        return cv2.addWeighted(flash, intensity, canvas, 1.0 - intensity, 0)
