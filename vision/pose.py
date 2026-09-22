"""
Pose Tracker for Single and Duo Users
Tracks full-body skeletal landmarks for up to two individuals simultaneously.
"""
from typing import List, Dict, Any
import numpy as np
import cv2
import mediapipe as mp
from config import settings
from vision.models_manager import ensure_model

BaseOptions = mp.tasks.BaseOptions
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode


class PoseTracker:
    def __init__(self, num_poses=2):
        self.num_poses = num_poses
        self.landmarker = None
        self._init_model()

    def _init_model(self):
        model_path = ensure_model("pose_landmarker_lite.task")
        if not model_path:
            return

        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=VisionRunningMode.IMAGE,
            num_poses=self.num_poses,
            min_pose_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        try:
            self.landmarker = PoseLandmarker.create_from_options(options)
            print("[PoseTracker] PoseLandmarker initialized (duo mode enabled).")
        except Exception as e:
            print(f"[PoseTracker] Error initializing PoseLandmarker: {e}")

    def track(self, frame_bgr: np.ndarray) -> List[Dict[str, Any]]:
        """
        Processes frame and returns a list of detected people (up to 2).
        Each entry contains landmark points scaled to frame coordinates.
        """
        h, w = frame_bgr.shape[:2]
        results = []

        if self.landmarker is None:
            return results

        # Process at vision resolution for speed
        small_w = settings.VISION_WIDTH
        small_h = settings.VISION_HEIGHT
        small_bgr = cv2.resize(frame_bgr, (small_w, small_h), interpolation=cv2.INTER_LINEAR)
        small_rgb = cv2.cvtColor(small_bgr, cv2.COLOR_BGR2RGB)

        try:
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=small_rgb)
            detection_res = self.landmarker.detect(mp_image)
            if not detection_res.pose_landmarks:
                return results

            for person_idx, landmarks in enumerate(detection_res.pose_landmarks):
                person_data = {
                    "person_id": person_idx + 1,
                    "landmarks": [],
                    "keypoints": {}
                }
                # Scale landmarks to full frame (w, h)
                pts = []
                for lm in landmarks:
                    px = int(np.clip(lm.x * w, 0, w - 1))
                    py = int(np.clip(lm.y * h, 0, h - 1))
                    pts.append((px, py, lm.visibility))
                person_data["landmarks"] = pts

                # Key anatomical points
                # 0: nose, 11/12: shoulders, 15/16: wrists, 23/24: hips, 27/28: ankles
                if len(pts) >= 29:
                    person_data["keypoints"] = {
                        "nose": pts[0][:2],
                        "left_shoulder": pts[11][:2],
                        "right_shoulder": pts[12][:2],
                        "left_wrist": pts[15][:2],
                        "right_wrist": pts[16][:2],
                        "left_hip": pts[23][:2],
                        "right_hip": pts[24][:2],
                        "left_ankle": pts[27][:2],
                        "right_ankle": pts[28][:2],
                    }
                results.append(person_data)
        except Exception:
            pass

        return results
