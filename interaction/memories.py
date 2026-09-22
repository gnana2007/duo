"""
TimeSensei Temporal Memory System
───────────────────────────────────
Manages persistent frozen temporal clones ("memories") with:
  • Precise spatial anchoring (clones stay locked exactly where the visitor froze time)
  • Zero floating / zero accidental movement (touch, punch, and fist-grab disabled)
  • Natural grounded contact shadows
  • Seamless multi-channel alpha blending & environment lighting adaptation
  • Hard collection limit (FIFO eviction at MAX_MEMORIES)
"""
import time
import math
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import cv2
from config import settings


class FrozenMemory:
    """A stationary frozen temporal clone locked in physical space."""

    def __init__(
        self,
        person_bgra: np.ndarray,
        bbox: Tuple[int, int, int, int],
        capture_time: float,
        memory_id: int,
        frame_h: int,
        frame_w: int,
    ):
        self.memory_id = memory_id
        self.capture_time = capture_time
        self.frame_h = frame_h
        self.frame_w = frame_w

        x, y, bw, bh = bbox
        self.crop_bgra = person_bgra[y:y+bh, x:x+bw].copy()

        # Feather bottom edge (6px) to eliminate harsh crop lines
        if bh > 10:
            for r in range(min(6, bh)):
                factor = r / 6.0
                self.crop_bgra[bh - 1 - r, :, 3] = (
                    self.crop_bgra[bh - 1 - r, :, 3].astype(np.float32) * factor
                ).astype(np.uint8)

        # ── Precise Spatial Anchoring: Lock clone exactly where visitor was standing ──
        self.origin_x = float(x)
        self.origin_y = float(y)
        self.width = bw
        self.height = bh

        # Reaction / Motion offsets (strictly stationary)
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.rotation = 0.0
        self.shake_intensity = 0.0
        self.reaction_label = ""
        self.reaction_time = 0.0
        self.reaction_duration = 0.0
        self.strike_count = 0
        self.last_strike_time = 0.0

        # Clone remains intact and stationary
        self.is_shattered = False
        self.shatter_finished = False
        self.is_grabbed = False
        self.is_hover_target = False

    @property
    def center_x(self) -> int:
        return int(self.origin_x + self.width / 2.0)

    @property
    def center_y(self) -> int:
        return int(self.origin_y + self.height / 2.0)

    def apply_strike(self, kind: str, direction_x: float = 0.0, direction_y: float = 0.0, force: float = 1.0) -> bool:
        """Combat and touch disabled as of now — clone remains peacefully stationary."""
        return False

    def update(self):
        """No drift, no wobble — clone stays locked in place."""
        pass

    def render_onto(self, canvas: np.ndarray, env_tint: Tuple[float, float, float] = (1.0, 1.0, 1.0)):
        """Composite memory onto canvas with natural grounding and contact shadow."""
        ch, cw = canvas.shape[:2]

        dx = int(self.origin_x)
        dy = int(self.origin_y)

        crop = self.crop_bgra.copy()

        # Environment lighting adaptation
        if env_tint != (1.0, 1.0, 1.0):
            tint_arr = np.array([env_tint[0], env_tint[1], env_tint[2]], dtype=np.float32)
            intensity = 0.20
            effective = (1.0 - intensity) + (tint_arr * intensity)
            crop[:, :, :3] = np.clip(crop[:, :, :3].astype(np.float32) * effective, 0, 255).astype(np.uint8)

        mh, mw = crop.shape[:2]

        # ── Realistic Ground Contact Shadow under clone base ──
        shadow_cx = dx + mw // 2
        shadow_cy = min(ch - 3, dy + mh - 2)
        shadow_w = int(mw * 0.38)
        shadow_h = max(6, int(mh * 0.035))

        if 0 < shadow_cy < ch and 0 < shadow_cx < cw:
            shadow_overlay = canvas.copy()
            cv2.ellipse(shadow_overlay, (shadow_cx, shadow_cy), (shadow_w, shadow_h), 0, 0, 360, (5, 5, 8), -1)
            cv2.ellipse(shadow_overlay, (shadow_cx, shadow_cy + 1), (int(shadow_w * 1.35), int(shadow_h * 1.5)), 0, 0, 360, (15, 15, 22), -1)
            cv2.addWeighted(shadow_overlay, 0.40, canvas, 0.60, 0, canvas)

        # ── Composite Memory Cutout ──
        src_x1 = max(0, -dx)
        src_y1 = max(0, -dy)
        dst_x1 = max(0, dx)
        dst_y1 = max(0, dy)
        src_x2 = min(mw, cw - dx)
        src_y2 = min(mh, ch - dy)
        dst_x2 = dst_x1 + (src_x2 - src_x1)
        dst_y2 = dst_y1 + (src_y2 - src_y1)

        if src_x1 < src_x2 and src_y1 < src_y2 and dst_x1 < cw and dst_y1 < ch:
            patch = crop[src_y1:src_y2, src_x1:src_x2]
            alpha = patch[:, :, 3:4].astype(np.float32) / 255.0
            bgr = patch[:, :, :3].astype(np.float32)
            roi = canvas[dst_y1:dst_y2, dst_x1:dst_x2].astype(np.float32)
            canvas[dst_y1:dst_y2, dst_x1:dst_x2] = (bgr * alpha + roi * (1.0 - alpha)).astype(np.uint8)


class MemoryManager:
    """Manages all frozen temporal clones in TimeSensei."""

    def __init__(self):
        self.memories: List[FrozenMemory] = []
        self._next_id = 1
        self.grabbed_memory: Optional[FrozenMemory] = None

    def create_memory(self, frame_bgr: np.ndarray, alpha_mask: np.ndarray) -> Optional[FrozenMemory]:
        """Create a frozen clone from the current frame and mask, locked to its exact physical position."""
        h, w = frame_bgr.shape[:2]

        binary = (alpha_mask > 0.30).astype(np.uint8)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) < 4500:
            return None

        x, y, bw, bh = cv2.boundingRect(largest)
        pad = 12
        x = max(0, x - pad)
        y = max(0, y - pad)
        bw = min(w - x, bw + 2 * pad)
        bh = min(h - y, bh + 2 * pad)

        bgra = np.zeros((h, w, 4), dtype=np.uint8)
        bgra[:, :, :3] = frame_bgr
        bgra[:, :, 3] = (np.clip(alpha_mask, 0, 1) * 255).astype(np.uint8)

        # Enforce MAX_MEMORIES cap: Evict oldest if ceiling reached
        if len(self.memories) >= settings.MAX_MEMORIES:
            self.memories.pop(0)

        memory = FrozenMemory(
            person_bgra=bgra,
            bbox=(x, y, bw, bh),
            capture_time=time.time(),
            memory_id=self._next_id,
            frame_h=h,
            frame_w=w,
        )
        self._next_id += 1
        self.memories.append(memory)
        return memory

    def update_all(self):
        """Update all active clones."""
        for m in self.memories:
            m.update()

    def render_all(self, canvas: np.ndarray, env_tint: Tuple[float, float, float] = (1.0, 1.0, 1.0)):
        for m in self.memories:
            m.render_onto(canvas, env_tint)

    def find_closest_memory(self, px: int, py: int, max_dist: float = 140.0) -> Optional[FrozenMemory]:
        best = None
        best_dist = max_dist
        for m in self.memories:
            dist = math.hypot(px - m.center_x, py - m.center_y)
            if dist < best_dist:
                best_dist = dist
                best = m
        return best

    def update_hover_targets(self, hand_positions: List[Tuple[int, int]]):
        """Hover target disabled."""
        pass

    def try_grab(self, hand_x: int, hand_y: int) -> bool:
        """Grab disabled — clones stay stationary."""
        return False

    def drag(self, hand_x: int, hand_y: int):
        pass

    def release(self):
        self.grabbed_memory = None

    def clear_all(self):
        self.memories.clear()
        self._next_id = 1
        self.grabbed_memory = None
