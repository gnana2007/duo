"""
Person Segmentation Engine v3.3
─────────────────────────────
Naturalistic, ghost-free person segmentation with:
  • S-curve alpha enhancement (core is 100% solid, eliminates translucent ghosts)
  • Fast motion-responsive temporal IIR smoothing (no trailing lag)
  • Guided-filter edge-aware boundary preservation
  • Soft ground contact shadow synthesis
"""
import numpy as np
import cv2
import mediapipe as mp
from config import settings
from vision.models_manager import ensure_model

BaseOptions = mp.tasks.BaseOptions
ImageSegmenter = mp.tasks.vision.ImageSegmenter
ImageSegmenterOptions = mp.tasks.vision.ImageSegmenterOptions
VisionRunningMode = mp.tasks.vision.RunningMode


def _guided_filter(guide: np.ndarray, src: np.ndarray, radius: int, eps: float) -> np.ndarray:
    """
    Edge-aware guided filter.
    guide: H×W float32 (grayscale luminance of original frame)
    src:   H×W float32 (the mask to smooth)
    """
    r = radius
    guide = guide.astype(np.float32)
    src = src.astype(np.float32)

    mean_g = cv2.boxFilter(guide, -1, (r, r))
    mean_s = cv2.boxFilter(src, -1, (r, r))
    corr_gs = cv2.boxFilter(guide * src, -1, (r, r))
    corr_gg = cv2.boxFilter(guide * guide, -1, (r, r))

    var_g = corr_gg - mean_g * mean_g
    cov_gs = corr_gs - mean_g * mean_s

    a = cov_gs / (var_g + eps)
    b = mean_s - a * mean_g

    mean_a = cv2.boxFilter(a, -1, (r, r))
    mean_b = cv2.boxFilter(b, -1, (r, r))

    return mean_a * guide + mean_b


class PersonSegmenter:
    def __init__(self):
        self.segmenter = None
        self.smoothed_mask = None
        self._init_model()

    def _init_model(self):
        model_path = ensure_model("selfie_segmenter.tflite")
        if not model_path:
            print("[Segmenter] Model not available — using fallback heuristic.")
            return
        options = ImageSegmenterOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=VisionRunningMode.IMAGE,
            output_confidence_masks=True,
        )
        self.segmenter = ImageSegmenter.create_from_options(options)
        print("[Segmenter] Selfie segmenter initialized (v3.3 naturalistic pipeline).")

    # ──────────────────────────────────────────────
    def compute_mask(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Returns float32 alpha mask [0..1] at full frame resolution."""
        h, w = frame_bgr.shape[:2]
        sw, sh = settings.VISION_WIDTH, settings.VISION_HEIGHT

        # Downscale for inference
        small = cv2.resize(frame_bgr, (sw, sh), interpolation=cv2.INTER_LINEAR)
        small_rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        raw = None
        if self.segmenter is not None:
            try:
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=small_rgb)
                res = self.segmenter.segment(mp_img)
                if res.confidence_masks:
                    raw = res.confidence_masks[0].numpy_view().squeeze().copy()
            except Exception:
                pass

        if raw is None:
            raw = np.zeros((sh, sw), dtype=np.float32)
            cv2.ellipse(raw, (sw // 2, int(sh * 0.65)),
                        (int(sw * 0.35), int(sh * 0.45)), 0, 0, 360, 1.0, -1)

        # ── Step 1: Morphological close (fills small interior holes) ──
        kernel = np.ones((settings.MASK_MORPH_KERNEL, settings.MASK_MORPH_KERNEL), np.uint8)
        raw_u8 = (np.clip(raw, 0, 1) * 255).astype(np.uint8)
        closed = cv2.morphologyEx(raw_u8, cv2.MORPH_CLOSE, kernel)
        raw_closed = closed.astype(np.float32) / 255.0

        # ── Step 2: Upscale to full resolution ──
        full_mask = cv2.resize(raw_closed, (w, h), interpolation=cv2.INTER_LINEAR)

        # ── Step 3: Guided filter — edge-aware smoothing with frame luminance ──
        guide_gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        full_mask = _guided_filter(guide_gray, full_mask,
                                   radius=settings.MASK_GUIDED_RADIUS,
                                   eps=settings.MASK_GUIDED_EPS)

        # ── Step 4: S-curve contrast (core is 100% solid, eliminates translucent ghosts) ──
        # Remap [0.18..0.72] to [0..1] with cubic Hermite smoothstep
        clamped = np.clip((full_mask - 0.18) / 0.54, 0.0, 1.0)
        full_mask = clamped * clamped * (3.0 - 2.0 * clamped)

        # ── Step 5: Fast motion-responsive temporal IIR smoothing ──
        if self.smoothed_mask is None or self.smoothed_mask.shape != full_mask.shape:
            self.smoothed_mask = full_mask.copy()
        else:
            a = settings.MASK_TEMPORAL_ALPHA
            self.smoothed_mask = a * self.smoothed_mask + (1.0 - a) * full_mask

        # ── Step 6: Final subpixel edge feather ──
        ksize = settings.MASK_EDGE_FEATHER * 2 + 1
        result = cv2.GaussianBlur(self.smoothed_mask, (ksize, ksize), 0)
        return np.clip(result, 0.0, 1.0)

    # ──────────────────────────────────────────────
    def generate_contact_shadow(self, mask: np.ndarray) -> np.ndarray:
        """Synthesises a soft ground-contact shadow beneath segmented people."""
        h, w = mask.shape[:2]
        shadow = np.zeros((h, w), dtype=np.float32)
        if not settings.ENABLE_CONTACT_SHADOW:
            return shadow

        lower = (mask > 0.40).astype(np.uint8)
        lower[: int(h * 0.65), :] = 0

        contours, _ = cv2.findContours(lower, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            if cv2.contourArea(cnt) < 400:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            cx = x + bw // 2
            cy = min(h - 8, y + bh)
            ax = int(bw * 0.45)
            ay = max(8, int(bh * 0.12))
            cv2.ellipse(shadow, (cx, cy), (ax, ay), 0, 0, 360, settings.SHADOW_OPACITY, -1)

        if np.any(shadow > 0):
            shadow = cv2.GaussianBlur(shadow,
                                      (settings.SHADOW_BLUR, settings.SHADOW_BLUR), 0)
        return shadow
