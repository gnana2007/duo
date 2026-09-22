"""
Gesture Manager v3.3 — Full Gesture-Only Control
───────────────────────────────────────────────
Rock-solid gesture detection:
  ✌️  Victory / Peace  → Capture photo (hold 0.6s)
  👍 Thumb_Up         → Show QR code popup (hold 0.35s, cannot trigger if fist present)
  ✊  Closed_Fist      → Completely hide QR code popup (instant, no blinking) / Grab memory
  ✋  Open_Palm        → Release memory
"""
import time
from typing import List, Dict, Any
import numpy as np
from config import settings


def is_fist(hand: Dict[str, Any]) -> bool:
    """Detect if hand is in a closed fist."""
    g = hand.get("gesture", "")
    conf = hand.get("gesture_confidence", 0.0)

    # 1. Direct MediaPipe gesture classification
    if g == "Closed_Fist" and conf >= 0.40:
        return True

    pts = hand.get("all_landmarks")
    if pts and len(pts) == 21:
        palm_cx, palm_cy = hand.get("palm_center", (pts[0][0], pts[0][1]))
        wrist = pts[0]
        hand_scale = max(20.0, float(np.hypot(palm_cx - wrist[0], palm_cy - wrist[1])))

        # In a closed fist, all 4 fingertips are curled close to palm center
        d_index = np.hypot(pts[8][0] - palm_cx, pts[8][1] - palm_cy)
        d_mid = np.hypot(pts[12][0] - palm_cx, pts[12][1] - palm_cy)
        d_ring = np.hypot(pts[16][0] - palm_cx, pts[16][1] - palm_cy)
        d_pinky = np.hypot(pts[20][0] - palm_cx, pts[20][1] - palm_cy)

        fingers_curled_to_palm = (
            d_index < hand_scale * 1.10 and
            d_mid < hand_scale * 1.10 and
            d_ring < hand_scale * 1.10 and
            d_pinky < hand_scale * 1.10
        )

        # In a fist, thumb tip is tucked near index knuckle (pts[5])
        thumb_tip = pts[4]
        index_mcp = pts[5]
        d_thumb_knuckle = np.hypot(thumb_tip[0] - index_mcp[0], thumb_tip[1] - index_mcp[1])
        thumb_tucked = d_thumb_knuckle < hand_scale * 0.90

        if fingers_curled_to_palm and thumb_tucked and g != "Thumb_Up":
            return True

    return False


def is_thumb_up(hand: Dict[str, Any]) -> bool:
    """Detect if hand is in an unambiguous, genuine thumbs-up gesture."""
    g = hand.get("gesture", "")
    conf = hand.get("gesture_confidence", 0.0)

    # If hand is a fist, it is NEVER a thumb up!
    if is_fist(hand):
        return False

    pts = hand.get("all_landmarks")
    if not pts or len(pts) < 21:
        return g == "Thumb_Up" and conf >= 0.65

    palm_cx, palm_cy = hand.get("palm_center", (pts[0][0], pts[0][1]))
    wrist = pts[0]
    hand_scale = max(20.0, float(np.hypot(palm_cx - wrist[0], palm_cy - wrist[1])))

    thumb_tip = pts[4]
    index_mcp = pts[5]

    # In a genuine thumbs-up:
    # 1. Thumb tip is extended significantly above index knuckle and thumb joint
    thumb_pointing_up = (thumb_tip[1] < index_mcp[1] - 30) and (thumb_tip[1] < pts[3][1] - 15)

    # 2. Thumb tip is extended outward/upward away from the index knuckle
    d_thumb_knuckle = np.hypot(thumb_tip[0] - index_mcp[0], thumb_tip[1] - index_mcp[1])
    thumb_extended = d_thumb_knuckle > hand_scale * 0.65

    # 3. Other 4 fingers must be curled
    fingers_curled = (
        pts[8][1] > pts[6][1] - 5 and
        pts[12][1] > pts[10][1] - 5 and
        pts[16][1] > pts[14][1] - 5 and
        pts[20][1] > pts[18][1] - 5
    )

    # MediaPipe classified as Thumb_Up with confidence >= 0.50 AND thumb pointing up
    if g == "Thumb_Up" and conf >= 0.50 and thumb_pointing_up:
        return True

    # Robust geometric thumbs up
    if thumb_pointing_up and thumb_extended and fingers_curled and g not in ("Closed_Fist", "Victory", "Open_Palm"):
        return True

    return False


class GestureManager:
    def __init__(self):
        # Per-gesture hold start times
        self._hold = {}      # key → start_time
        self._cooldown = {}  # key → last_trigger_time
        self.last_fist_time = 0.0

    def _check_hold(self, key: str, active: bool,
                    duration: float, cooldown: float = 2.0) -> bool:
        now = time.time()
        if active:
            if key not in self._hold:
                self._hold[key] = now
            elif now - self._hold[key] >= duration:
                last = self._cooldown.get(key, 0)
                if now - last > cooldown:
                    self._cooldown[key] = now
                    self._hold.pop(key, None)
                    return True
        else:
            self._hold.pop(key, None)
        return False

    # ── Public API ─────────────────────────────────

    def check_capture_trigger(self, hands: List[Dict[str, Any]]) -> bool:
        """✌️ Peace/Victory held for GESTURE_HOLD_S → trigger photo."""
        has_peace = any(
            h.get("gesture") == "Victory" and h.get("gesture_confidence", 0) > 0.55
            for h in hands
        )
        return self._check_hold("capture", has_peace, settings.GESTURE_HOLD_S)

    def check_fist(self, hands: List[Dict[str, Any]]) -> bool:
        """
        Check if any visible hand is currently in a closed fist.
        Returns True continuously as long as a fist is present (no single-pulse cooldown).
        Completely and immediately suppresses QR popup without blinking.
        """
        has_fist = any(is_fist(h) for h in hands)
        if has_fist:
            self.last_fist_time = time.time()
            self._hold.pop("thumb_qr", None)
        return has_fist

    def check_fist_trigger(self, hands: List[Dict[str, Any]]) -> bool:
        """Backward-compatible alias for check_fist."""
        return self.check_fist(hands)

    def check_thumb_trigger(self, hands: List[Dict[str, Any]]) -> bool:
        """
        👍 Thumb_Up held for 0.35s → show QR popup.
        Guaranteed NEVER to trigger if a fist is visible or was seen within 1.5s.
        """
        now = time.time()
        # Cooldown guard: cannot open QR within 1.5s of seeing a fist (prevents blinking on release)
        if now - self.last_fist_time < 1.5:
            self._hold.pop("thumb_qr", None)
            return False

        # If any hand is a fist right now, suppress
        if any(is_fist(h) for h in hands):
            self.last_fist_time = now
            self._hold.pop("thumb_qr", None)
            return False

        has_thumb = any(is_thumb_up(h) for h in hands)
        return self._check_hold("thumb_qr", has_thumb, 0.35, cooldown=1.2)

    def check_confirm_trigger(self, hands: List[Dict[str, Any]]) -> bool:
        return self.check_thumb_trigger(hands)

    def check_close_trigger(self, hands: List[Dict[str, Any]]) -> bool:
        return self.check_fist(hands)
