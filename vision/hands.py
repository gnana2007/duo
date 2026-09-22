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


def detect_victory(pts: List[tuple], palm_center: tuple, gesture_name: str, confidence: float) -> bool:
    """Robust geometric and ML check for a two-finger Victory / Peace sign (V-shape)."""
    if gesture_name == "Victory" and confidence >= 0.45:
        return True

    if not pts or len(pts) < 21:
        return False

    palm_cx, palm_cy = palm_center
    wrist = pts[0]
    hand_scale = max(20.0, float(np.hypot(palm_cx - wrist[0], palm_cy - wrist[1])))

    # 1. Index finger extended: tip (8) is well above pip (6) and mcp (5)
    index_extended = (pts[8][1] < pts[6][1] - 12) and (pts[6][1] < pts[5][1] + 10)

    # 2. Middle finger extended: tip (12) is well above pip (10) and mcp (9)
    middle_extended = (pts[12][1] < pts[10][1] - 12) and (pts[10][1] < pts[9][1] + 10)

    # 3. Ring finger curled: tip (16) is close to palm or below pip (14)
    ring_curled = pts[16][1] > pts[14][1] - 12

    # 4. Pinky finger curled: tip (20) is close to palm or below pip (18)
    pinky_curled = pts[20][1] > pts[18][1] - 12

    # 5. Index and middle tips are separated into a 'V' shape
    tip_dist = np.hypot(pts[8][0] - pts[12][0], pts[8][1] - pts[12][1])
    is_v_shape = tip_dist > hand_scale * 0.20

    return index_extended and middle_extended and ring_curled and pinky_curled and is_v_shape


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
                victory = detect_victory(pts, (palm_cx, palm_cy), gesture_name, confidence)

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
                    "is_victory": victory,
                    "gesture": gesture_name,
                    "gesture_confidence": confidence,
                    "all_landmarks": pts
                })
        except Exception:
            pass

        return hands_data
