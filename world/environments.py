"""
Virtual Environment Manager v3
──────────────────────────────
Four clean atmospheric environments + the original camera room.
No text on environments.  Smooth gradients and subtle details only.
"""
from dataclasses import dataclass, field
from typing import List, Tuple
from pathlib import Path
import numpy as np
import cv2
from config import settings


@dataclass
class Environment:
    id: str
    name: str
    accent_color_bgr: Tuple[int, int, int]
    ambient_tint_bgr: Tuple[float, float, float]
    brightness_multiplier: float
    contrast_multiplier: float
    image: np.ndarray = field(repr=False)


class EnvironmentManager:
    def __init__(self, width=settings.CAPTURE_WIDTH, height=settings.CAPTURE_HEIGHT):
        self.width = width
        self.height = height
        self.environments: List[Environment] = []
        self.current_index = 0
        # Index 0 will be the "Original Room" — set later from camera
        self._add_original_room_placeholder()
        self._load_or_generate_environments()

    def _add_original_room_placeholder(self):
        """Placeholder for the original camera background — replaced at runtime."""
        placeholder = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        self.environments.append(Environment(
            id="original_room",
            name="Present Reality",
            accent_color_bgr=(180, 190, 200),
            ambient_tint_bgr=(1.0, 1.0, 1.0),
            brightness_multiplier=1.0,
            contrast_multiplier=1.0,
            image=placeholder,
        ))

    def set_original_room(self, bg_frame: np.ndarray):
        """Replace the original room placeholder with the actual captured background."""
        self.environments[0].image = bg_frame.copy()

    def _load_or_generate_environments(self):
        env_configs = [
            {
                "id": "haunted_castle",
                "name": "Haunted Castle",
                "files": ["haunted_castle.jpg", "haunted_room.png"],
                "accent": (40, 45, 190),
                "tint": (0.85, 0.85, 0.92),
                "brightness": 0.88,
                "contrast": 1.18,
                "generator": self._generate_haunted,
            },
            {
                "id": "cyberpunk",
                "name": "Cyberpunk Metropolis",
                "files": ["cyberpunk_loft.png", "neon_metropolis.jpg"],
                "accent": (240, 60, 220),
                "tint": (1.15, 0.90, 1.15),
                "brightness": 1.05,
                "contrast": 1.15,
                "generator": self._generate_arena,
            },
            {
                "id": "sunlit_penthouse",
                "name": "Luxury Penthouse",
                "files": ["sunlit_penthouse.png"],
                "accent": (80, 190, 240),
                "tint": (0.95, 1.05, 1.10),
                "brightness": 1.05,
                "contrast": 1.05,
                "generator": self._generate_interactive_room,
            },
            {
                "id": "space_nebula",
                "name": "Cosmic Nebula",
                "files": ["space_nebula.jpg", "space.png"],
                "accent": (220, 100, 180),
                "tint": (1.20, 0.85, 1.15),
                "brightness": 0.95,
                "contrast": 1.20,
                "generator": self._generate_space,
            },
            {
                "id": "tropical_beach",
                "name": "Sunset Beach",
                "files": ["tropical_beach.jpg"],
                "accent": (60, 180, 255),
                "tint": (0.90, 1.05, 1.15),
                "brightness": 1.05,
                "contrast": 1.05,
                "generator": self._generate_interactive_room,
            },
            {
                "id": "zen_sanctuary",
                "name": "Zen Sanctuary",
                "files": ["zen_sanctuary.png"],
                "accent": (80, 210, 120),
                "tint": (0.95, 1.08, 1.02),
                "brightness": 1.02,
                "contrast": 1.05,
                "generator": self._generate_interactive_room,
            },
            {
                "id": "mystic_forest",
                "name": "Mystic Forest",
                "files": ["mystic_forest.jpg"],
                "accent": (60, 190, 140),
                "tint": (0.90, 1.10, 0.95),
                "brightness": 0.95,
                "contrast": 1.10,
                "generator": self._generate_interactive_room,
            },
            {
                "id": "gallery_studio",
                "name": "Modern Gallery",
                "files": ["gallery_studio.png"],
                "accent": (220, 220, 230),
                "tint": (1.0, 1.0, 1.0),
                "brightness": 1.0,
                "contrast": 1.05,
                "generator": self._generate_arena,
            },
        ]

        for cfg in env_configs:
            loaded_img = None
            for fn in cfg.get("files", [f"{cfg['id']}.png"]):
                fp = settings.ENVIRONMENTS_DIR / fn
                if fp.exists():
                    img = cv2.imread(str(fp))
                    if img is not None:
                        if img.shape[1] != self.width or img.shape[0] != self.height:
                            img = cv2.resize(img, (self.width, self.height), interpolation=cv2.INTER_LINEAR)
                        loaded_img = img
                        break

            if loaded_img is None:
                print(f"[EnvManager] Generating procedural fallback: {cfg['name']}...")
                loaded_img = cfg["generator"]()
                fallback_path = settings.ENVIRONMENTS_DIR / f"{cfg['id']}.png"
                cv2.imwrite(str(fallback_path), loaded_img)

            self.environments.append(Environment(
                id=cfg["id"],
                name=cfg["name"],
                accent_color_bgr=cfg["accent"],
                ambient_tint_bgr=cfg["tint"],
                brightness_multiplier=cfg["brightness"],
                contrast_multiplier=cfg["contrast"],
                image=loaded_img,
            ))

    def current(self) -> Environment:
        return self.environments[self.current_index]

    def next(self) -> Environment:
        self.current_index = (self.current_index + 1) % len(self.environments)
        return self.current()

    def previous(self) -> Environment:
        self.current_index = (self.current_index - 1 + len(self.environments)) % len(self.environments)
        return self.current()

    def is_original_room(self) -> bool:
        return self.current_index == 0

    # ─── PROCEDURAL ENVIRONMENT GENERATORS ───

    def _generate_interactive_room(self) -> np.ndarray:
        h, w = self.height, self.width
        img = np.zeros((h, w, 3), dtype=np.uint8)

        # Warm room walls gradient
        for y in range(int(h * 0.65)):
            t = y / (h * 0.65)
            img[y, :] = (int(55 + 25 * t), int(60 + 30 * t), int(75 + 40 * t))

        # Wooden floor
        floor_y = int(h * 0.65)
        for y in range(floor_y, h):
            t = (y - floor_y) / (h - floor_y)
            img[y, :] = (int(45 + 30 * t), int(70 + 40 * t), int(110 + 50 * t))

        # Floor line
        cv2.line(img, (0, floor_y), (w, floor_y), (60, 80, 100), 2, cv2.LINE_AA)

        # Table (simple wooden rectangle)
        tx, ty = int(w * 0.15), int(h * 0.50)
        tw, th = int(w * 0.22), int(h * 0.15)
        cv2.rectangle(img, (tx, ty), (tx + tw, ty + th), (40, 65, 100), -1)
        cv2.rectangle(img, (tx, ty), (tx + tw, ty + th), (30, 50, 80), 2, cv2.LINE_AA)
        # Table legs
        cv2.rectangle(img, (tx + 5, ty + th), (tx + 15, floor_y), (35, 55, 85), -1)
        cv2.rectangle(img, (tx + tw - 15, ty + th), (tx + tw - 5, floor_y), (35, 55, 85), -1)

        # Chair on right side
        cx, cy = int(w * 0.72), int(h * 0.48)
        cw, ch_chair = int(w * 0.08), int(h * 0.18)
        cv2.rectangle(img, (cx, cy), (cx + cw, cy + ch_chair), (50, 80, 120), -1)
        cv2.rectangle(img, (cx, cy - int(h * 0.12)), (cx + cw, cy), (55, 85, 125), -1)
        cv2.rectangle(img, (cx + 3, cy + ch_chair), (cx + 10, floor_y), (40, 60, 90), -1)
        cv2.rectangle(img, (cx + cw - 10, cy + ch_chair), (cx + cw - 3, floor_y), (40, 60, 90), -1)

        # Ball on floor
        ball_cx, ball_cy = int(w * 0.55), floor_y - 25
        cv2.circle(img, (ball_cx, ball_cy), 25, (60, 80, 200), -1, cv2.LINE_AA)
        cv2.circle(img, (ball_cx - 6, ball_cy - 8), 6, (100, 130, 230), -1, cv2.LINE_AA)

        # Soft ambient light from above
        for x in range(w):
            for y_l in range(min(30, h)):
                t = 1.0 - y_l / 30.0
                px = img[y_l, x].astype(np.float32) + np.array([20, 25, 30]) * t
                img[y_l, x] = np.clip(px, 0, 255).astype(np.uint8)

        return cv2.GaussianBlur(img, (3, 3), 0)

    def _generate_space(self) -> np.ndarray:
        h, w = self.height, self.width
        img = np.zeros((h, w, 3), dtype=np.uint8)

        # Deep cosmic gradient
        for y in range(h):
            t = y / h
            img[y, :] = (int(35 * t), int(12 * t), int(30 * t))

        # Starfield
        np.random.seed(999)
        for _ in range(300):
            sx = np.random.randint(0, w)
            sy = np.random.randint(0, h)
            brightness = np.random.randint(100, 255)
            r = 1 if np.random.rand() > 0.15 else 2
            cv2.circle(img, (sx, sy), r, (brightness, brightness, brightness), -1)

        # Nebula clouds (soft)
        nebula = np.zeros_like(img)
        cv2.circle(nebula, (int(w * 0.25), int(h * 0.35)), int(h * 0.40), (100, 25, 80), -1)
        cv2.circle(nebula, (int(w * 0.75), int(h * 0.45)), int(h * 0.35), (80, 60, 25), -1)
        nebula = cv2.GaussianBlur(nebula, (71, 71), 0)
        img = cv2.add(img, nebula)

        # Planet
        planet_cx, planet_cy = int(w * 0.80), int(h * 0.25)
        cv2.circle(img, (planet_cx, planet_cy), 55, (100, 80, 60), -1, cv2.LINE_AA)
        cv2.circle(img, (planet_cx, planet_cy), 55, (130, 110, 80), 2, cv2.LINE_AA)
        # Ring
        cv2.ellipse(img, (planet_cx, planet_cy), (90, 20), -20, 0, 360, (140, 120, 90), 2, cv2.LINE_AA)

        # Space station floor
        deck_y = int(h * 0.72)
        for y in range(deck_y, h):
            t = (y - deck_y) / (h - deck_y)
            img[y, :] = (int(55 + 25 * t), int(45 + 20 * t), int(40 + 15 * t))
        cv2.line(img, (0, deck_y), (w, deck_y), (200, 160, 100), 2, cv2.LINE_AA)

        # Panel lines on floor
        for x in range(0, w, 100):
            cv2.line(img, (x, deck_y), (x, h), (100, 80, 60), 1)

        return img

    def _generate_haunted(self) -> np.ndarray:
        h, w = self.height, self.width
        img = np.zeros((h, w, 3), dtype=np.uint8)

        # Dark moody gradient
        for y in range(int(h * 0.70)):
            t = y / (h * 0.70)
            img[y, :] = (int(20 + 15 * t), int(18 + 12 * t), int(15 + 10 * t))

        # Cobblestone floor
        floor_y = int(h * 0.70)
        for y in range(floor_y, h):
            t = (y - floor_y) / (h - floor_y)
            img[y, :] = (int(30 + 20 * t), int(28 + 18 * t), int(25 + 15 * t))

        # Atmospheric fog (bright patch in center)
        fog = np.zeros_like(img)
        cv2.circle(fog, (w // 2, int(h * 0.4)), int(h * 0.5), (30, 28, 25), -1)
        fog = cv2.GaussianBlur(fog, (101, 101), 0)
        img = cv2.add(img, fog)

        # Candle glow spots
        np.random.seed(666)
        for _ in range(5):
            cx = np.random.randint(int(w * 0.1), int(w * 0.9))
            cy = np.random.randint(int(h * 0.3), int(h * 0.6))
            glow = np.zeros_like(img)
            cv2.circle(glow, (cx, cy), 40, (15, 40, 60), -1)
            glow = cv2.GaussianBlur(glow, (41, 41), 0)
            img = cv2.add(img, glow)
            # Candle flame
            cv2.circle(img, (cx, cy), 4, (40, 120, 200), -1, cv2.LINE_AA)
            cv2.circle(img, (cx, cy - 5), 2, (60, 180, 255), -1, cv2.LINE_AA)

        # Cobweb in corner
        for i in range(8):
            angle = i * 22.5
            ex = int(40 * np.cos(np.radians(angle)))
            ey = int(40 * np.sin(np.radians(angle)))
            cv2.line(img, (0, 0), (ex * 3, ey * 3), (50, 50, 50), 1, cv2.LINE_AA)

        # Mysterious door
        dx, dy = int(w * 0.42), int(h * 0.15)
        dw_d, dh_d = int(w * 0.16), int(h * 0.55)
        cv2.rectangle(img, (dx, dy), (dx + dw_d, dy + dh_d), (25, 22, 18), -1)
        cv2.rectangle(img, (dx, dy), (dx + dw_d, dy + dh_d), (50, 45, 35), 2, cv2.LINE_AA)
        # Door handle
        cv2.circle(img, (dx + dw_d - 15, dy + dh_d // 2), 5, (80, 75, 60), -1, cv2.LINE_AA)

        return img

    def _generate_arena(self) -> np.ndarray:
        h, w = self.height, self.width
        img = np.zeros((h, w, 3), dtype=np.uint8)

        # Dark arena backdrop
        for y in range(int(h * 0.65)):
            t = y / (h * 0.65)
            img[y, :] = (int(40 * t), int(30 * t), int(20 * t))

        # Arena floor
        floor_y = int(h * 0.65)
        for y in range(floor_y, h):
            t = (y - floor_y) / (h - floor_y)
            img[y, :] = (int(50 + 20 * t), int(45 + 18 * t), int(25 + 15 * t))

        # Perspective grid on floor
        vp_x = w // 2
        for i in range(-8, 9):
            x_bottom = int(vp_x + i * (w / 7.0))
            cv2.line(img, (vp_x, floor_y), (x_bottom, h), (80, 60, 35), 1, cv2.LINE_AA)
        for y in range(floor_y + 15, h, 25):
            cv2.line(img, (0, y), (w, y), (70, 55, 30), 1, cv2.LINE_AA)

        # Arena ring
        cv2.ellipse(img, (w // 2, floor_y), (int(w * 0.35), int(h * 0.12)),
                    0, 0, 360, (255, 200, 50), 2, cv2.LINE_AA)

        # Spotlight beams from top
        for bx in [int(w * 0.25), int(w * 0.50), int(w * 0.75)]:
            beam = np.zeros_like(img)
            pts = np.array([
                [bx - 15, 0],
                [bx + 15, 0],
                [bx + 80, floor_y],
                [bx - 80, floor_y],
            ], np.int32)
            cv2.fillConvexPoly(beam, pts, (15, 15, 10))
            beam = cv2.GaussianBlur(beam, (21, 21), 0)
            img = cv2.add(img, beam)

        # Targets on sides
        for tx, ty in [(int(w * 0.12), int(h * 0.35)), (int(w * 0.88), int(h * 0.35))]:
            cv2.circle(img, (tx, ty), 35, (40, 40, 180), 2, cv2.LINE_AA)
            cv2.circle(img, (tx, ty), 22, (50, 50, 220), 2, cv2.LINE_AA)
            cv2.circle(img, (tx, ty), 8, (60, 60, 255), -1, cv2.LINE_AA)

        # Ball
        ball_cx, ball_cy = int(w * 0.60), floor_y - 20
        cv2.circle(img, (ball_cx, ball_cy), 20, (50, 200, 255), -1, cv2.LINE_AA)
        cv2.circle(img, (ball_cx - 5, ball_cy - 6), 5, (100, 230, 255), -1, cv2.LINE_AA)

        return img
