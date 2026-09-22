"""
Frozen Memory System v3.2
─────────────────────────
Persistent person cutouts with:
  • Grounding to floor plane — NEVER floats in the air
  • Soft ground contact shadow beneath feet
  • Stable, zero-bobbing rendering (no floating movement)
  • Environment lighting adaptation
  • Grab & move with hand gestures
  • Reactive interactions (punch/kick/tickle/touch)
  • No frame or memory numbering badges
"""
import time
import math
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import cv2


class FrozenMemory:
    """One captured person cutout frozen at a specific physical location, grounded to the floor."""

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

        # Feather bottom edge (4 pixels) to prevent harsh floating crop line
        if bh > 8:
            for r in range(min(5, bh)):
                factor = r / 5.0
                self.crop_bgra[bh - 1 - r, :, 3] = (
                    self.crop_bgra[bh - 1 - r, :, 3].astype(np.float32) * factor
                ).astype(np.uint8)

        self.origin_x = x
        self.width = bw
        self.height = bh

        # ── Grounding: Anchor feet to the floor plane (no floating in mid-air) ──
        floor_y = int(frame_h * 0.94)
        if y + bh < floor_y:
            # Shift vertically so feet touch the floor plane
            self.origin_y = max(10, floor_y - bh)
        else:
            self.origin_y = y

        # Reaction state
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.rotation = 0.0
        self.shake_intensity = 0.0
        self.reaction_label = ""
        self.reaction_time = 0.0
        self.reaction_duration = 1.0

        # Grab/move state
        self.is_grabbed = False
        self.grab_offset_x = 0
        self.grab_offset_y = 0

    @property
    def center_x(self) -> int:
        return self.origin_x + self.width // 2

    @property
    def center_y(self) -> int:
        return self.origin_y + self.height // 2

    @property
    def foot_y(self) -> int:
        return self.origin_y + self.height

    def move_to(self, new_cx: int, new_cy: int):
        """Move memory center to new position (for drag & drop)."""
        self.origin_x = new_cx - self.width // 2
        self.origin_y = new_cy - self.height // 2

    def apply_reaction(self, kind: str, direction_x: float = 0, direction_y: float = 0):
        """Trigger a reaction effect."""
        if self.is_grabbed:
            return
        now = time.time()
        self.reaction_time = now
        self.reaction_label = kind

        if kind == "PUNCH!":
            self.offset_x = direction_x * 45
            self.offset_y = -12
            self.rotation = direction_x * 10
            self.shake_intensity = 14.0
            self.reaction_duration = 0.9
        elif kind == "KICK!":
            self.offset_x = direction_x * 55
            self.offset_y = -20
            self.rotation = direction_x * 14
            self.shake_intensity = 18.0
            self.reaction_duration = 1.0
        elif kind == "TICKLE!":
            self.shake_intensity = 8.0
            self.offset_x = direction_x * 12
            self.rotation = 0
            self.reaction_duration = 1.5
        elif kind == "TOUCH":
            self.offset_x = direction_x * 10
            self.offset_y = -5
            self.shake_intensity = 3.0
            self.reaction_duration = 0.7

    def update(self):
        """Animate reaction decay."""
        now = time.time()
        elapsed = now - self.reaction_time

        if self.reaction_label and elapsed > self.reaction_duration:
            self.offset_x = 0
            self.offset_y = 0
            self.rotation = 0
            self.shake_intensity = 0
            self.reaction_label = ""
        elif self.reaction_label:
            self.offset_x *= 0.91
            self.offset_y *= 0.91
            self.rotation *= 0.89
            self.shake_intensity *= 0.87

    def render_onto(self, canvas: np.ndarray, env_tint: Tuple[float, float, float] = (1.0, 1.0, 1.0)):
        """Composite memory onto canvas with grounding and pseudo-3D effects."""
        ch, cw = canvas.shape[:2]

        # Shake displacement (only during punch/kick reactions)
        shake_x, shake_y = 0, 0
        if self.shake_intensity > 0.5:
            shake_x = int(np.random.uniform(-self.shake_intensity, self.shake_intensity))
            shake_y = int(np.random.uniform(-self.shake_intensity * 0.4, self.shake_intensity * 0.4))

        # Final position — stable, zero floating bobbing
        dx = self.origin_x + int(self.offset_x) + shake_x
        dy = self.origin_y + int(self.offset_y) + shake_y

        crop = self.crop_bgra.copy()
        render_w = self.width
        render_h = self.height

        # Apply rotation (during punch/kick)
        if abs(self.rotation) > 0.5:
            rcx, rcy = render_w // 2, render_h // 2
            M = cv2.getRotationMatrix2D((rcx, rcy), self.rotation, 1.0)
            crop = cv2.warpAffine(crop, M, (render_w, render_h),
                                  flags=cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_CONSTANT,
                                  borderValue=(0, 0, 0, 0))

        # Environment lighting adaptation
        if env_tint != (1.0, 1.0, 1.0):
            tint_arr = np.array([env_tint[0], env_tint[1], env_tint[2]], dtype=np.float32)
            intensity = 0.20
            effective = (1.0 - intensity) + (tint_arr * intensity)
            crop_float = crop[:, :, :3].astype(np.float32) * effective
            crop[:, :, :3] = np.clip(crop_float, 0, 255).astype(np.uint8)

        mh, mw = crop.shape[:2]

        # ── Realistic Ground Contact Shadow on the Floor ──
        shadow_cx = dx + mw // 2 + int(self.offset_x * 0.3)
        shadow_cy = min(ch - 3, dy + mh - 2)
        shadow_w = int(mw * 0.38)
        shadow_h = max(7, int(mh * 0.035))

        if 0 < shadow_cy < ch and 0 < shadow_cx < cw:
            shadow_overlay = canvas.copy()
            # Deep inner contact ellipse right at the ground plane
            cv2.ellipse(shadow_overlay, (shadow_cx, shadow_cy),
                        (shadow_w, shadow_h), 0, 0, 360, (5, 5, 8), -1)
            # Soft outer diffuse shadow
            cv2.ellipse(shadow_overlay, (shadow_cx, shadow_cy + 1),
                        (int(shadow_w * 1.35), int(shadow_h * 1.6)), 0, 0, 360, (15, 15, 22), -1)
            cv2.addWeighted(shadow_overlay, 0.45, canvas, 0.55, 0, canvas)

        # ── Clip and composite the memory ──
        src_x1 = max(0, -dx)
        src_y1 = max(0, -dy)
        dst_x1 = max(0, dx)
        dst_y1 = max(0, dy)
        src_x2 = min(mw, cw - dx)
        src_y2 = min(mh, ch - dy)
        dst_x2 = dst_x1 + (src_x2 - src_x1)
        dst_y2 = dst_y1 + (src_y2 - src_y1)

        if src_x1 >= src_x2 or src_y1 >= src_y2:
            return
        if dst_x1 >= cw or dst_y1 >= ch:
            return

        patch = crop[src_y1:src_y2, src_x1:src_x2]
        alpha = patch[:, :, 3:4].astype(np.float32) / 255.0
        bgr = patch[:, :, :3].astype(np.float32)

        roi = canvas[dst_y1:dst_y2, dst_x1:dst_x2].astype(np.float32)
        blended = bgr * alpha + roi * (1.0 - alpha)
        canvas[dst_y1:dst_y2, dst_x1:dst_x2] = blended.astype(np.uint8)

        # ── Rim light (subtle edge glow for 3D presence) ──
        if alpha.shape[0] > 2 and alpha.shape[1] > 2:
            alpha_2d = alpha[:, :, 0]
            edge = cv2.Canny((alpha_2d * 255).astype(np.uint8), 100, 200)
            edge = cv2.dilate(edge, np.ones((2, 2), np.uint8))
            edge_mask = edge > 0
            rim_color = np.array([200, 210, 220], dtype=np.float32)
            for c in range(3):
                ch_slice = canvas[dst_y1:dst_y2, dst_x1:dst_x2, c].astype(np.float32)
                ch_slice[edge_mask] = ch_slice[edge_mask] * 0.70 + rim_color[c] * 0.30
                canvas[dst_y1:dst_y2, dst_x1:dst_x2, c] = np.clip(ch_slice, 0, 255).astype(np.uint8)

        # ── Reaction label (fades upward on interaction) ──
        if self.reaction_label:
            elapsed = time.time() - self.reaction_time
            if elapsed < self.reaction_duration:
                label_y = dst_y1 - 15 - int(elapsed * 35)
                label_x = self.center_x + int(self.offset_x) - 40

                colors = {
                    "PUNCH!": (0, 80, 255),
                    "KICK!": (0, 140, 255),
                    "TICKLE!": (0, 230, 180),
                    "TOUCH": (220, 200, 180),
                }
                color = colors.get(self.reaction_label, (255, 255, 255))
                if 20 < label_y < ch and 0 < label_x < cw - 100:
                    cv2.putText(canvas, self.reaction_label,
                                (label_x, label_y),
                                cv2.FONT_HERSHEY_DUPLEX, 0.9, color, 2, cv2.LINE_AA)


class MemoryManager:
    """Manages all frozen memories."""

    def __init__(self):
        self.memories: List[FrozenMemory] = []
        self._next_id = 1
        self.grabbed_memory: Optional[FrozenMemory] = None

    def create_memory(self, frame_bgr: np.ndarray, alpha_mask: np.ndarray) -> Optional[FrozenMemory]:
        """Create a frozen memory from the current frame and mask, grounded to the floor."""
        h, w = frame_bgr.shape[:2]

        binary = (alpha_mask > 0.3).astype(np.uint8)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) < 5000:
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
        for m in self.memories:
            m.update()

    def render_all(self, canvas: np.ndarray, env_tint: Tuple[float, float, float] = (1.0, 1.0, 1.0)):
        for m in self.memories:
            m.render_onto(canvas, env_tint)

    def find_closest_memory(self, px: int, py: int, max_dist: float = 150) -> Optional[FrozenMemory]:
        best = None
        best_dist = max_dist
        for m in self.memories:
            dist = np.hypot(px - m.center_x, py - m.center_y)
            if dist < best_dist:
                best_dist = dist
                best = m
        return best

    def try_grab(self, hand_x: int, hand_y: int) -> bool:
        """Try to grab the closest memory near the hand position."""
        mem = self.find_closest_memory(hand_x, hand_y, max_dist=100)
        if mem and not mem.is_grabbed:
            mem.is_grabbed = True
            mem.grab_offset_x = mem.origin_x - hand_x
            mem.grab_offset_y = mem.origin_y - hand_y
            self.grabbed_memory = mem
            return True
        return False

    def drag(self, hand_x: int, hand_y: int):
        """Move the grabbed memory horizontally and vertically following the hand."""
        if self.grabbed_memory and self.grabbed_memory.is_grabbed:
            self.grabbed_memory.origin_x = hand_x + self.grabbed_memory.grab_offset_x
            self.grabbed_memory.origin_y = hand_y + self.grabbed_memory.grab_offset_y

    def release(self):
        """Release the grabbed memory at its current horizontal position and ground it to floor."""
        if self.grabbed_memory:
            floor_y = int(self.grabbed_memory.frame_h * 0.94)
            # Ensure it snaps down firmly to the floor plane upon release
            self.grabbed_memory.origin_y = max(10, floor_y - self.grabbed_memory.height)
            self.grabbed_memory.is_grabbed = False
            self.grabbed_memory = None

    def clear_all(self):
        self.memories.clear()
        self._next_id = 1
        self.grabbed_memory = None
