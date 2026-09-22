"""
Personality Mode Engine
Implements Mirror (with configurable frame delay), Opposite, Lazy, Angry, and Curious behaviors.
"""
from collections import deque
import time
import numpy as np
import cv2
from config import settings


class PersonalityModeManager:
    def __init__(self):
        self.modes = settings.AVAILABLE_MODES
        self.current_mode_index = 0
        self.delay_frames = settings.MIRROR_DELAY_FRAMES
        self.frame_buffer = deque(maxlen=20)
        self.ghost_buffer = deque(maxlen=6)
        
        # Curious mode: autonomous glowing wisps
        self.wisps = [
            {"pos": np.array([300.0, 300.0]), "vel": np.array([0.0, 0.0]), "color": (255, 230, 80)},
            {"pos": np.array([600.0, 250.0]), "vel": np.array([0.0, 0.0]), "color": (100, 240, 255)},
            {"pos": np.array([900.0, 350.0]), "vel": np.array([0.0, 0.0]), "color": (255, 120, 240)}
        ]

        # Angry mode: flame particle system
        self.particles = []

    @property
    def current_mode(self) -> str:
        return self.modes[self.current_mode_index]

    def cycle_mode(self) -> str:
        self.current_mode_index = (self.current_mode_index + 1) % len(self.modes)
        self.frame_buffer.clear()
        self.ghost_buffer.clear()
        return self.current_mode

    def set_delay(self, frames: int):
        self.delay_frames = max(0, min(15, frames))

    def process_frame(self, frame: np.ndarray, hands: list, poses: list) -> np.ndarray:
        """
        Applies personality mode transformations and atmospheric particle visuals.
        """
        mode = self.current_mode
        h, w = frame.shape[:2]

        # 1. Configurable Mirror Delay Buffer
        if self.delay_frames > 0:
            self.frame_buffer.append(frame.copy())
            if len(self.frame_buffer) > self.delay_frames:
                frame = self.frame_buffer.popleft()

        # 2. Personality-Specific Visual Processing
        if mode == "Mirror":
            # Pure clean mirror with optional delay
            return frame

        elif mode == "Opposite":
            # Opposite mode: Add dynamic inverted holographic grid & crosshairs
            cv2.line(frame, (w // 2, 0), (w // 2, h), (180, 80, 255), 1)
            cv2.putText(frame, "OPPOSITE MODE: INVERTED DYNAMICS", (w // 2 - 140, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 160, 255), 1)
            return frame

        elif mode == "Lazy":
            # Lazy mode: Ghostly trailing motion blur
            self.ghost_buffer.append(frame.copy())
            blended = frame.astype(np.float32)
            alpha_weight = 0.25
            for past_frame in list(self.ghost_buffer)[:-1]:
                blended = blended * (1.0 - alpha_weight) + past_frame.astype(np.float32) * alpha_weight
            return np.clip(blended, 0, 255).astype(np.uint8)

        elif mode == "Angry":
            # Angry mode: Red lightning aura & fiery embers bursting from hands/shoulders
            out = frame.copy()
            # Spawn embers from active hands
            for hand in hands:
                hx, hy = hand["palm_center"]
                for _ in range(4):
                    self.particles.append({
                        "pos": np.array([float(hx) + np.random.uniform(-15, 15), float(hy) + np.random.uniform(-10, 10)]),
                        "vel": np.array([np.random.uniform(-3, 3), np.random.uniform(-7, -2)]),
                        "life": 1.0,
                        "decay": np.random.uniform(0.04, 0.08),
                        "color": (20, np.random.randint(50, 150), 255) # Red-orange embers
                    })

            # Update and draw particles
            alive = []
            for p in self.particles:
                p["pos"] += p["vel"]
                p["life"] -= p["decay"]
                if p["life"] > 0:
                    alive.append(p)
                    px, py = int(p["pos"][0]), int(p["pos"][1])
                    if 0 <= px < w and 0 <= py < h:
                        rad = max(1, int(6 * p["life"]))
                        cv2.circle(out, (px, py), rad, p["color"], -1)
            self.particles = alive[:120]

            # Red vignette border
            cv2.rectangle(out, (0, 0), (w, h), (0, 0, 180), 3)
            return out

        elif mode == "Curious":
            # Curious mode: Glowing wisps playfully flock towards fingertips
            out = frame.copy()
            # Target is the first index tip, or screen center
            target = np.array([w / 2.0, h / 2.0])
            if hands:
                target = np.array([float(hands[0]["index_tip"][0]), float(hands[0]["index_tip"][1])])

            for wisp in self.wisps:
                # Seek steering force
                desired = target - wisp["pos"]
                dist = np.linalg.norm(desired)
                if dist > 5:
                    desired = (desired / dist) * 8.0 # max speed
                    steer = desired - wisp["vel"]
                    wisp["vel"] += steer * 0.12
                    wisp["vel"] += np.random.uniform(-0.5, 0.5, size=2) # Jitter
                wisp["pos"] += wisp["vel"]

                wx, wy = int(wisp["pos"][0]), int(wisp["pos"][1])
                if 0 <= wx < w and 0 <= wy < h:
                    # Glowing orb layers
                    cv2.circle(out, (wx, wy), 18, (255, 255, 255), -1)
                    cv2.circle(out, (wx, wy), 28, wisp["color"], 2)
                    # Playful eye pupil
                    cv2.circle(out, (wx + 2, wy), 5, (20, 20, 20), -1)

            return out

        return frame
