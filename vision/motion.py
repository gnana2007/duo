"""
TimeSensei Double-Palm Swipe Detector
─────────────────────────────────────
Requires at least two consecutive swipes in the same direction to switch backgrounds:
  1st Swipe: Registers motion intent (shows "SWIPE AGAIN" hint)
  2nd Swipe within 2.0s: Triggers background environment change (-1 = Prev, +1 = Next)
Prevents accidental single-palm triggers while giving intuitive tactile control.
"""
import time
from collections import deque
from typing import List, Dict, Any


class MotionTracker:
    """Tracks hand velocity and requires a double swipe to trigger background switching."""

    def __init__(self):
        # Track hand history: (time, x, y)
        self._history = deque(maxlen=25)
        self.last_trigger_time = 0.0
        self.cooldown = 0.70  # Cooldown after successful double swipe
        self.min_velocity = 300.0  # px/s
        self.min_displacement = 65.0  # px

        # Double-swipe state
        self.first_swipe_dir = 0        # -1 (Left) or +1 (Right)
        self.first_swipe_time = 0.0     # Timestamp of 1st swipe
        self.double_swipe_window = 2.0  # Max seconds allowed for 2nd swipe
        self.inter_swipe_delay = 0.20   # Min gap so single continuous swing doesn't count as 2

    @property
    def pending_direction(self) -> int:
        """Returns pending swipe direction (-1 or +1) if waiting for 2nd swipe, else 0."""
        if self.first_swipe_dir != 0:
            if time.time() - self.first_swipe_time <= self.double_swipe_window:
                return self.first_swipe_dir
            self.first_swipe_dir = 0
        return 0

    def update(self, hands: List[Dict[str, Any]]) -> int:
        """
        Returns:
          -1 = Double Swipe Left (Previous Timeline)
          +1 = Double Swipe Right (Next Timeline)
           0 = Waiting or No Double Swipe
        """
        now = time.time()

        # Expire pending 1st swipe if window exceeded
        if self.first_swipe_dir != 0 and (now - self.first_swipe_time > self.double_swipe_window):
            self.first_swipe_dir = 0

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

        # Analyze motion over the last 0.20 seconds
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

        # Swipe motion detected
        if abs(vx) >= self.min_velocity and abs(dx) >= self.min_displacement:
            swipe_dir = 1 if vx > 0 else -1

            # Case 1: First swipe
            if self.first_swipe_dir == 0:
                self.first_swipe_dir = swipe_dir
                self.first_swipe_time = now
                self._history.clear()
                return 0  # Do not trigger background change yet!

            # Case 2: Second swipe in the same direction within window
            if self.first_swipe_dir == swipe_dir:
                elapsed = now - self.first_swipe_time
                if elapsed >= self.inter_swipe_delay:
                    # Double swipe successfully achieved!
                    self.first_swipe_dir = 0
                    self.last_trigger_time = now
                    self._history.clear()
                    return swipe_dir

            # Case 3: Swiped in opposite direction -> reset 1st swipe to the new direction
            if self.first_swipe_dir != swipe_dir:
                self.first_swipe_dir = swipe_dir
                self.first_swipe_time = now
                self._history.clear()
                return 0

        return 0
