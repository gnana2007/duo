"""
TimeSensei Real-Time Temporal Rewind Engine
──────────────────────────────────────────
Maintains a 3-second circular ring buffer of recent foreground motion sampled at 12 FPS.
Replays temporal states backward with ethereal ghost trails, reverse time markers,
and seamless return to live reality.
"""
import time
from collections import deque
from typing import Optional, Tuple
import numpy as np
import cv2
from config import settings
from interaction.audio import TimeSenseiAudio


class RewindBuffer:
    """Manages circular recording and reverse playback of recent movement."""

    def __init__(self, buffer_seconds: float = settings.REWIND_BUFFER_SECONDS,
                 fps: int = settings.REWIND_FPS,
                 audio: Optional[TimeSenseiAudio] = None):
        self.buffer_seconds = buffer_seconds
        self.fps = fps
        self.max_frames = int(buffer_seconds * fps)
        self.frame_interval = 1.0 / float(fps)
        self.audio = audio

        # Circular buffer: (timestamp, small_bgr, small_mask)
        self.history = deque(maxlen=self.max_frames)
        self.last_record_time = 0.0

        # Playback state
        self.is_rewinding = False
        self.playback_frames = []
        self.playback_idx = 0
        self.playback_start_time = 0.0
        self.playback_speed = settings.REWIND_PLAYBACK_SPEED

    def record_frame(self, frame_bgr: np.ndarray, alpha_mask: np.ndarray):
        """Records a downscaled foreground sample into the ring buffer."""
        if self.is_rewinding:
            return

        now = time.time()
        if now - self.last_record_time < self.frame_interval:
            return
        self.last_record_time = now

        # Downscale for memory efficiency (480x270)
        sw, sh = settings.VISION_WIDTH, settings.VISION_HEIGHT
        small_bgr = cv2.resize(frame_bgr, (sw, sh), interpolation=cv2.INTER_LINEAR)
        small_mask = cv2.resize(alpha_mask, (sw, sh), interpolation=cv2.INTER_LINEAR)
        small_mask_u8 = (np.clip(small_mask, 0.0, 1.0) * 255).astype(np.uint8)

        self.history.append((now, small_bgr, small_mask_u8))

    def trigger_rewind(self) -> bool:
        """Starts reverse playback if buffer has sufficient history."""
        if self.is_rewinding or len(self.history) < int(self.fps * 1.0):
            return False

        self.is_rewinding = True
        # Snapshot current history for backward playback
        self.playback_frames = list(self.history)
        self.playback_idx = len(self.playback_frames) - 1
        self.playback_start_time = time.time()

        if self.audio:
            self.audio.play_rewind()

        return True

    def update_and_render(self, canvas: np.ndarray, bg_frame: np.ndarray) -> Tuple[bool, np.ndarray]:
        """
        Advances reverse playback and renders the supernatural rewind effect.
        Returns: (is_rewinding_active, composited_canvas)
        """
        if not self.is_rewinding:
            return False, canvas

        now = time.time()
        elapsed = now - self.playback_start_time
        total_playback_time = (len(self.playback_frames) * self.frame_interval) / self.playback_speed

        if elapsed >= total_playback_time or self.playback_idx < 0:
            # Rewind complete: dissolve back to live
            self.is_rewinding = False
            self.playback_frames = []
            return False, canvas

        # Calculate current backward frame index
        progress = elapsed / total_playback_time
        self.playback_idx = int((1.0 - progress) * (len(self.playback_frames) - 1))
        self.playback_idx = max(0, min(len(self.playback_frames) - 1, self.playback_idx))

        _, past_bgr, past_mask_u8 = self.playback_frames[self.playback_idx]

        h, w = canvas.shape[:2]
        # Upscale historical frame to full canvas resolution
        full_past_bgr = cv2.resize(past_bgr, (w, h), interpolation=cv2.INTER_LINEAR)
        full_past_mask = cv2.resize(past_mask_u8, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255.0

        # ── Supernatural Visual Treatment ──
        # 1. Dim background slightly
        dimmed_bg = (bg_frame.astype(np.float32) * 0.70).astype(np.uint8)

        # 2. Cyan chromatic ghosting on the past self
        ghost_bgr = full_past_bgr.copy()
        ghost_bgr[:, :, 0] = np.clip(ghost_bgr[:, :, 0].astype(np.float32) * 1.25, 0, 255).astype(np.uint8)  # Boost blue
        ghost_bgr[:, :, 1] = np.clip(ghost_bgr[:, :, 1].astype(np.float32) * 1.15, 0, 255).astype(np.uint8)  # Boost green

        # 3. Composite past self onto dimmed background
        mask_3ch = np.expand_dims(full_past_mask, axis=-1)
        composite = (ghost_bgr.astype(np.float32) * mask_3ch + dimmed_bg.astype(np.float32) * (1.0 - mask_3ch)).astype(np.uint8)

        # 4. Reverse Scanlines / Time Markers
        t_mod = int((time.time() * 400) % h)
        cv2.line(composite, (0, h - t_mod), (w, h - t_mod), (0, 240, 255), 1, cv2.LINE_AA)

        # 5. On-screen REWINDING TIME banner
        banner_w, banner_h = 320, 48
        bx = (w - banner_w) // 2
        by = 85
        overlay = composite.copy()
        cv2.rectangle(overlay, (bx, by), (bx + banner_w, by + banner_h), (12, 16, 24), -1)
        cv2.rectangle(overlay, (bx, by), (bx + banner_w, by + banner_h), (0, 220, 255), 2, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.75, composite, 0.25, 0, composite)

        # Text & Reverse Progress Bar
        cv2.putText(composite, "<< REWINDING TIME", (bx + 28, by + 30),
                    cv2.FONT_HERSHEY_DUPLEX, 0.75, (0, 240, 255), 2, cv2.LINE_AA)

        # Progress line at bottom of banner
        bar_len = int((1.0 - progress) * (banner_w - 20))
        cv2.line(composite, (bx + 10, by + banner_h - 4), (bx + 10 + bar_len, by + banner_h - 4),
                 (0, 240, 255), 2, cv2.LINE_AA)

        return True, composite
