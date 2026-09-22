"""
Timelapse & Burst Photography Manager
Sequences multi-pose captures over time (e.g., 4 burst photos across changing poses).
"""
import time
from typing import List, Optional
import numpy as np
import cv2
from config import settings


class TimelapseManager:
    def __init__(self, count: int = settings.BURST_COUNT, interval: float = settings.BURST_INTERVAL_S):
        self.count = count
        self.interval = interval
        self.is_active = False
        self.current_step = 0
        self.last_snap_time = 0.0
        self.captured_frames: List[np.ndarray] = []
        self.selected_index = 0

    def start(self):
        self.is_active = True
        self.current_step = 0
        self.captured_frames = []
        self.last_snap_time = time.time()
        self.selected_index = 0

    def update(self, current_composite: np.ndarray) -> Optional[str]:
        """
        Updates burst sequence.
        Returns "SNAP" when a frame is captured, "FINISHED" when all poses are done, or None.
        """
        if not self.is_active:
            return None

        now = time.time()
        elapsed = now - self.last_snap_time

        if elapsed >= self.interval:
            # Capture photo
            self.captured_frames.append(current_composite.copy())
            self.current_step += 1
            self.last_snap_time = now

            if self.current_step >= self.count:
                self.is_active = False
                return "FINISHED"
            return "SNAP"

        return None

    def get_progress_info(self):
        """Returns (current_pose_num, total_poses, time_until_next_snap)"""
        if not self.is_active:
            return 0, self.count, 0.0
        time_left = max(0.0, self.interval - (time.time() - self.last_snap_time))
        return self.current_step + 1, self.count, time_left

    def select_next(self):
        if self.captured_frames:
            self.selected_index = (self.selected_index + 1) % len(self.captured_frames)

    def select_previous(self):
        if self.captured_frames:
            self.selected_index = (self.selected_index - 1 + len(self.captured_frames)) % len(self.captured_frames)

    def get_selected_photo(self) -> Optional[np.ndarray]:
        if self.captured_frames and 0 <= self.selected_index < len(self.captured_frames):
            return self.captured_frames[self.selected_index]
        return None
