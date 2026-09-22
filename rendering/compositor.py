"""
Natural Compositor Engine
Blends segmented subjects into virtual environments with lighting adaptation,
contact shadows, edge defringing, and anti-aliasing.
"""
import numpy as np
import cv2
from config import settings
from world.environments import Environment


class NaturalCompositor:
    def __init__(self):
        pass

    def adapt_lighting(self, fg: np.ndarray, env: Environment) -> np.ndarray:
        """
        Adapts the foreground subject's color temperature and contrast
        to match the virtual environment's ambient lighting profile.
        """
        # Convert to float for accurate color transformations
        fg_float = fg.astype(np.float32)
        
        # Apply environment ambient tint (B, G, R multiplier)
        tint = np.array(env.ambient_tint_bgr, dtype=np.float32)
        intensity = settings.COLOR_MATCH_INTENSITY
        
        # Weighted tint blend: (1 - intensity) + tint * intensity
        effective_tint = (1.0 - intensity) + (tint * intensity)
        fg_tinted = fg_float * effective_tint

        # Apply brightness & contrast tuning
        fg_adjusted = (fg_tinted - 128.0) * env.contrast_multiplier + 128.0
        fg_adjusted = fg_adjusted * env.brightness_multiplier
        
        return np.clip(fg_adjusted, 0.0, 255.0).astype(np.uint8)

    def defringe_edges(self, fg: np.ndarray, alpha: np.ndarray) -> np.ndarray:
        """
        Reduces color bleeding / halo artifacts along the silhouette boundaries.
        """
        # Find semi-transparent boundary regions (alpha between 0.08 and 0.88)
        border_mask = ((alpha > 0.08) & (alpha < 0.88)).astype(np.uint8)
        if not np.any(border_mask):
            return fg

        # Erode alpha slightly to get pure inner foreground
        inner_mask = (alpha >= 0.88).astype(np.uint8)
        if not np.any(inner_mask):
            return fg

        # Inpaint/smear inner foreground colors slightly into the boundary zone
        # to remove real-world background light bleed
        dilated_inner = cv2.dilate(fg, np.ones((settings.DEFRINGE_RADIUS * 2 + 1, settings.DEFRINGE_RADIUS * 2 + 1), np.uint8))
        
        # Blend border pixels towards dilated inner core
        defringed = fg.copy()
        weight = (border_mask[..., None] * 0.45).astype(np.float32)
        defringed = (fg * (1.0 - weight) + dilated_inner * weight).astype(np.uint8)
        return defringed

    def composite(
        self,
        fg_frame: np.ndarray,
        bg_frame: np.ndarray,
        alpha_mask: np.ndarray,
        shadow_mask: np.ndarray,
        env: Environment
    ) -> np.ndarray:
        """
        Executes full natural compositing pipeline.
        Returns final 1280x720 3-channel BGR image.
        """
        h, w = fg_frame.shape[:2]

        # 1. Environment Lighting & Color Adaptation
        adapted_fg = self.adapt_lighting(fg_frame, env)

        # 2. Defringe Boundary Halos
        clean_fg = self.defringe_edges(adapted_fg, alpha_mask)

        # 3. Ground Contact Shadow Synthesis
        # Dim the background where shadows are cast
        bg_shadowed = bg_frame.astype(np.float32)
        if shadow_mask is not None and np.any(shadow_mask > 0):
            # shadow factor (1.0 - shadow_mask) dims the background
            shadow_factor = 1.0 - np.clip(shadow_mask[..., None], 0.0, 0.75)
            bg_shadowed = bg_shadowed * shadow_factor

        # 4. Multi-channel Alpha Blending
        alpha_3ch = np.expand_dims(alpha_mask, axis=-1).astype(np.float32)
        
        composite_float = (clean_fg.astype(np.float32) * alpha_3ch) + (bg_shadowed * (1.0 - alpha_3ch))
        return np.clip(composite_float, 0.0, 255.0).astype(np.uint8)
