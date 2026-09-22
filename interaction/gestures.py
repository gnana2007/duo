"""
TimeSensei Gesture Arbitration & Manager
────────────────────────────────────────
Centralized gesture recognition with temporal hysteresis, state-awareness,
and anti-flicker cooldown guards.

Gestures:
  ✋ Open Palm Hold (0.75s)  → FREEZE TIME (creates grounded temporal clone)
  ✌️ Peace / Victory (0.60s)  → Photo Countdown Trigger
  👍 Thumbs-Up (0.35s)       → Reveal QR Code Sharing Card
  ✊ Closed Fist             → Suppress QR / Grab and Move Clone
  ☝️ Pointing Up (0.80s)     → Temporal Rewind Trigger
"""
import time
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from config import settings


def is_fist(hand: Dict[str, Any]) -> bool:
    """Detect if hand is in a closed fist."""
    g = hand.get("gesture", "")
    conf = hand.get("gesture_confidence", 0.0)

    if g == "Closed_Fist" and conf >= 0.40:
        return True

    pts = hand.get("all_landmarks")
    if pts and len(pts) == 21:
        palm_cx, palm_cy = hand.get("palm_center", (pts[0][0], pts[0][1]))
        wrist = pts[0]
        hand_scale = max(20.0, float(np.hypot(palm_cx - wrist[0], palm_cy - wrist[1])))

        d_index = np.hypot(pts[8][0] - palm_cx, pts[8][1] - palm_cy)
        d_mid = np.hypot(pts[12][0] - palm_cx, pts[12][1] - palm_cy)
        d_ring = np.hypot(pts[16][0] - palm_cx, pts[16][1] - palm_cy)
        d_pinky = np.hypot(pts[20][0] - palm_cx, pts[20][1] - palm_cy)

        fingers_curled = (
            d_index < hand_scale * 1.10 and
            d_mid < hand_scale * 1.10 and
            d_ring < hand_scale * 1.10 and
            d_pinky < hand_scale * 1.10
        )

        thumb_tip = pts[4]
        index_mcp = pts[5]
        d_thumb = np.hypot(thumb_tip[0] - index_mcp[0], thumb_tip[1] - index_mcp[1])
        thumb_tucked = d_thumb < hand_scale * 0.90

        if fingers_curled and thumb_tucked and g != "Thumb_Up":
            return True

    return False


def is_thumb_up(hand: Dict[str, Any]) -> bool:
    """Detect if hand is in an unambiguous, genuine thumbs-up gesture."""
    if is_fist(hand):
        return False

    g = hand.get("gesture", "")
    conf = hand.get("gesture_confidence", 0.0)
    pts = hand.get("all_landmarks")
    if not pts or len(pts) < 21:
        return g == "Thumb_Up" and conf >= 0.65

    palm_cx, palm_cy = hand.get("palm_center", (pts[0][0], pts[0][1]))
    wrist = pts[0]
    hand_scale = max(20.0, float(np.hypot(palm_cx - wrist[0], palm_cy - wrist[1])))

    thumb_tip = pts[4]
    index_mcp = pts[5]

    thumb_pointing_up = (thumb_tip[1] < index_mcp[1] - 25) and (thumb_tip[1] < pts[3][1] - 12)
    d_thumb = np.hypot(thumb_tip[0] - index_mcp[0], thumb_tip[1] - index_mcp[1])
    thumb_extended = d_thumb > hand_scale * 0.60

    fingers_curled = (
        pts[8][1] > pts[6][1] - 5 and
        pts[12][1] > pts[10][1] - 5 and
        pts[16][1] > pts[14][1] - 5 and
        pts[20][1] > pts[18][1] - 5
    )

    if g == "Thumb_Up" and conf >= 0.50 and thumb_pointing_up:
        return True

    if thumb_pointing_up and thumb_extended and fingers_curled and g not in ("Closed_Fist", "Victory", "Open_Palm"):
        return True

    return False


class GestureManager:
    """Centralized temporal gesture evaluator for TimeSensei."""

    def __init__(self):
        self._hold = {}          # key -> start_time
        self._cooldown = {}      # key -> last_trigger_time
        self.last_fist_time = 0.0
        self.last_freeze_time = 0.0

    def _check_hold_progress(self, key: str, active: bool, duration: float, cooldown: float = 2.0) -> Tuple[bool, float]:
        now = time.time()
        last = self._cooldown.get(key, 0.0)

        # Still in cooldown
        if now - last < cooldown:
            self._hold.pop(key, None)
            return False, 0.0

        if active:
            if key not in self._hold:
                self._hold[key] = now
                return False, 0.0
            elapsed = now - self._hold[key]
            progress = min(1.0, elapsed / duration)
            if elapsed >= duration:
                self._cooldown[key] = now
                self._hold.pop(key, None)
                return True, 1.0
            return False, progress
        else:
            self._hold.pop(key, None)
            return False, 0.0

    # ── TimeSensei Signature Gesture: Two-Finger Victory Freeze ──

    def check_victory_freeze(self, hands: List[Dict[str, Any]], qr_active: bool = False) -> Tuple[bool, float, Optional[Tuple[int, int]]]:
        """
        ✌️ First two fingers in Victory sign held for settings.VICTORY_FREEZE_HOLD_S.
        Returns: (triggered: bool, progress: float [0..1], victory_pos: (x, y) or None)
        """
        if qr_active or any(is_fist(h) for h in hands):
            self._hold.pop("victory_freeze", None)
            return False, 0.0, None

        victory_hands = [
            h for h in hands
            if h.get("is_victory", False) or (h.get("gesture") == "Victory" and h.get("gesture_confidence", 0) > 0.40)
        ]
        has_victory = len(victory_hands) > 0
        victory_pos = None
        if has_victory:
            vh = victory_hands[0]
            victory_pos = vh.get("victory_center") or vh.get("index_tip") or vh.get("palm_center")

        triggered, progress = self._check_hold_progress(
            "victory_freeze",
            has_victory,
            duration=settings.VICTORY_FREEZE_HOLD_S,
            cooldown=settings.VICTORY_FREEZE_COOLDOWN_S
        )
        if triggered:
            self.last_freeze_time = time.time()

        return triggered, progress, victory_pos

    # Alias for compatibility
    check_palm_freeze = check_victory_freeze

    # ── Photo Countdown Trigger: Thumbs-Up ──

    def check_capture_trigger(self, hands: List[Dict[str, Any]]) -> bool:
        """👍 Thumbs-Up held for settings.PHOTO_CAPTURE_HOLD_S -> triggers photo countdown."""
        has_thumb = any(is_thumb_up(h) for h in hands)
        triggered, _ = self._check_hold_progress("capture", has_thumb, settings.PHOTO_CAPTURE_HOLD_S, cooldown=3.0)
        return triggered

    # ── QR Code Popups: Thumbs Up / Fist ──

    def check_fist(self, hands: List[Dict[str, Any]]) -> bool:
        """
        ✊ Closed fist is active. Suppresses QR popup and can initiate memory drag.
        """
        has_fist = any(is_fist(h) for h in hands)
        if has_fist:
            self.last_fist_time = time.time()
            self._hold.pop("thumb_qr", None)
        return has_fist

    def check_thumb_trigger(self, hands: List[Dict[str, Any]]) -> bool:
        """
        👍 Thumb_Up held for settings.THUMB_HOLD_S -> show QR sharing popup.
        """
        now = time.time()
        # Cooldown guard: cannot open QR within 1.2s of seeing a fist
        if now - self.last_fist_time < 1.2:
            self._hold.pop("thumb_qr", None)
            return False

        if any(is_fist(h) for h in hands):
            self.last_fist_time = now
            self._hold.pop("thumb_qr", None)
            return False

        has_thumb = any(is_thumb_up(h) for h in hands)
        triggered, _ = self._check_hold_progress("thumb_qr", has_thumb, settings.THUMB_HOLD_S, cooldown=1.5)
        return triggered

    # ── Rewind Gesture Trigger: Pointing Up ──

    def check_rewind_trigger(self, hands: List[Dict[str, Any]]) -> bool:
        """☝️ Pointing Up held for 0.8s -> triggers rewind."""
        has_pointing = any(h.get("is_pointing_up", False) for h in hands)
        triggered, _ = self._check_hold_progress("rewind", has_pointing, duration=0.80, cooldown=3.5)
        return triggered

    # ── Start Screen Dwell / Button Hover ──

    def check_hover_dwell(self, hand_pts: List[Tuple[int, int]], target_x: int, target_y: int, radius: int, duration: float) -> Tuple[bool, float]:
        """Checks if any hand coordinate dwells within target circle for duration."""
        inside = any(np.hypot(pt[0] - target_x, pt[1] - target_y) <= radius for pt in hand_pts)
        return self._check_hold_progress("dwell_start", inside, duration, cooldown=1.0)
