"""
Camera Stream Manager
Handles real-time webcam acquisition with threaded buffer and synthetic fallback.
"""
import time
import threading
import numpy as np
import cv2
from config import settings


class CameraStream:
    def __init__(self, camera_index=settings.CAMERA_INDEX, width=settings.CAPTURE_WIDTH, height=settings.CAPTURE_HEIGHT):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.cap = None
        self.is_running = False
        self.is_synthetic = False
        self.current_frame = None
        self.lock = threading.Lock()
        self.thread = None
        self._init_camera()

    def _init_camera(self):
        # Try DirectShow first on Windows for faster initialization, then default
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(self.camera_index)
        
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_FPS, settings.TARGET_FPS)
            ret, frame = cap.read()
            if ret and frame is not None:
                self.cap = cap
                self.current_frame = cv2.flip(frame, 1)  # Mirror mode
                self.is_synthetic = False
                return
            cap.release()

        # Fallback to synthetic camera if physical device is unavailable or busy
        self.is_synthetic = True
        self.current_frame = self._generate_synthetic_frame(0)

    def _generate_synthetic_frame(self, t):
        """Generates dynamic synthetic people (a duo) moving naturally in front of a camera."""
        frame = np.full((self.height, self.width, 3), (35, 30, 25), dtype=np.uint8)
        
        # Draw background wall grid
        for x in range(0, self.width, 60):
            cv2.line(frame, (x, 0), (x, self.height), (45, 40, 35), 1)
        for y in range(0, self.height, 60):
            cv2.line(frame, (0, y), (self.width, y), (45, 40, 35), 1)
        
        # Person 1 (Primary - Left/Center)
        cx1 = int(self.width * 0.38 + np.sin(t * 1.5) * 40)
        cy1 = int(self.height * 0.60)
        # Body
        cv2.ellipse(frame, (cx1, cy1 + 120), (100, 160), 0, 0, 360, (140, 110, 80), -1)
        # Head
        cv2.circle(frame, (cx1, cy1 - 70), 55, (200, 180, 155), -1)
        # Arm & waving hand
        hand_x1 = int(cx1 - 120 + np.sin(t * 3.0) * 30)
        hand_y1 = int(cy1 - 50 + np.cos(t * 3.0) * 40)
        cv2.line(frame, (cx1 - 60, cy1 + 30), (hand_x1, hand_y1), (140, 110, 80), 28)
        cv2.circle(frame, (hand_x1, hand_y1), 22, (200, 180, 155), -1)

        # Person 2 (Duo Partner - Right/Center)
        cx2 = int(self.width * 0.65 + np.cos(t * 1.2) * 35)
        cy2 = int(self.height * 0.62)
        # Body
        cv2.ellipse(frame, (cx2, cy2 + 110), (90, 150), 0, 0, 360, (70, 120, 150), -1)
        # Head
        cv2.circle(frame, (cx2, cy2 - 60), 50, (190, 170, 150), -1)
        # Raised hand
        hand_x2 = int(cx2 + 100 + np.cos(t * 2.5) * 25)
        hand_y2 = int(cy2 - 80 + np.sin(t * 2.5) * 30)
        cv2.line(frame, (cx2 + 50, cy2 + 20), (hand_x2, hand_y2), (70, 120, 150), 24)
        cv2.circle(frame, (hand_x2, hand_y2), 20, (190, 170, 150), -1)

        # Banner note
        cv2.putText(frame, "SIMULATED CAMERA STREAM (Physical camera busy or not detected)", 
                    (30, self.height - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (100, 220, 255), 2)
        return frame

    def start(self):
        if self.is_running:
            return self
        self.is_running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()
        return self

    def _update_loop(self):
        t0 = time.time()
        while self.is_running:
            if not self.is_synthetic and self.cap is not None:
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    mirrored = cv2.flip(frame, 1)
                    with self.lock:
                        self.current_frame = mirrored
                else:
                    time.sleep(0.01)
            else:
                elapsed = time.time() - t0
                frame = self._generate_synthetic_frame(elapsed)
                with self.lock:
                    self.current_frame = frame
                time.sleep(1.0 / settings.TARGET_FPS)

    def read(self):
        with self.lock:
            if self.current_frame is not None:
                return True, self.current_frame.copy()
            return False, None

    def release(self):
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.cap is not None:
            self.cap.release()
            self.cap = None
