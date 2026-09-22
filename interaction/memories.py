"""
TimeSensei Temporal Memory System
───────────────────────────────────
Manages persistent frozen temporal clones ("memories") with:
  • Crisp, razor-sharp silhouette cropping (zero blur, zero room wall bleed)
  • Strict Depth Ordering: First picture in front, later pictures behind if collided
  • Seamless Environment Lighting Adaptation via hardware LUTs (feels captured in each world)
  • Localized, natural ground contact shadows (no whole-canvas blurring)
  • Precise spatial anchoring (clones stay locked exactly where the visitor posed)
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

    _lut_cache: Dict[Tuple, np.ndarray] = {}

    def __init__(
        self,
        crop_bgr: np.ndarray,
        crop_alpha: np.ndarray,
        origin_x: int,
        origin_y: int,
        capture_time: float,
        memory_id: int,
        frame_h: int,
        frame_w: int,
    ):
        self.memory_id = memory_id
        self.capture_time = capture_time
        self.frame_h = frame_h
        self.frame_w = frame_w

        # Razor-sharp RGB cutout and solid alpha mask
        self.crop_bgr = crop_bgr.copy()
        self.crop_alpha = crop_alpha.copy()

        # Spatial Anchoring: Lock clone exactly where visitor was standing
        self.origin_x = float(origin_x)
        self.origin_y = float(origin_y)
        self.height, self.width = crop_bgr.shape[:2]

        # Stationarity
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.rotation = 0.0
        self.shake_intensity = 0.0
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
        return False

    def update(self):
        """Clone stays stationary."""
        pass

    @classmethod
    def _get_env_lut(cls, env: Any) -> Optional[np.ndarray]:
        """Computes or retrieves cached 1x256x3 hardware Look-Up Table matching active environment."""
        if env is None or getattr(env, "id", "") == "original_room":
            return None

        ambient_tint = getattr(env, "ambient_tint_bgr", (1.0, 1.0, 1.0))
        brightness = getattr(env, "brightness_multiplier", 1.0)
        contrast = getattr(env, "contrast_multiplier", 1.0)
        env_id = getattr(env, "id", "custom")

        key = (env_id, ambient_tint, brightness, contrast)
        lut = cls._lut_cache.get(key)
        if lut is not None:
            return lut

        tint = np.array(ambient_tint, dtype=np.float32)
        intensity = settings.COLOR_MATCH_INTENSITY
        effective_tint = (1.0 - intensity) + (tint * intensity)

        lut_arr = np.zeros((1, 256, 3), dtype=np.uint8)
        for i in range(256):
            for c in range(3):
                val = (i * effective_tint[c] - 128.0) * contrast + 128.0
                lut_arr[0, i, c] = int(np.clip(val * brightness, 0.0, 255.0))

        cls._lut_cache[key] = lut_arr
        return lut_arr

    def render_shadow(self, canvas: np.ndarray):
        """
        Renders localized ground contact shadow under clone base.
        Restricted to a local bounding box under the feet — zero full-canvas blurs.
        """
        ch, cw = canvas.shape[:2]
        dx = int(self.origin_x)
        dy = int(self.origin_y)
        mw, mh = self.width, self.height

        shadow_cx = dx + mw // 2
        shadow_cy = min(ch - 4, dy + mh - 2)
        shadow_rx = int(mw * 0.36)
        shadow_ry = max(5, int(mh * 0.032))

        # Local ROI bounds
        x1 = max(0, shadow_cx - shadow_rx * 2)
        x2 = min(cw, shadow_cx + shadow_rx * 2)
        y1 = max(0, shadow_cy - shadow_ry * 2)
        y2 = min(ch, shadow_cy + shadow_ry * 2)

        if x2 > x1 and y2 > y1 and shadow_cy > 0:
            roi_h, roi_w = y2 - y1, x2 - x1
            local_shadow = np.zeros((roi_h, roi_w), dtype=np.float32)
            local_cx = shadow_cx - x1
            local_cy = shadow_cy - y1

            # Inner dense contact + soft outer falloff
            cv2.ellipse(local_shadow, (local_cx, local_cy), (shadow_rx, shadow_ry), 0, 0, 360, 0.40, -1)
            cv2.ellipse(local_shadow, (local_cx, local_cy + 1), (int(shadow_rx * 1.3), int(shadow_ry * 1.4)), 0, 0, 360, 0.20, -1)
            local_shadow = cv2.GaussianBlur(local_shadow, (15, 15), 0)

            factor = 1.0 - local_shadow[..., None]
            canvas[y1:y2, x1:x2] = (canvas[y1:y2, x1:x2].astype(np.float32) * factor).astype(np.uint8)

    def render_person(self, canvas: np.ndarray, env: Any = None):
        """
        Composites the crisp person cutout onto canvas, dynamically adapted to active environment.
        """
        ch, cw = canvas.shape[:2]
        dx = int(self.origin_x)
        dy = int(self.origin_y)
        mw, mh = self.width, self.height

        # Dynamic environment lighting adaptation
        lut = self._get_env_lut(env)
        if lut is not None:
            adapted_bgr = cv2.LUT(self.crop_bgr, lut)
        elif isinstance(env, tuple) and env != (1.0, 1.0, 1.0):
            # Backward-compat tuple tint
            tint_arr = np.array([env[0], env[1], env[2]], dtype=np.float32)
            intensity = settings.COLOR_MATCH_INTENSITY
            eff = (1.0 - intensity) + (tint_arr * intensity)
            adapted_bgr = np.clip(self.crop_bgr.astype(np.float32) * eff, 0, 255).astype(np.uint8)
        else:
            adapted_bgr = self.crop_bgr

        # Canvas ROI intersection
        src_x1 = max(0, -dx)
        src_y1 = max(0, -dy)
        dst_x1 = max(0, dx)
        dst_y1 = max(0, dy)
        src_x2 = min(mw, cw - dx)
        src_y2 = min(mh, ch - dy)
        dst_x2 = dst_x1 + (src_x2 - src_x1)
        dst_y2 = dst_y1 + (src_y2 - src_y1)

        if src_x1 < src_x2 and src_y1 < src_y2 and dst_x1 < cw and dst_y1 < ch:
            patch_bgr = adapted_bgr[src_y1:src_y2, src_x1:src_x2].astype(np.float32)
            patch_alpha = self.crop_alpha[src_y1:src_y2, src_x1:src_x2, None]
            roi = canvas[dst_y1:dst_y2, dst_x1:dst_x2].astype(np.float32)
            canvas[dst_y1:dst_y2, dst_x1:dst_x2] = (
                patch_bgr * patch_alpha + roi * (1.0 - patch_alpha)
            ).astype(np.uint8)

    def render_onto(self, canvas: np.ndarray, env: Any = None):
        """Unified rendering for single memory."""
        self.render_shadow(canvas)
        self.render_person(canvas, env)


class MemoryManager:
    """Manages all frozen temporal clones in TimeSensei with depth sorting."""

    def __init__(self):
        self.memories: List[FrozenMemory] = []
        self._next_id = 1
        self.grabbed_memory: Optional[FrozenMemory] = None

    def create_memory(self, frame_bgr: np.ndarray, alpha_mask: np.ndarray) -> Optional[FrozenMemory]:
        """
        Creates a razor-sharp frozen clone from the current frame and mask:
          • Rejects all room background bleed (wall, furniture, boxes).
          • Preserves 100% authentic sensor pixel sharpness inside body (no blur/smearing).
          • Anti-aliases the 1-pixel boundary so it blends seamlessly into any virtual world.
        """
        h, w = frame_bgr.shape[:2]

        binary = (alpha_mask > 0.04).astype(np.uint8)
        if not np.any(binary):
            return None

        # Encompass ALL person pixels (including thin fingers, peace signs, and hair)
        bx, by, bw, bh = cv2.boundingRect(binary)
        if bw < 10 or bh < 10:
            return None

        # Generous safety padding (48px) to guarantee zero clipping of fingers or gestures
        pad = 48
        x1 = max(0, bx - pad)
        y1 = max(0, by - pad)
        x2 = min(w, bx + bw + pad)
        y2 = min(h, by + bh + pad)
        bw = x2 - x1
        bh = y2 - y1

        roi_bgr = frame_bgr[y1:y2, x1:x2].copy()
        raw_roi_alpha = alpha_mask[y1:y2, x1:x2].copy()

        # ── Step 1: Smooth S-curve preserving fine fingers, gestures, and hair ──
        # Any confidence > 0.40 becomes solid 1.0 opacity (zero translucency on clothing/body)
        # Any confidence < 0.10 fades smoothly to background
        clean_alpha = np.zeros_like(raw_roi_alpha, dtype=np.float32)
        span = 0.30
        t = np.clip((raw_roi_alpha - 0.10) / span, 0.0, 1.0)
        clean_alpha = t * t * (3.0 - 2.0 * t)

        # ── Step 2: Multi-scale boundary color extension (eliminates black/dark halos) ──
        # Propagate inner body colors into the boundary transition zone (alpha between 0.01 and 0.70)
        # so that edge pixels carry authentic skin/clothing color instead of dark room shadow.
        inner = (clean_alpha >= 0.70).astype(np.uint8)
        border = (clean_alpha > 0.01) & (clean_alpha < 0.70)
        if np.any(inner) and np.any(border):
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
            dilated_colors = cv2.dilate(roi_bgr * inner[..., None], k, iterations=2)
            dilated_weights = cv2.dilate(inner, k, iterations=2)
            valid = (dilated_weights > 0) & border
            if np.any(valid):
                roi_bgr[valid] = dilated_colors[valid]

        # Only clear pixels that are completely transparent
        roi_bgr[clean_alpha == 0] = 0

        # Only feather bottom edge if the person was actually cut off at the bottom frame edge
        if y2 >= h - 2 and bh > 12:
            for r in range(min(6, bh)):
                factor = r / 6.0
                clean_alpha[bh - 1 - r, :] *= factor

        # Enforce MAX_MEMORIES cap (FIFO eviction)
        if len(self.memories) >= settings.MAX_MEMORIES:
            self.memories.pop(0)

        memory = FrozenMemory(
            crop_bgr=roi_bgr,
            crop_alpha=clean_alpha,
            origin_x=x1,
            origin_y=y1,
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

    def render_all(self, canvas: np.ndarray, env: Any = None):
        """
        Renders all temporal memories with strict depth ordering:
          1. Floor contact shadows are rendered first (on the ground).
          2. Clones are rendered in reverse chronological order:
             • Later pictures (P2, P3...) are drawn first (in the background).
             • First picture (P1) is drawn last (in the foreground, at first).
             • If collided: first picture stays at first in front, later pictures behind.
             • If not collided: both pictures appear crisp and unhindered.
        """
        if not self.memories:
            return

        # Pass 1: Floor contact shadows underneath all clones
        for m in reversed(self.memories):
            m.render_shadow(canvas)

        # Pass 2: Person cutouts (reversed: earliest clone rendered last = in front)
        for m in reversed(self.memories):
            m.render_person(canvas, env)

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
        pass

    def try_grab(self, hand_x: int, hand_y: int) -> bool:
        return False

    def drag(self, hand_x: int, hand_y: int):
        pass

    def release(self):
        self.grabbed_memory = None

    def clear_all(self):
        self.memories.clear()
        self._next_id = 1
        self.grabbed_memory = None
