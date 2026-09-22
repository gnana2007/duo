"""
TimeSensei Gesture Arbitration & Manager
────────────────────────────────────────
Centralized gesture recognition with temporal hysteresis, state-awareness,
and anti-flicker cooldown guards.

Gestures:
  ✌️ Peace / Victory (0.20s)  → Photo Countdown Trigger (Latched)
  👍 Open Thumb (0.18s)       → Reveal QR Code Sharing Card (Latched at bottom-right)
  ✊ Closed Fist (0.12s)      → Dismiss QR Code Sharing Card (Latched closed)
  ✋ Open Palm (0.35s)        → Freeze Time (creates grounded temporal clone)
  ☝️ Pointing Up (0.80s)      → Temporal Rewind Trigger
"""
import time
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from config import settings


def is_fist(hand: Dict[str, Any]) -> bool:
    """Detect if hand is in a closed fist."""
    if hand.get("is_fist", False):
        return True

    g = hand.get("gesture", "")
    conf = hand.get("gesture_confidence", 0.0)
    if g == "Closed_Fist" and conf >= 0.40:
        return True

    pts = hand.get("all_landmarks")
    if pts and len(pts) == 21:
        palm_cx, palm_cy = hand.get("palm_center", (pts[0][0], pts[0][1]))
        wrist = pts[0]
        hand_scale = max(20.0, float(np.hypot(palm_cx - wrist[0], palm_cy - wrist[1])))

        d_thumb = np.hypot(pts[4][0] - palm_cx, pts[4][1] - palm_cy)
        d_index = np.hypot(pts[8][0] - palm_cx, pts[8][1] - palm_cy)
        d_mid = np.hypot(pts[12][0] - palm_cx, pts[12][1] - palm_cy)
        d_ring = np.hypot(pts[16][0] - palm_cx, pts[16][1] - palm_cy)
        d_pinky = np.hypot(pts[20][0] - palm_cx, pts[20][1] - palm_cy)

        all_curled = (
            d_thumb < hand_scale * 0.95 and
            d_index < hand_scale * 1.05 and
            d_mid < hand_scale * 1.05 and
            d_ring < hand_scale * 1.05 and
            d_pinky < hand_scale * 1.05
        )
        if all_curled and g not in ("Open_Palm", "Victory", "Thumb_Up"):
            return True

    return False


def is_thumb_up(hand: Dict[str, Any]) -> bool:
    """Detect if hand is in an unambiguous open thumb / thumbs-up gesture."""
    if is_fist(hand):
        return False

    if hand.get("is_thumb_open", False):
        return True

    g = hand.get("gesture", "")
    conf = hand.get("gesture_confidence", 0.0)
    if g == "Thumb_Up" and conf >= 0.45:
        return True

    pts = hand.get("all_landmarks")
    if not pts or len(pts) < 21:
        return False

    palm_cx, palm_cy = hand.get("palm_center", (pts[0][0], pts[0][1]))
    wrist = pts[0]
    hand_scale = max(20.0, float(np.hypot(palm_cx - wrist[0], palm_cy - wrist[1])))

    d_thumb = np.hypot(pts[4][0] - palm_cx, pts[4][1] - palm_cy)
    d_index = np.hypot(pts[8][0] - palm_cx, pts[8][1] - palm_cy)
    d_mid = np.hypot(pts[12][0] - palm_cx, pts[12][1] - palm_cy)
    d_ring = np.hypot(pts[16][0] - palm_cx, pts[16][1] - palm_cy)
    d_pinky = np.hypot(pts[20][0] - palm_cx, pts[20][1] - palm_cy)

    thumb_extended = d_thumb > hand_scale * 1.05
    fingers_curled = (
        d_index < hand_scale * 1.15 and
        d_mid < hand_scale * 1.15 and
        d_ring < hand_scale * 1.15 and
        d_pinky < hand_scale * 1.15
    )

    return thumb_extended and fingers_curled and g not in ("Closed_Fist", "Victory", "Open_Palm")


def is_peace_sign(hand: Dict[str, Any]) -> bool:
    """Detect if hand is in a two-finger peace/victory sign."""
    if is_fist(hand):
        return False

    if hand.get("is_victory", False):
        return True

    g = hand.get("gesture", "")
    conf = hand.get("gesture_confidence", 0.0)
    if g == "Victory" and conf >= 0.40:
        return True

    pts = hand.get("all_landmarks")
    if not pts or len(pts) < 21:
        return False

    palm_cx, palm_cy = hand.get("palm_center", (pts[0][0], pts[0][1]))
    wrist = pts[0]
    hand_scale = max(20.0, float(np.hypot(palm_cx - wrist[0], palm_cy - wrist[1])))

    d_index = np.hypot(pts[8][0] - palm_cx, pts[8][1] - palm_cy)
    d_middle = np.hypot(pts[12][0] - palm_cx, pts[12][1] - palm_cy)
    d_ring = np.hypot(pts[16][0] - palm_cx, pts[16][1] - palm_cy)
    d_pinky = np.hypot(pts[20][0] - palm_cx, pts[20][1] - palm_cy)

    index_extended = d_index > hand_scale * 1.25
    middle_extended = d_middle > hand_scale * 1.25
    ring_curled = d_ring < hand_scale * 1.15
    pinky_curled = d_pinky < hand_scale * 1.15

    tip_dist = np.hypot(pts[8][0] - pts[12][0], pts[8][1] - pts[12][1])
    is_v = tip_dist > hand_scale * 0.16

    return index_extended and middle_extended and ring_curled and pinky_curled and is_v


class GestureManager:
    """Centralized temporal gesture evaluator with latching and hysteresis."""

    def __init__(self):
        self._hold = {}          # key -> start_time
        self._last_seen = {}     # key -> last_time_active
        self._cooldown = {}      # key -> last_trigger_time
        self.last_fist_time = 0.0
        self.last_freeze_time = 0.0
        self.grace_period = getattr(settings, "GESTURE_GRACE_PERIOD_S", 0.22)

    def _check_hold_progress(self, key: str, active: bool, duration: float, cooldown: float = 2.0) -> Tuple[bool, float]:
        now = time.time()
        last_trig = self._cooldown.get(key, 0.0)

        # Still in cooldown
        if now - last_trig < cooldown:
            self._hold.pop(key, None)
            return False, 0.0

        if active:
            self._last_seen[key] = now
            if key not in self._hold:
                self._hold[key] = now
                return False, 0.0
            elapsed = now - self._hold[key]
            progress = min(1.0, elapsed / max(0.01, duration))
            if elapsed >= duration:
                self._cooldown[key] = now
                self._hold.pop(key, None)
                self._last_seen.pop(key, None)
                return True, 1.0
            return False, progress
        else:
            # Tolerant hysteresis: don't reset immediately if tracking blipped for < grace_period
            last_active = self._last_seen.get(key, 0.0)
            if now - last_active > self.grace_period:
                self._hold.pop(key, None)
                self._last_seen.pop(key, None)
            elif key in self._hold:
                elapsed = now - self._hold[key]
                progress = min(1.0, elapsed / max(0.01, duration))
                return False, progress
            return False, 0.0

    # ── 1. ✌️ Peace Sign: Photo Capture Trigger (Snappy & Latched) ──

    def check_peace_capture(self, hands: List[Dict[str, Any]]) -> bool:
        """
        ✌️ Peace / Victory sign triggers photo capture countdown.
        Once triggered, the action latches without requiring continuous holding.
        """
        has_peace = any(is_peace_sign(h) for h in hands)
        duration = getattr(settings, "PEACE_PHOTO_HOLD_S", 0.20)
        cooldown = getattr(settings, "PEACE_PHOTO_COOLDOWN_S", 3.5)
        triggered, _ = self._check_hold_progress("peace_photo", has_peace, duration=duration, cooldown=cooldown)
        return triggered

    # ── 2. 👍 Open Thumb: Reveal QR Popup at Bottom-Right ──

    def check_thumb_trigger(self, hands: List[Dict[str, Any]]) -> bool:
        """
        👍 Open thumb triggers QR card popup at bottom-right.
        Once shown, it latches open until fist is shown.
        """
        now = time.time()
        # Cooldown guard: cannot open QR within 0.8s of seeing a fist
        if now - self.last_fist_time < 0.8:
            self._hold.pop("thumb_qr", None)
            return False

        has_thumb = any(is_thumb_up(h) for h in hands)
        duration = getattr(settings, "THUMB_HOLD_S", 0.18)
        triggered, _ = self._check_hold_progress("thumb_qr", has_thumb, duration=duration, cooldown=1.0)
        return triggered

    # ── 3. ✊ Closed Fist: Close QR Popup ──

    def check_fist(self, hands: List[Dict[str, Any]]) -> bool:
        """
        ✊ Closed fist dismisses the QR popup.
        """
        has_fist = any(is_fist(h) for h in hands)
        if has_fist:
            self.last_fist_time = time.time()
            self._hold.pop("thumb_qr", None)
        return has_fist

    def check_fist_close_qr(self, hands: List[Dict[str, Any]]) -> bool:
        """Snappy fist trigger for closing QR popup."""
        has_fist = any(is_fist(h) for h in hands)
        duration = getattr(settings, "FIST_HOLD_S", 0.12)
        triggered, _ = self._check_hold_progress("fist_close", has_fist, duration=duration, cooldown=0.6)
        if triggered or has_fist:
            self.last_fist_time = time.time()
            self._hold.pop("thumb_qr", None)
            return True
        return False

    # ── 4. ✋ Open Palm: Freeze Time ──

    def check_open_palm_freeze(self, hands: List[Dict[str, Any]], qr_active: bool = False) -> Tuple[bool, float, Optional[Tuple[int, int]]]:
        """
        ✋ Open palm creates a frozen temporal clone locked in physical space.
        Returns: (triggered: bool, progress: float [0..1], palm_pos: (x, y) or None)
        """
        if qr_active or any(is_fist(h) for h in hands):
            self._hold.pop("palm_freeze", None)
            return False, 0.0, None

        palm_hands = [
            h for h in hands
            if h.get("is_open_palm", False) or (h.get("gesture") == "Open_Palm" and h.get("gesture_confidence", 0) > 0.40)
        ]
        has_palm = len(palm_hands) > 0
        palm_pos = None
        if has_palm:
            ph = palm_hands[0]
            palm_pos = ph.get("palm_center") or ph.get("index_tip")

        duration = getattr(settings, "PALM_FREEZE_HOLD_S", 0.35)
        cooldown = getattr(settings, "PALM_FREEZE_COOLDOWN_S", 1.4)
        triggered, progress = self._check_hold_progress("palm_freeze", has_palm, duration=duration, cooldown=cooldown)
        if triggered:
            self.last_freeze_time = time.time()
        return triggered, progress, palm_pos

    # ── Compatibility Aliases ──

    def check_victory_freeze(self, hands: List[Dict[str, Any]], qr_active: bool = False) -> Tuple[bool, float, Optional[Tuple[int, int]]]:
        """Maps to open palm freeze for clone creation."""
        return self.check_open_palm_freeze(hands, qr_active)

    check_palm_freeze = check_open_palm_freeze

    def check_capture_trigger(self, hands: List[Dict[str, Any]]) -> bool:
        """Photo capture trigger: now triggered by peace sign ✌️."""
        return self.check_peace_capture(hands)

    # ── 5. ☝️ Rewind Gesture: Pointing Up ──

    def check_rewind_trigger(self, hands: List[Dict[str, Any]]) -> bool:
        """☝️ Pointing Up held for 0.8s -> triggers rewind."""
        has_pointing = any(h.get("is_pointing_up", False) for h in hands)
        triggered, _ = self._check_hold_progress("rewind", has_pointing, duration=0.80, cooldown=3.5)
        return triggered

    # ── 6. Start Screen Dwell / Button Hover ──

    def check_hover_dwell(self, hand_pts: List[Tuple[int, int]], target_x: int, target_y: int, radius: int, duration: float) -> Tuple[bool, float]:
        """Checks if any hand coordinate dwells within target circle for duration."""
        inside = any(np.hypot(pt[0] - target_x, pt[1] - target_y) <= radius for pt in hand_pts)
        return self._check_hold_progress("dwell_start", inside, duration, cooldown=1.0)
