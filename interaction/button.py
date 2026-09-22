"""
Top-Center Virtual Capture Button v2
────────────────────────────────────
Purely gesture-activated: the user hovers their index fingertip or palm
inside the target zone. Progress fills over BUTTON_HOVER_S seconds.
The button's visual rendering is handled entirely by UIRenderer (PIL overlays).
This module only tracks state.
"""
import time
from typing import List, Dict, Any
import numpy as np
from config import settings


class VirtualButton:
    def __init__(self):
        w, h = settings.CAPTURE_WIDTH, settings.CAPTURE_HEIGHT
        self.cx = int(w * settings.TOP_BUTTON_X_RATIO)
        self.cy = int(h * settings.TOP_BUTTON_Y_RATIO)
        self.radius = settings.TOP_BUTTON_RADIUS
        self.hover_duration = settings.BUTTON_HOVER_S
        self.hover_start = None
        self.is_hovered = False
        self.is_triggered = False
        self.progress = 0.0

    def update(self, hands: List[Dict[str, Any]]) -> bool:
        """Returns True at the exact moment the button triggers."""
        inside = False
        for hand in hands:
            for pt in [hand["index_tip"], hand["palm_center"]]:
                if np.hypot(pt[0] - self.cx, pt[1] - self.cy) <= self.radius:
                    inside = True
                    break
            if inside:
                break

        now = time.time()
        triggered = False

        if inside:
            if not self.is_hovered:
                self.is_hovered = True
                self.hover_start = now
                self.progress = 0.0
            else:
                self.progress = min(1.0, (now - self.hover_start) / self.hover_duration)
                if self.progress >= 1.0 and not self.is_triggered:
                    self.is_triggered = True
                    triggered = True
        else:
            self.is_hovered = False
            self.is_triggered = False
            self.hover_start = None
            self.progress = 0.0

        return triggered
