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
        # Per-hand history: hand_id -> deque of (time, x, y)
        self._hand_histories: Dict[int, deque] = {}
        self.last_trigger_time = 0.0
        self.cooldown = 0.60            # Cooldown after successful background switch
        self.min_velocity = 160.0       # Natural, smooth swipe speed (px/s)
        self.min_displacement = 50.0   # Minimum horizontal hand travel (px)

        # Double-swipe state machine
        self.first_swipe_dir = 0        # -1 (Left/Prev) or +1 (Right/Next)
        self.first_swipe_time = 0.0     # Timestamp of 1st swipe
        self.double_swipe_window = 2.2  # Seconds allowed for 2nd swipe
        self.inter_swipe_delay = 0.14   # Minimum gap before 2nd swipe can trigger

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
        Tracks hand movements and triggers background transitions on double-swipe.
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
            self._hand_histories.clear()
            return 0

        # Prune inactive hands from tracking dictionary
        active_ids = {h.get("id", idx) for idx, h in enumerate(hands)}
        self._hand_histories = {k: v for k, v in self._hand_histories.items() if k in active_ids}

        detected_swipe_dir = 0

        # Scan each visible hand independently
        for idx, h in enumerate(hands):
            # Clenched fists do not trigger swipe transitions
            if h.get("is_fist", False):
                continue

            hand_id = h.get("id", idx)
            if hand_id not in self._hand_histories:
                self._hand_histories[hand_id] = deque(maxlen=20)

            history = self._hand_histories[hand_id]
            px, py = h["palm_center"]
            history.append((now, px, py))

            if len(history) < 2:
                continue

            # Analyze recent movement over past 0.25 seconds
            recent = [(t, x, y) for t, x, y in history if now - t <= 0.25]
            if len(recent) < 2:
                continue

            t_old, x_old, _ = recent[0]
            t_new, x_new, _ = recent[-1]
            dt = t_new - t_old
            dx = x_new - x_old

            if dt < 0.03:
                continue

            vx = dx / dt

            # Check if this hand achieved the swipe threshold
            if abs(vx) >= self.min_velocity and abs(dx) >= self.min_displacement:
                detected_swipe_dir = 1 if vx > 0 else -1
                history.clear()
                break

        if detected_swipe_dir == 0:
            return 0

        # State machine arbitration:
        # Case 1: First swipe detected -> arm pending state
        if self.first_swipe_dir == 0:
            self.first_swipe_dir = detected_swipe_dir
            self.first_swipe_time = now
            return 0  # Do not switch yet; display on-screen prompt

        # Case 2: Second swipe in the SAME direction within window
        elif self.first_swipe_dir == detected_swipe_dir:
            elapsed = now - self.first_swipe_time
            if elapsed >= self.inter_swipe_delay:
                # Double-swipe completed! Trigger timeline transition!
                self.first_swipe_dir = 0
                self.last_trigger_time = now
                self._hand_histories.clear()
                return detected_swipe_dir

        # Case 3: Hand motion in opposite direction
        # When swiping right, the hand naturally returns to the left to prepare for swipe 2.
        # We do NOT cancel the pending swipe on return motion!
        # Only switch intent if the opposite motion occurs after a deliberate pause (> 0.55s).
        else:
            if (now - self.first_swipe_time) > 0.55:
                self.first_swipe_dir = detected_swipe_dir
                self.first_swipe_time = now

        return 0
