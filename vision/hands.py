"""
Multi-Hand Tracker & Gesture Detector
Tracks up to 4 hands (duo support), extracting fingertips, palm centers, pinch states,
and recognized gestures (Victory, Open_Palm, Thumb_Up, etc.).
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
        Extracts hand positions, pinch coordinates, and active gestures.
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
                # Scale landmarks to full frame
                pts = []
                for lm in landmarks:
                    px = int(np.clip(lm.x * w, 0, w - 1))
                    py = int(np.clip(lm.y * h, 0, h - 1))
                    pts.append((px, py))

                if len(pts) < 21:
                    continue

                # Fingertips: 4=Thumb, 8=Index, 12=Middle, 16=Ring, 20=Pinky
                # Wrist: 0
                wrist = pts[0]
                thumb_tip = pts[4]
                index_tip = pts[8]
                middle_tip = pts[12]

                # Palm center (average of wrist and knuckle base points)
                palm_cx = int((pts[0][0] + pts[5][0] + pts[9][0] + pts[17][0]) / 4.0)
                palm_cy = int((pts[0][1] + pts[5][1] + pts[9][1] + pts[17][1]) / 4.0)

                # Pinch calculation (distance between thumb and index tip)
                dist = np.hypot(thumb_tip[0] - index_tip[0], thumb_tip[1] - index_tip[1])
                is_pinching = dist < 42

                # Gesture name
                gesture_name = "None"
                confidence = 0.0
                if res.gestures and len(res.gestures) > hand_idx and len(res.gestures[hand_idx]) > 0:
                    top_g = res.gestures[hand_idx][0]
                    gesture_name = top_g.category_name
                    confidence = top_g.score

                # Handedness (Left/Right)
                label = "Hand"
                if res.handedness and len(res.handedness) > hand_idx and len(res.handedness[hand_idx]) > 0:
                    label = res.handedness[hand_idx][0].category_name

                hands_data.append({
                    "id": hand_idx,
                    "label": label,
                    "palm_center": (palm_cx, palm_cy),
                    "index_tip": index_tip,
                    "thumb_tip": thumb_tip,
                    "middle_tip": middle_tip,
                    "is_pinching": is_pinching,
                    "gesture": gesture_name,
                    "gesture_confidence": confidence,
                    "all_landmarks": pts
                })
        except Exception:
            pass

        return hands_data
