"""
TimeSensei Temporal Mode Engine
───────────────────────────────
Orchestrates temporal reality states:
  • PRESENT  : Pure real-time reflection with optional frame delay buffer
  • ECHO     : Temporal Echo Mode — 4 distinct delayed past echoes with progressive alpha fading
  • PARADOX  : Inverted dynamic perspective with timeline grid
  • RIFT     : Crimson energy rift with active ember particles
  • ANOMALY  : Playful temporal wisps gravitating towards fingertips
"""
from collections import deque
import time
import numpy as np
import cv2
from config import settings


class PersonalityModeManager:
    """Manages timeline personality modes and temporal echo rendering."""

    def __init__(self):
        self.modes = settings.AVAILABLE_MODES
        self.current_mode_index = 0
        self.delay_frames = settings.MIRROR_DELAY_FRAMES
        self.frame_buffer = deque(maxlen=25)

        # Temporal Echo buffer: (timestamp, frame_bgr, mask)
        self.echo_buffer = deque(maxlen=30)

        # Anomaly mode: autonomous glowing wisps
        self.wisps = [
            {"pos": np.array([320.0, 320.0]), "vel": np.array([0.0, 0.0]), "color": (255, 230, 80)},
            {"pos": np.array([640.0, 260.0]), "vel": np.array([0.0, 0.0]), "color": (100, 240, 255)},
            {"pos": np.array([960.0, 340.0]), "vel": np.array([0.0, 0.0]), "color": (255, 120, 240)}
        ]

        # Rift mode: flame particles
        self.particles = []

    @property
    def current_mode(self) -> str:
        return self.modes[self.current_mode_index]

    def cycle_mode(self) -> str:
        self.current_mode_index = (self.current_mode_index + 1) % len(self.modes)
        self.frame_buffer.clear()
        self.echo_buffer.clear()
        self.particles.clear()
        return self.current_mode

    def set_mode(self, mode_name: str) -> bool:
        if mode_name in self.modes:
            self.current_mode_index = self.modes.index(mode_name)
            self.frame_buffer.clear()
            self.echo_buffer.clear()
            return True
        return False

    def toggle_echo(self) -> str:
        """Toggles between PRESENT and ECHO mode."""
        if self.current_mode == "ECHO":
            self.set_mode("PRESENT")
        else:
            self.set_mode("ECHO")
        return self.current_mode

    def process_frame(self, frame: np.ndarray, alpha_mask: np.ndarray, hands: list, poses: list) -> np.ndarray:
        """Applies active temporal mode visual transforms."""
        mode = self.current_mode
        h, w = frame.shape[:2]

        # ── 1. PRESENT MODE (Optional Latency Buffer) ──
        if mode == "PRESENT":
            if self.delay_frames > 0:
                self.frame_buffer.append(frame.copy())
                if len(self.frame_buffer) > self.delay_frames:
                    return self.frame_buffer.popleft()
            return frame

        # ── 2. ECHO MODE (Temporal Echo with Progressive Past Echoes) ──
        elif mode == "ECHO":
            now = time.time()
            # Downscaled sample for echo buffer
            sw, sh = settings.VISION_WIDTH, settings.VISION_HEIGHT
            small_bgr = cv2.resize(frame, (sw, sh), interpolation=cv2.INTER_LINEAR)
            small_mask = cv2.resize(alpha_mask, (sw, sh), interpolation=cv2.INTER_LINEAR)
            self.echo_buffer.append((now, small_bgr, small_mask))

            out = frame.copy()
            # Sample 3 past timestamps at roughly 6, 12, 18 frames ago (~200ms, ~400ms, ~600ms)
            delay_steps = [6, 12, 18]
            alphas = [0.45, 0.28, 0.16]

            buf_len = len(self.echo_buffer)
            for step, echo_alpha in zip(delay_steps, alphas):
                if buf_len > step:
                    _, past_bgr, past_m = self.echo_buffer[buf_len - 1 - step]
                    full_p_bgr = cv2.resize(past_bgr, (w, h), interpolation=cv2.INTER_LINEAR)
                    full_p_mask = cv2.resize(past_m, (w, h), interpolation=cv2.INTER_LINEAR)

                    # Desaturate and add ethereal cyan tint to older echoes
                    gray = cv2.cvtColor(full_p_bgr, cv2.COLOR_BGR2GRAY)
                    echo_tinted = np.zeros_like(full_p_bgr)
                    echo_tinted[:, :, 0] = np.clip(gray.astype(np.float32) * 1.2, 0, 255).astype(np.uint8)  # Blue
                    echo_tinted[:, :, 1] = np.clip(gray.astype(np.float32) * 1.1, 0, 255).astype(np.uint8)  # Green
                    echo_tinted[:, :, 2] = np.clip(gray.astype(np.float32) * 0.9, 0, 255).astype(np.uint8)  # Red

                    # Blend echo into current frame where mask is active
                    m3 = np.expand_dims(full_p_mask * echo_alpha, axis=-1)
                    out = (echo_tinted.astype(np.float32) * m3 + out.astype(np.float32) * (1.0 - m3)).astype(np.uint8)

            return out

        # ── 3. PARADOX MODE (Inverted Perspective & Spatial Grid) ──
        elif mode == "PARADOX":
            out = frame.copy()
            cv2.line(out, (w // 2, 0), (w // 2, h), (180, 80, 255), 1, cv2.LINE_AA)
            cv2.line(out, (0, h // 2), (w, h // 2), (180, 80, 255), 1, cv2.LINE_AA)
            cv2.putText(out, "PARADOX MODE // INVERTED DYNAMICS", (w // 2 - 170, 40),
                        cv2.FONT_HERSHEY_DUPLEX, 0.6, (220, 160, 255), 1, cv2.LINE_AA)
            return out

        # ── 4. RIFT MODE (Crimson Energy Rift & Fiery Particles) ──
        elif mode == "RIFT":
            out = frame.copy()
            for hand in hands:
                hx, hy = hand["palm_center"]
                for _ in range(4):
                    self.particles.append({
                        "pos": np.array([float(hx) + np.random.uniform(-15, 15), float(hy) + np.random.uniform(-10, 10)]),
                        "vel": np.array([np.random.uniform(-3, 3), np.random.uniform(-8, -2)]),
                        "life": 1.0,
                        "decay": np.random.uniform(0.04, 0.08),
                        "color": (20, np.random.randint(40, 130), 255)  # Crimson ember
                    })

            alive = []
            for p in self.particles:
                p["pos"] += p["vel"]
                p["life"] -= p["decay"]
                if p["life"] > 0:
                    alive.append(p)
                    px, py = int(p["pos"][0]), int(p["pos"][1])
                    if 0 <= px < w and 0 <= py < h:
                        rad = max(1, int(5 * p["life"]))
                        cv2.circle(out, (px, py), rad, p["color"], -1)
            self.particles = alive[:settings.MAX_PARTICLES]
            return out

        # ── 5. ANOMALY MODE (Playful Glowing Temporal Wisps) ──
        elif mode == "ANOMALY":
            out = frame.copy()
            target = np.array([w / 2.0, h / 2.0])
            if hands:
                target = np.array([float(hands[0]["index_tip"][0]), float(hands[0]["index_tip"][1])])

            for wisp in self.wisps:
                desired = target - wisp["pos"]
                dist = np.linalg.norm(desired)
                if dist > 5:
                    desired = (desired / dist) * 7.5
                    steer = desired - wisp["vel"]
                    wisp["vel"] += steer * 0.12
                    wisp["vel"] += np.random.uniform(-0.4, 0.4, size=2)
                wisp["pos"] += wisp["vel"]

                wx, wy = int(wisp["pos"][0]), int(wisp["pos"][1])
                if 0 <= wx < w and 0 <= wy < h:
                    cv2.circle(out, (wx, wy), 16, (255, 255, 255), -1, cv2.LINE_AA)
                    cv2.circle(out, (wx, wy), 26, wisp["color"], 2, cv2.LINE_AA)
                    cv2.circle(out, (wx + 2, wy), 4, (20, 20, 20), -1)

            return out

        return frame
