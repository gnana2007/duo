"""
TimeSensei Cinematic Startup & Attract Experience
─────────────────────────────────────────────────
Cinematic, eerie Halloween-inspired intro:
  • Charcoal / near-black atmosphere with deep crimson & bone-white typography
  • Subtle procedural film grain, dust scratches, and slow fog
  • Distressed chromatic shadow & breathing scale
  • Three start activations: Mouse Click, ENTER / SPACE, or Open Palm Dwell
  • Vertical timeline scanning laser with "TIMELINE LOCKED" transition
"""
import time
import math
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from config import settings


def _find_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Finds available system font on macOS, Windows, or Linux."""
    candidates = [
        # macOS
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Avenir.ttc",
        "/System/Library/Fonts/Menlo.ttc",
        # Windows
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


_F_TITLE = _find_font(64, bold=True)
_F_SUBTITLE = _find_font(18, bold=True)
_F_BTN = _find_font(18, bold=True)
_F_LOCK = _find_font(32, bold=True)
_F_HINT = _find_font(13)


def _overlay_bgra(canvas_bgr: np.ndarray, overlay_bgra: np.ndarray, x: int, y: int):
    oh, ow = overlay_bgra.shape[:2]
    ch, cw = canvas_bgr.shape[:2]
    x1, y1 = max(x, 0), max(y, 0)
    x2, y2 = min(x + ow, cw), min(y + oh, ch)
    if x1 >= x2 or y1 >= y2:
        return
    ox1, oy1 = x1 - x, y1 - y
    patch = overlay_bgra[oy1:oy1 + (y2 - y1), ox1:ox1 + (x2 - x1)]
    alpha = patch[:, :, 3:4].astype(np.float32) / 255.0
    bgr = patch[:, :, :3].astype(np.float32)
    roi = canvas_bgr[y1:y2, x1:x2].astype(np.float32)
    canvas_bgr[y1:y2, x1:x2] = (bgr * alpha + roi * (1.0 - alpha)).astype(np.uint8)


class IntroRenderer:
    """Renders the cinematic TimeSensei intro and transition sequence."""

    def __init__(self, width: int = settings.CAPTURE_WIDTH, height: int = settings.CAPTURE_HEIGHT):
        self.width = width
        self.height = height

        # Watermark asset (EXPO 2026 Logo)
        self.watermark = None
        wm_path = settings.ASSETS_DIR / "watermark.png"
        if wm_path.exists():
            wm_raw = cv2.imread(str(wm_path), cv2.IMREAD_UNCHANGED)
            if wm_raw is not None and wm_raw.shape[2] == 4:
                self.watermark = cv2.resize(wm_raw, (68, 68), interpolation=cv2.INTER_AREA)

        # Button bounds
        self.btn_w = 340
        self.btn_h = 54
        self.btn_x = (width - self.btn_w) // 2
        self.btn_y = int(height * 0.74)

        # Procedural scratches / dust particles
        np.random.seed(42)
        self.dust_particles = [
            {"x": np.random.uniform(0, width), "y": np.random.uniform(0, height),
             "speed": np.random.uniform(10, 35), "size": np.random.randint(1, 3)}
            for _ in range(40)
        ]

        self.mouse_clicked_start = False
        self.dwell_start_time = None
        self.dwell_progress = 0.0

    def check_mouse_click(self, x: int, y: int) -> bool:
        """Called when a mouse click occurs in the window."""
        if self.btn_x <= x <= self.btn_x + self.btn_w and self.btn_y <= y <= self.btn_y + self.btn_h:
            self.mouse_clicked_start = True
            return True
        return False

    def render_attract(self, live_frame: np.ndarray, hands: List[Dict[str, Any]]) -> Tuple[np.ndarray, bool]:
        """
        Renders the eerie attract screen over the live camera feed.
        Returns: (canvas, start_triggered: bool)
        """
        now = time.time()
        h, w = self.height, self.width

        # ── 1. Desaturate & Darken Live Camera Feed ──
        gray = cv2.cvtColor(live_frame, cv2.COLOR_BGR2GRAY)
        dark_feed = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR).astype(np.float32)
        # Deep vignette / charcoal tint
        dark_feed = dark_feed * 0.22 + np.array([12, 10, 16], dtype=np.float32)
        canvas = np.clip(dark_feed, 0, 255).astype(np.uint8)

        # ── 2. Subtle Drifting Fog / Smoke ──
        fog_offset = int((now * 25) % 180)
        cv2.line(canvas, (0, int(h * 0.60) + int(math.sin(now * 1.5) * 20)),
                 (w, int(h * 0.60) + int(math.cos(now * 1.2) * 20)), (35, 30, 42), 18, cv2.LINE_AA)

        # ── 3. Dust & Scratch Particles ──
        for p in self.dust_particles:
            p["y"] = (p["y"] + p["speed"] * 0.033) % h
            cv2.circle(canvas, (int(p["x"]), int(p["y"])), p["size"], (65, 60, 75), -1)

        # ── 4. Stylized TimeSensei Title (Bone-White + Dried Blood Crimson) ──
        # Very gentle breathing scale
        breathe = math.sin(now * 1.8) * 0.015 + 1.0
        flicker = 1.0
        # Occasional subtle single-frame flicker (every ~4 seconds)
        if int(now * 10) % 43 == 0:
            flicker = 0.70

        pil_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(pil_img)

        title_text = "TimeSensei"
        tw = draw.textlength(title_text, font=_F_TITLE)
        tx = (w - tw) / 2.0
        ty = h * 0.32

        # Dried-blood crimson duplicate drop shadow (eerie chromatic offset)
        crimson = (140, 15, 30, int(190 * flicker))
        draw.text((tx + 3, ty + 4), title_text, font=_F_TITLE, fill=crimson)

        # Faint cyan chromatic tearing
        cyan_glitch = (0, 180, 210, int(60 * flicker))
        draw.text((tx - 2, ty - 1), title_text, font=_F_TITLE, fill=cyan_glitch)

        # Main bone-white title
        bone = (235, 230, 222, int(255 * flicker))
        draw.text((tx, ty), title_text, font=_F_TITLE, fill=bone)

        # Subtitle: CONTROL YOUR TIMELINE
        sub_text = "C O N T R O L   Y O U R   T I M E L I N E"
        stw = draw.textlength(sub_text, font=_F_SUBTITLE)
        sx = (w - stw) / 2.0
        sy = ty + 78
        draw.text((sx, sy), sub_text, font=_F_SUBTITLE, fill=(185, 30, 45, int(230 * flicker)))

        # ── 5. Button: [ ENTER THE TIMELINE ] ──
        bx, by, bw, bh = self.btn_x, self.btn_y, self.btn_w, self.btn_h

        # Check Open Palm Dwell Hover
        inside_hover = False
        hover_pt = None
        for hand in hands:
            for pt in [hand["palm_center"], hand["index_tip"]]:
                if bx <= pt[0] <= bx + bw and by <= pt[1] <= by + bh:
                    inside_hover = True
                    hover_pt = pt
                    break
            if inside_hover:
                break

        triggered = False
        if self.mouse_clicked_start:
            triggered = True
            self.mouse_clicked_start = False
        elif inside_hover:
            if self.dwell_start_time is None:
                self.dwell_start_time = now
            elapsed = now - self.dwell_start_time
            self.dwell_progress = min(1.0, elapsed / settings.START_BUTTON_HOVER_S)
            if self.dwell_progress >= 1.0:
                triggered = True
        else:
            self.dwell_start_time = None
            self.dwell_progress = 0.0

        # Draw Button Pill
        btn_outline = (180, 25, 40, 240) if inside_hover else (140, 135, 130, 180)
        btn_fill = (35, 12, 18, 220) if inside_hover else (18, 18, 24, 200)

        draw.rounded_rectangle([(bx, by), (bx + bw, by + bh)], radius=14,
                               fill=btn_fill, outline=btn_outline, width=2)

        btn_label = "[ ENTER THE TIMELINE ]"
        blw = draw.textlength(btn_label, font=_F_BTN)
        draw.text((bx + (bw - blw) / 2.0, by + 16), btn_label, font=_F_BTN, fill=(245, 242, 235, 255))

        # Helper hint below button
        hint_text = "Hover Open Palm   •   Press SPACE / ENTER   •   Click with Mouse"
        htw = draw.textlength(hint_text, font=_F_HINT)
        draw.text(((w - htw) / 2.0, by + bh + 14), hint_text, font=_F_HINT, fill=(120, 120, 135, 220))

        # Composite PIL overlay onto canvas
        overlay_bgra = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGBA2BGRA)
        alpha = overlay_bgra[:, :, 3:4].astype(np.float32) / 255.0
        bgr = overlay_bgra[:, :, :3].astype(np.float32)
        canvas = (bgr * alpha + canvas.astype(np.float32) * (1.0 - alpha)).astype(np.uint8)

        # ── 6. Circular Dwell Progress Ring if hovering ──
        if inside_hover and hover_pt and self.dwell_progress > 0.05:
            hx, hy = hover_pt
            r = 28
            cv2.circle(canvas, (hx, hy), r, (80, 80, 95), 2, cv2.LINE_AA)
            angle = int(self.dwell_progress * 360)
            cv2.ellipse(canvas, (hx, hy), (r, r), -90, 0, angle, (0, 40, 255), 3, cv2.LINE_AA)

        # ── 7. Top-Left EXPO 2026 Watermark Logo ──
        if self.watermark is not None:
            _overlay_bgra(canvas, self.watermark, 18, 14)

        return canvas, triggered

    def render_entering(self, live_frame: np.ndarray, progress: float) -> np.ndarray:
        """
        Renders the vertical timeline scan transition with 'TIMELINE LOCKED'.
        progress: 0.0 -> 1.0 over ~0.7 seconds.
        """
        h, w = self.height, self.width
        canvas = live_frame.copy()

        # 1. Subtle Logo Glitch in first 25% of transition
        if progress < 0.25:
            glitch_y = int(h * 0.40)
            shift = np.random.randint(-15, 15)
            canvas[glitch_y:glitch_y + 40, max(0, shift):min(w, w + shift)] = (
                live_frame[glitch_y:glitch_y + 40, max(0, -shift):min(w, w - shift)]
            )

        # 2. Vertical Luminous Scanning Laser Line sweeping from top to bottom
        scan_y = int(progress * h)
        if 0 <= scan_y < h:
            # Laser beam line
            cv2.line(canvas, (0, scan_y), (w, scan_y), (0, 60, 255), 3, cv2.LINE_AA)
            cv2.line(canvas, (0, scan_y), (w, scan_y), (255, 255, 255), 1, cv2.LINE_AA)

            # Soft glow around beam
            glow_h = 30
            y1 = max(0, scan_y - glow_h)
            y2 = min(h, scan_y + glow_h)
            glow_patch = canvas[y1:y2, :].astype(np.float32)
            glow_patch[:, :, 0] += 20  # Blue
            glow_patch[:, :, 2] += 60  # Red / crimson glow
            canvas[y1:y2, :] = np.clip(glow_patch, 0, 255).astype(np.uint8)

        # 3. Luminous Banner: "TIMELINE LOCKED"
        banner_w, banner_h = 380, 56
        bx = (w - banner_w) // 2
        by = (h - banner_h) // 2

        overlay = canvas.copy()
        cv2.rectangle(overlay, (bx, by), (bx + banner_w, by + banner_h), (10, 10, 16), -1)
        cv2.rectangle(overlay, (bx, by), (bx + banner_w, by + banner_h), (0, 30, 240), 2, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.70, canvas, 0.30, 0, canvas)

        cv2.putText(canvas, "TIMELINE LOCKED", (bx + 42, by + 38),
                    cv2.FONT_HERSHEY_DUPLEX, 0.95, (240, 235, 225), 2, cv2.LINE_AA)

        # 4. Top-Left EXPO 2026 Watermark Logo
        if self.watermark is not None:
            _overlay_bgra(canvas, self.watermark, 18, 14)

        return canvas
