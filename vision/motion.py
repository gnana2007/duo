"""
TimeSensei Responsive Single-Palm Swipe Detector
────────────────────────────────────────────────
Instantly detects a single, fast horizontal swipe of the hand/palm.
Swipe Right -> Next Timeline (+1)
Swipe Left  -> Previous Timeline (-1)
Fast cooldown (0.60s) ensures immediate responsiveness without accidental multi-triggers.
"""
import time
from collections import deque
from typing import List, Dict, Any
from config import settings


class MotionTracker:
    """Tracks hand velocity and detects immediate single-palm swipes."""

    def __init__(self):
        # Track hand history: (time, x, y)
        self._history = deque(maxlen=25)
        self.last_trigger_time = 0.0
        self.cooldown = 0.60  # Fast, snappy cooldown
        self.min_velocity = 380.0  # px/s
        self.min_displacement = 75.0  # px

    def update(self, hands: List[Dict[str, Any]]) -> int:
        """
        Returns:
          -1 = Swipe Left (Previous Timeline)
          +1 = Swipe Right (Next Timeline)
           0 = No Swipe
        """
        now = time.time()

        if now - self.last_trigger_time < self.cooldown:
            return 0

        if not hands:
            self._history.clear()
            return 0

        # Prioritize open palm or dominant hand
        target_hand = hands[0]
        for h in hands:
            if h.get("is_open_palm", False):
                target_hand = h
                break

        px, py = target_hand["palm_center"]
        self._history.append((now, px, py))

        if len(self._history) < 3:
            return 0

        # Analyze motion over the last 0.18 seconds
        recent = [(t, x, y) for t, x, y in self._history if now - t <= 0.20]
        if len(recent) < 2:
            return 0

        t_old, x_old, _ = recent[0]
        t_new, x_new, _ = recent[-1]
        dt = t_new - t_old
        dx = x_new - x_old

        if dt < 0.04:
            return 0

        vx = dx / dt

        # Single swipe detection
        if abs(vx) >= self.min_velocity and abs(dx) >= self.min_displacement:
            self.last_trigger_time = now
            self._history.clear()
            # Moving left in screen coordinates -> previous; right -> next
            return 1 if vx > 0 else -1

        return 0
