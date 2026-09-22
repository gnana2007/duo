"""
Scene Transition Manager v3
───────────────────────────
Smooth horizontal slide transitions between environments.
Memories persist across transitions.
"""
import time
import numpy as np
import cv2
from config import settings
from world.environments import EnvironmentManager, Environment


class Scene:
    def __init__(self, env_manager: EnvironmentManager):
        self.env_manager = env_manager
        self.transitioning = False
        self.transition_start_time = 0.0
        self.transition_duration = settings.ENV_TRANSITION_DURATION
        self.transition_direction = 0
        self.from_env: Environment = None
        self.to_env: Environment = None

    def trigger_swipe(self, direction: int):
        """
        direction = -1  ->  previous environment (left hand triple-swipe)
        direction = +1  ->  next environment (right hand triple-swipe)
        """
        if self.transitioning:
            return
        self.from_env = self.env_manager.current()
        if direction > 0:
            self.to_env = self.env_manager.next()
        else:
            self.to_env = self.env_manager.previous()
        self.transition_direction = direction
        self.transition_start_time = time.time()
        self.transitioning = True

    def get_background(self) -> np.ndarray:
        """Returns current background, interpolated during transitions."""
        if not self.transitioning:
            return self.env_manager.current().image.copy()

        elapsed = time.time() - self.transition_start_time
        progress = min(1.0, elapsed / self.transition_duration)

        if progress >= 1.0:
            self.transitioning = False
            return self.env_manager.current().image.copy()

        # Ease-out cubic
        ease = 1.0 - (1.0 - progress) ** 3
        h, w = self.from_env.image.shape[:2]
        shift = int(ease * w)

        canvas = np.zeros_like(self.from_env.image)
        if self.transition_direction > 0:
            # Slide right: old exits right, new enters from left
            if shift < w:
                canvas[:, shift:] = self.from_env.image[:, :w - shift]
            if shift > 0:
                canvas[:, :shift] = self.to_env.image[:, w - shift:]
        else:
            # Slide left: old exits left, new enters from right
            if shift < w:
                canvas[:, :w - shift] = self.from_env.image[:, shift:]
            if shift > 0:
                canvas[:, w - shift:] = self.to_env.image[:, :shift]

        return canvas

    def current_environment(self) -> Environment:
        return self.env_manager.current()

    def is_original_room(self) -> bool:
        return self.env_manager.is_original_room() and not self.transitioning
