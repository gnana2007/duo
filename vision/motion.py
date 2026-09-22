"""
Triple-Swipe Gesture Detector v3
────────────────────────────────
Detects 3 deliberate left-hand or right-hand swipes within a short time window.
Left hand ×3 = previous environment.
Right hand ×3 = next environment.
Uses smoothing and cooldown to avoid accidental triggers.
"""
import time
from collections import deque
from typing import List, Dict, Any
from config import settings


class MotionTracker:
    """Tracks hand positions over time and detects triple-swipe gestures."""

    def __init__(self):
        # Track each hand separately
        self._left_history = deque(maxlen=30)   # (time, x, y)
        self._right_history = deque(maxlen=30)

        # Count swipe events within a time window
        self._left_swipes = deque(maxlen=10)    # timestamps of detected left-hand swipes
        self._right_swipes = deque(maxlen=10)

        self.last_trigger_time = 0.0
        self.cooldown = 2.5  # seconds between triple-swipe triggers
        self.swipe_window = 2.0  # seconds — all 3 swipes must happen within this window
        self.min_velocity = 400  # px/s for a single swipe

    def update(self, hands: List[Dict[str, Any]]) -> int:
        """
        Returns:
          -1 = left-hand triple-swipe detected (go to PREVIOUS environment)
          +1 = right-hand triple-swipe detected (go to NEXT environment)
           0 = no triple-swipe
        """
        now = time.time()

        if now - self.last_trigger_time < self.cooldown:
            return 0

        if not hands:
            return 0

        # Identify left vs right hands
        for hand in hands:
            handedness = hand.get("handedness", "").lower()
            px, py = hand["palm_center"]

            if "left" in handedness:
                self._left_history.append((now, px, py))
                swipe = self._detect_single_swipe(self._left_history)
                if swipe != 0:
                    self._left_swipes.append(now)
            elif "right" in handedness:
                self._right_history.append((now, px, py))
                swipe = self._detect_single_swipe(self._right_history)
                if swipe != 0:
                    self._right_swipes.append(now)
            else:
                # Unknown handedness — use x-position heuristic
                # Person on camera left = likely their right hand (mirrored)
                if px < settings.CAPTURE_WIDTH // 2:
                    self._right_history.append((now, px, py))
                    swipe = self._detect_single_swipe(self._right_history)
                    if swipe != 0:
                        self._right_swipes.append(now)
                else:
                    self._left_history.append((now, px, py))
                    swipe = self._detect_single_swipe(self._left_history)
                    if swipe != 0:
                        self._left_swipes.append(now)

        # Check for triple-swipe within window
        # Left hand ×3 = go to PREVIOUS environment
        recent_left = [t for t in self._left_swipes if now - t < self.swipe_window]
        if len(recent_left) >= 3:
            self.last_trigger_time = now
            self._left_swipes.clear()
            self._left_history.clear()
            return -1

        # Right hand ×3 = go to NEXT environment
        recent_right = [t for t in self._right_swipes if now - t < self.swipe_window]
        if len(recent_right) >= 3:
            self.last_trigger_time = now
            self._right_swipes.clear()
            self._right_history.clear()
            return +1

        return 0

    def _detect_single_swipe(self, history: deque) -> int:
        """Detects a single fast horizontal sweep in the history. Returns -1/+1/0."""
        if len(history) < 4:
            return 0

        # Look at the last ~0.2 seconds
        now = history[-1][0]
        recent = [(t, x, y) for t, x, y in history if now - t < 0.25]

        if len(recent) < 3:
            return 0

        t_old, x_old, _ = recent[0]
        t_new, x_new, _ = recent[-1]
        dt = t_new - t_old

        if dt < 0.05:
            return 0

        vx = (x_new - x_old) / dt

        if abs(vx) > self.min_velocity:
            # Clear recent history to avoid double-counting
            history.clear()
            return 1 if vx > 0 else -1

        return 0
