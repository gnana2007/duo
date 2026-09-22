"""
Photo Capture & State Coordinator
Orchestrates countdowns, camera flashes, burst sequences, review, and QR sharing.
"""
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import numpy as np
import cv2
from config import settings
from capture.timelapse import TimelapseManager
from capture.qr import QRCodeGenerator


class CaptureState:
    LIVE = "LIVE"
    COUNTDOWN = "COUNTDOWN"
    FLASH = "FLASH"
    BURST = "BURST"
    REVIEW = "REVIEW"
    QR = "QR"


class PhotoCaptureManager:
    def __init__(self):
        self.state = CaptureState.LIVE
        self.countdown_start = 0.0
        self.countdown_duration = settings.COUNTDOWN_SECONDS
        self.flash_start = 0.0
        self.flash_duration = settings.FLASH_DURATION_S
        
        self.timelapse = TimelapseManager()
        self.is_burst_mode = False

        self.last_captured_image: Optional[np.ndarray] = None
        self.last_photo_id: Optional[str] = None
        self.qr_generator = QRCodeGenerator()
        self.qr_image: Optional[np.ndarray] = None

    def trigger_capture(self, is_burst: bool = False):
        """Starts countdown for single photo or burst timelapse."""
        if self.state != CaptureState.LIVE:
            return
        self.is_burst_mode = is_burst
        self.countdown_start = time.time()
        self.state = CaptureState.COUNTDOWN

    def cancel_capture(self):
        self.state = CaptureState.LIVE
        self.timelapse.is_active = False

    def update(self, current_composite: np.ndarray) -> Optional[np.ndarray]:
        """
        Updates the capture state machine.
        Returns a flash overlay frame if flashing, else None.
        """
        now = time.time()

        # 1. Countdown Phase
        if self.state == CaptureState.COUNTDOWN:
            elapsed = now - self.countdown_start
            if elapsed >= self.countdown_duration:
                # Trigger Flash and capture
                self.flash_start = now
                self.state = CaptureState.FLASH
                if self.is_burst_mode:
                    self.timelapse.start()

        # 2. Flash Phase
        elif self.state == CaptureState.FLASH:
            elapsed = now - self.flash_start
            if elapsed >= self.flash_duration:
                if self.is_burst_mode:
                    self.state = CaptureState.BURST
                else:
                    self._save_photo(current_composite)
                    self.state = CaptureState.REVIEW

        # 3. Burst Phase
        elif self.state == CaptureState.BURST:
            status = self.timelapse.update(current_composite)
            if status == "SNAP":
                self.flash_start = now
            elif status == "FINISHED":
                best_photo = self.timelapse.get_selected_photo()
                if best_photo is not None:
                    self._save_photo(best_photo)
                self.state = CaptureState.REVIEW

        return None

    def _save_photo(self, photo_bgr: np.ndarray):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.last_photo_id = f"photo_{timestamp}"
        file_path = settings.CAPTURES_DIR / f"{self.last_photo_id}.jpg"
        cv2.imwrite(str(file_path), photo_bgr)
        self.last_captured_image = photo_bgr
        self.qr_image = self.qr_generator.generate_qr_image(self.last_photo_id)

    def keep_photo(self):
        """Transitions from REVIEW to QR sharing."""
        if self.state == CaptureState.REVIEW:
            self.state = CaptureState.QR

    def discard_photo(self):
        """Discards current capture and returns to LIVE."""
        self.state = CaptureState.LIVE
        self.last_captured_image = None
        self.last_photo_id = None
        self.qr_image = None

    def get_countdown_remaining(self) -> float:
        if self.state != CaptureState.COUNTDOWN:
            return 0.0
        remaining = self.countdown_duration - (time.time() - self.countdown_start)
        return max(0.0, remaining)

    def is_flashing(self) -> bool:
        if self.state == CaptureState.FLASH:
            return True
        if self.state == CaptureState.BURST and (time.time() - self.flash_start) < 0.15:
            return True
        return False
