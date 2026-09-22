"""
Multi-Hand Tracker & Gesture Detector
─────────────────────────────────────
Tracks up to 4 hands with high fidelity, extracting fingertips, palm centers,
pinch states, extended fingers, open palm detection, and recognized gestures.
"""
from typing import List, Dict, Any
import numpy as np
import cv2
import mediapipe as mp
from config import settings
from vision.models_manager import ensure_model

BaseOptions = mp.tasks.BaseOptions
GestureRecognizer = mp.tasks.vision.GestureRecognizer
GestureRecognizerOptions = mp.tasks.vision.GestureRecognizerOptions
VisionRunningMode = mp.tasks.vision.RunningMode


def detect_open_palm(pts: List[tuple], palm_center: tuple, gesture_name: str, confidence: float) -> bool:
    """Robust geometric and ML check for an extended open palm."""
    if gesture_name == "Open_Palm" and confidence >= 0.50:
        return True

    if not pts or len(pts) < 21:
        return False

    palm_cx, palm_cy = palm_center
    wrist = pts[0]
    hand_scale = max(25.0, float(np.hypot(palm_cx - wrist[0], palm_cy - wrist[1])))

    # Check that all 4 fingers (index, middle, ring, pinky) are extended outward
    # In an open palm, fingertip distance from palm center is noticeably larger than knuckle distance
    d_index = np.hypot(pts[8][0] - palm_cx, pts[8][1] - palm_cy)
    d_middle = np.hypot(pts[12][0] - palm_cx, pts[12][1] - palm_cy)
    d_ring = np.hypot(pts[16][0] - palm_cx, pts[16][1] - palm_cy)
    d_pinky = np.hypot(pts[20][0] - palm_cx, pts[20][1] - palm_cy)

    fingers_extended = (
        d_index > hand_scale * 1.35 and
        d_middle > hand_scale * 1.40 and
        d_ring > hand_scale * 1.30 and
        d_pinky > hand_scale * 1.15
    )

    # Check thumb is also extended
    d_thumb = np.hypot(pts[4][0] - palm_cx, pts[4][1] - palm_cy)
    thumb_extended = d_thumb > hand_scale * 1.05

    return fingers_extended and thumb_extended and gesture_name not in ("Closed_Fist", "Victory")


def detect_pointing_up(pts: List[tuple], palm_center: tuple) -> bool:
    """Detects index finger pointing straight up with others curled."""
    if not pts or len(pts) < 21:
        return False

    # Index finger straight up: tip (8) is well above pip (6) and mcp (5)
    index_up = pts[8][1] < pts[6][1] - 20 and pts[6][1] < pts[5][1]

    # Other fingers curled: tip is below pip or close to palm
    middle_curled = pts[12][1] > pts[10][1] - 10
    ring_curled = pts[16][1] > pts[14][1] - 10
    pinky_curled = pts[20][1] > pts[18][1] - 10

    return index_up and middle_curled and ring_curled and pinky_curled


def detect_pointing_direction(pts: List[tuple], palm_center: tuple) -> int:
    """
    Detects horizontal index finger pointing direction:
      -1: Pointing Left
      +1: Pointing Right
       0: Neutral / Not pointing left or right
    """
    if not pts or len(pts) < 21:
        return 0

    palm_cx, palm_cy = palm_center
    wrist = pts[0]
    hand_scale = max(20.0, float(np.hypot(palm_cx - wrist[0], palm_cy - wrist[1])))

    # Vector from index MCP (knuckle, joint 5) to index TIP (joint 8)
    dx = pts[8][0] - pts[5][0]
    dy = pts[8][1] - pts[5][1]
    d_index = np.hypot(dx, dy)
    d_index_palm = np.hypot(pts[8][0] - palm_cx, pts[8][1] - palm_cy)

    # Index finger must be physically extended from knuckle
    if d_index < hand_scale * 0.70:
        return 0

    # Horizontal dominance: |dx| must be distinctly larger than |dy|
    if abs(dx) < abs(dy) * 0.85 or abs(dx) < 25.0:
        return 0

    # Middle, ring, and pinky fingers must be curled towards palm
    d_middle = np.hypot(pts[12][0] - palm_cx, pts[12][1] - palm_cy)
    d_ring = np.hypot(pts[16][0] - palm_cx, pts[16][1] - palm_cy)
    d_pinky = np.hypot(pts[20][0] - palm_cx, pts[20][1] - palm_cy)

    # Middle finger extension check (distinguishes from peace sign)
    d_mid_knuckle = np.hypot(pts[12][0] - pts[9][0], pts[12][1] - pts[9][1])
    if d_mid_knuckle > d_index * 0.75:
        return 0

    if d_middle > hand_scale * 1.35 or d_ring > hand_scale * 1.30 or d_pinky > hand_scale * 1.30:
        return 0

    return -1 if dx < 0 else 1


def detect_victory(pts: List[tuple], palm_center: tuple, gesture_name: str, confidence: float) -> bool:
    """Robust geometric and ML check for a two-finger Victory / Peace sign (V-shape), rotation-invariant."""
    if gesture_name == "Victory" and confidence >= 0.40:
        return True

    if not pts or len(pts) < 21:
        return False

    palm_cx, palm_cy = palm_center
    wrist = pts[0]
    hand_scale = max(20.0, float(np.hypot(palm_cx - wrist[0], palm_cy - wrist[1])))

    # Rotation-invariant extension check via distances from palm center
    d_index = np.hypot(pts[8][0] - palm_cx, pts[8][1] - palm_cy)
    d_middle = np.hypot(pts[12][0] - palm_cx, pts[12][1] - palm_cy)
    d_ring = np.hypot(pts[16][0] - palm_cx, pts[16][1] - palm_cy)
    d_pinky = np.hypot(pts[20][0] - palm_cx, pts[20][1] - palm_cy)

    index_extended = d_index > hand_scale * 1.25
    middle_extended = d_middle > hand_scale * 1.25
    ring_curled = d_ring < hand_scale * 1.15
    pinky_curled = d_pinky < hand_scale * 1.15

    # Index and middle tips are separated into a 'V' shape
    tip_dist = np.hypot(pts[8][0] - pts[12][0], pts[8][1] - pts[12][1])
    is_v_shape = tip_dist > hand_scale * 0.16

    # Vertical-axis fallback check
    vert_index = pts[8][1] < pts[6][1] - 10
    vert_middle = pts[12][1] < pts[10][1] - 10
    vert_ring = pts[16][1] > pts[14][1] - 12
    vert_pinky = pts[20][1] > pts[18][1] - 12
    vertical_v = vert_index and vert_middle and vert_ring and vert_pinky and is_v_shape

    return (index_extended and middle_extended and ring_curled and pinky_curled and is_v_shape) or vertical_v


def detect_open_thumb(pts: List[tuple], palm_center: tuple, gesture_name: str, confidence: float) -> bool:
    """Detects an open thumb (Thumbs-Up or open thumb extension), rotation-invariant."""
    if gesture_name == "Thumb_Up" and confidence >= 0.40:
        return True

    if not pts or len(pts) < 21:
        return False

    palm_cx, palm_cy = palm_center
    wrist = pts[0]
    hand_scale = max(20.0, float(np.hypot(palm_cx - wrist[0], palm_cy - wrist[1])))

    d_thumb = np.hypot(pts[4][0] - palm_cx, pts[4][1] - palm_cy)
    d_index = np.hypot(pts[8][0] - palm_cx, pts[8][1] - palm_cy)
    d_middle = np.hypot(pts[12][0] - palm_cx, pts[12][1] - palm_cy)
    d_ring = np.hypot(pts[16][0] - palm_cx, pts[16][1] - palm_cy)
    d_pinky = np.hypot(pts[20][0] - palm_cx, pts[20][1] - palm_cy)

    thumb_extended = d_thumb > hand_scale * 1.05
    fingers_curled = (
        d_index < hand_scale * 1.15 and
        d_middle < hand_scale * 1.15 and
        d_ring < hand_scale * 1.15 and
        d_pinky < hand_scale * 1.15
    )

    # Vertical thumbs-up check
    vert_thumb = pts[4][1] < pts[3][1] - 10 and pts[4][1] < pts[5][1] - 15
    vert_curled = pts[8][1] > pts[6][1] - 10 and pts[12][1] > pts[10][1] - 10

    return (thumb_extended and fingers_curled) or (vert_thumb and vert_curled)


def detect_fist(pts: List[tuple], palm_center: tuple, gesture_name: str, confidence: float) -> bool:
    """Detects a closed fist where all fingers are tucked into palm."""
    if gesture_name == "Closed_Fist" and confidence >= 0.40:
        return True

    if not pts or len(pts) < 21:
        return False

    palm_cx, palm_cy = palm_center
    wrist = pts[0]
    hand_scale = max(20.0, float(np.hypot(palm_cx - wrist[0], palm_cy - wrist[1])))

    d_thumb = np.hypot(pts[4][0] - palm_cx, pts[4][1] - palm_cy)
    d_index = np.hypot(pts[8][0] - palm_cx, pts[8][1] - palm_cy)
    d_middle = np.hypot(pts[12][0] - palm_cx, pts[12][1] - palm_cy)
    d_ring = np.hypot(pts[16][0] - palm_cx, pts[16][1] - palm_cy)
    d_pinky = np.hypot(pts[20][0] - palm_cx, pts[20][1] - palm_cy)

    all_curled = (
        d_thumb < hand_scale * 0.95 and
        d_index < hand_scale * 1.05 and
        d_middle < hand_scale * 1.05 and
        d_ring < hand_scale * 1.05 and
        d_pinky < hand_scale * 1.05
    )
    return all_curled and gesture_name not in ("Open_Palm", "Victory", "Thumb_Up")


class HandTracker:
    def __init__(self, num_hands=4):
        self.num_hands = num_hands
        self.recognizer = None
        self._init_model()

    def _init_model(self):
        model_path = ensure_model("gesture_recognizer.task")
        if not model_path:
            return

        options = GestureRecognizerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=VisionRunningMode.IMAGE,
            num_hands=self.num_hands,
            min_hand_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        try:
            self.recognizer = GestureRecognizer.create_from_options(options)
            print("[HandTracker] GestureRecognizer initialized (4 hands supported).")
        except Exception as e:
            print(f"[HandTracker] Error initializing GestureRecognizer: {e}")

    def track(self, frame_bgr: np.ndarray) -> List[Dict[str, Any]]:
        """
        Extracts hand positions, pinch coordinates, open palm states, and active gestures.
        """
        h, w = frame_bgr.shape[:2]
        hands_data = []

        if self.recognizer is None:
            return hands_data

        small_w = settings.VISION_WIDTH
        small_h = settings.VISION_HEIGHT
        small_bgr = cv2.resize(frame_bgr, (small_w, small_h), interpolation=cv2.INTER_LINEAR)
        small_rgb = cv2.cvtColor(small_bgr, cv2.COLOR_BGR2RGB)

        try:
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=small_rgb)
            res = self.recognizer.recognize(mp_image)

            if not res.hand_landmarks:
                return hands_data

            for hand_idx, landmarks in enumerate(res.hand_landmarks):
                pts = []
                for lm in landmarks:
                    px = int(np.clip(lm.x * w, 0, w - 1))
                    py = int(np.clip(lm.y * h, 0, h - 1))
                    pts.append((px, py))

                if len(pts) < 21:
                    continue

                thumb_tip = pts[4]
                index_tip = pts[8]
                middle_tip = pts[12]

                # Palm center (weighted centroid)
                palm_cx = int((pts[0][0] + pts[5][0] + pts[9][0] + pts[17][0]) / 4.0)
                palm_cy = int((pts[0][1] + pts[5][1] + pts[9][1] + pts[17][1]) / 4.0)

                # Pinch distance
                dist = np.hypot(thumb_tip[0] - index_tip[0], thumb_tip[1] - index_tip[1])
                is_pinching = dist < 42

                # Gesture classification
                gesture_name = "None"
                confidence = 0.0
                if res.gestures and len(res.gestures) > hand_idx and len(res.gestures[hand_idx]) > 0:
                    top_g = res.gestures[hand_idx][0]
                    gesture_name = top_g.category_name
                    confidence = top_g.score

                # Handedness
                label = "Hand"
                if res.handedness and len(res.handedness) > hand_idx and len(res.handedness[hand_idx]) > 0:
                    label = res.handedness[hand_idx][0].category_name

                # Geometric enhancements
                open_palm = detect_open_palm(pts, (palm_cx, palm_cy), gesture_name, confidence)
                pointing_up = detect_pointing_up(pts, (palm_cx, palm_cy))
                pointing_dir = detect_pointing_direction(pts, (palm_cx, palm_cy))
                victory = detect_victory(pts, (palm_cx, palm_cy), gesture_name, confidence)
                thumb_open = detect_open_thumb(pts, (palm_cx, palm_cy), gesture_name, confidence)
                fist = detect_fist(pts, (palm_cx, palm_cy), gesture_name, confidence)

                victory_cx = int((index_tip[0] + middle_tip[0]) / 2.0)
                victory_cy = int((index_tip[1] + middle_tip[1]) / 2.0)

                hands_data.append({
                    "id": hand_idx,
                    "label": label,
                    "palm_center": (palm_cx, palm_cy),
                    "index_tip": index_tip,
                    "thumb_tip": thumb_tip,
                    "middle_tip": middle_tip,
                    "victory_center": (victory_cx, victory_cy),
                    "is_pinching": is_pinching,
                    "is_open_palm": open_palm,
                    "is_pointing_up": pointing_up,
                    "pointing_direction": pointing_dir,
                    "is_victory": victory,
                    "is_thumb_open": thumb_open,
                    "is_fist": fist,
                    "gesture": gesture_name,
                    "gesture_confidence": confidence,
                    "all_landmarks": pts
                })
        except Exception:
            pass

        return hands_data
