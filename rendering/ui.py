"""
TimeSensei UI & Overlay Renderer
────────────────────────────────
Renders the minimalist visitor HUD, micro-tutorial prompts, temporal capture overlays,
watermarking, palm freeze progress rings, and developer diagnostics.
"""
from typing import List, Dict, Any, Optional, Tuple
import time
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from config import settings


def _find_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Finds available system fonts on macOS, Windows, or Linux."""
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


_F_TITLE = _find_font(16, bold=True)
_F_SUB = _find_font(12)
_F_LARGE = _find_font(26, bold=True)
_F_SMALL = _find_font(11)
_F_COUNTDOWN = _find_font(72, bold=True)
_F_STATUS = _find_font(14, bold=True)
_F_HINT = _find_font(12)
_F_BTN = _find_font(15, bold=True)
_F_TUTORIAL = _find_font(18, bold=True)


def _pil_to_cv(pil_img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGBA2BGRA)


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


class UIRenderer:
    """TimeSensei UI Engine for HUD, micro-tutorials, QR popups, and watermarks."""

    def __init__(self):
        self._pill_cache = {}
        # Tutorial state machine: 0: SHOW PALM, 1: WALK AWAY, 2: PUNCH YOUR PAST, 3: DONE
        self.tutorial_step = 0
        self.tutorial_step_time = time.time()

    def reset_tutorial(self):
        self.tutorial_step = 0
        self.tutorial_step_time = time.time()

    def draw_capture_zone(self, canvas: np.ndarray, person_in_zone: bool):
        """Draws subtle corner brackets indicating full-body placement zone."""
        h, w = canvas.shape[:2]
        zx = int(w * settings.CAPTURE_ZONE_X_RATIO)
        zy = int(h * settings.CAPTURE_ZONE_Y_RATIO)
        zw = int(w * settings.CAPTURE_ZONE_W_RATIO)
        zh = int(h * settings.CAPTURE_ZONE_H_RATIO)

        color = (180, 40, 60) if person_in_zone else (90, 85, 95)
        thick = 2 if person_in_zone else 1
        cl = 30  # corner bracket length

        corners = [
            ((zx, zy), (zx + cl, zy), (zx, zy + cl)),
            ((zx + zw, zy), (zx + zw - cl, zy), (zx + zw, zy + cl)),
            ((zx, zy + zh), (zx + cl, zy + zh), (zx, zy + zh - cl)),
            ((zx + zw, zy + zh), (zx + zw - cl, zy + zh), (zx + zw, zy + zh - cl)),
        ]
        for origin, h_end, v_end in corners:
            cv2.line(canvas, origin, h_end, color, thick, cv2.LINE_AA)
            cv2.line(canvas, origin, v_end, color, thick, cv2.LINE_AA)

    def draw_victory_freeze_progress(self, canvas: np.ndarray, finger_pos: Tuple[int, int], progress: float):
        """Draws glowing circular temporal ring around fingers while holding Victory sign."""
        if finger_pos is None or progress <= 0.05:
            return
        px, py = finger_pos
        radius = 38
        # Outer track
        cv2.circle(canvas, (px, py), radius, (60, 60, 75), 2, cv2.LINE_AA)
        # Glowing progress arc (starts top, sweeps clockwise)
        angle = int(progress * 360)
        cv2.ellipse(canvas, (px, py), (radius, radius), -90, 0, angle, (0, 70, 255), 3, cv2.LINE_AA)
        cv2.ellipse(canvas, (px, py), (radius - 2, radius - 2), -90, 0, angle, (200, 240, 255), 1, cv2.LINE_AA)

        # Label above fingers
        cv2.putText(canvas, "FREEZING TIME...", (px - 58, py - 46),
                    cv2.FONT_HERSHEY_DUPLEX, 0.45, (235, 230, 220), 1, cv2.LINE_AA)

    # Alias for compatibility
    draw_palm_freeze_progress = draw_victory_freeze_progress

    def draw_hud(self, canvas: np.ndarray, timeline_name: str,
                 timeline_accent: Tuple[int, int, int], memory_count: int,
                 mode_name: str, fps: float, grabbed: bool = False):
        """Renders minimal dark glass visitor HUD."""
        h, w = canvas.shape[:2]

        # Top-Left: Timeline Pill
        pill_tl = Image.new("RGBA", (280, 42), (0, 0, 0, 0))
        d_tl = ImageDraw.Draw(pill_tl)
        d_tl.rounded_rectangle([(0, 0), (279, 41)], radius=12,
                               fill=(14, 16, 22, 190),
                               outline=(160, 30, 45, 220), width=1)
        # Accent indicator
        d_tl.ellipse([(12, 16), (20, 24)], fill=(timeline_accent[0], timeline_accent[1], timeline_accent[2], 255))
        d_tl.text((28, 11), f"TIMELINE // {timeline_name.upper()}", font=_F_TITLE, fill=(240, 238, 230, 255))
        _overlay_bgra(canvas, _pil_to_cv(pill_tl), 16, 16)

        # Top-Right: Echoes & Mode Pill
        pill_tr = Image.new("RGBA", (260, 42), (0, 0, 0, 0))
        d_tr = ImageDraw.Draw(pill_tr)
        d_tr.rounded_rectangle([(0, 0), (259, 41)], radius=12,
                               fill=(14, 16, 22, 190),
                               outline=(80, 85, 100, 180), width=1)
        d_tr.text((14, 11), f"ECHOES: {memory_count}   MODE: {mode_name}", font=_F_TITLE, fill=(210, 215, 225, 240))
        _overlay_bgra(canvas, _pil_to_cv(pill_tr), w - 276, 16)

        # Bottom Hints Bar
        hints_img = Image.new("RGBA", (780, 34), (0, 0, 0, 0))
        d_h = ImageDraw.Draw(hints_img)
        d_h.rounded_rectangle([(0, 0), (779, 33)], radius=10,
                              fill=(12, 14, 18, 170),
                              outline=(60, 65, 80, 150), width=1)
        hints = "✌️ Two Fingers: Freeze Time   •   ✋ Palm Swipe: Switch World   •   👍 Thumb: QR   •   P: Photo"
        tw = d_h.textlength(hints, font=_F_HINT)
        d_h.text(((780 - tw) / 2, 8), hints, font=_F_HINT, fill=(180, 185, 195, 220))
        _overlay_bgra(canvas, _pil_to_cv(hints_img), w // 2 - 390, h - 48)

    def draw_micro_tutorial(self, canvas: np.ndarray, has_person: bool, memory_count: int):
        """Minimal 5-second onboarding without a tutorial screen."""
        if not has_person or self.tutorial_step >= 3:
            return

        now = time.time()
        elapsed = now - self.tutorial_step_time
        h, w = canvas.shape[:2]

        msg = ""
        # Step 0: Initial prompt
        if self.tutorial_step == 0:
            msg = "SHOW TWO FINGERS (✌️) TO FREEZE TIME"
            if memory_count > 0:
                self.tutorial_step = 1
                self.tutorial_step_time = now

        # Step 1: Memory created
        elif self.tutorial_step == 1:
            msg = "TIME FROZEN -- NOW WALK AWAY"
            if elapsed > 3.5:
                self.tutorial_step = 2
                self.tutorial_step_time = now

        # Step 2: Swipe timeline
        elif self.tutorial_step == 2:
            msg = "SWIPE PALM (✋) TO SWITCH TIMELINES"
            if elapsed > 4.5:
                self.tutorial_step = 3

        if msg:
            tut_img = Image.new("RGBA", (460, 44), (0, 0, 0, 0))
            draw = ImageDraw.Draw(tut_img)
            draw.rounded_rectangle([(0, 0), (459, 43)], radius=12,
                                   fill=(20, 16, 24, 210),
                                   outline=(180, 30, 45, 240), width=2)
            tw = draw.textlength(msg, font=_F_TUTORIAL)
            draw.text(((460 - tw) / 2, 11), msg, font=_F_TUTORIAL, fill=(245, 242, 235, 255))
            _overlay_bgra(canvas, _pil_to_cv(tut_img), (w - 460) // 2, 75)



    def draw_countdown(self, canvas: np.ndarray, seconds_remaining: float, total: float):
        """Photo countdown circle."""
        h, w = canvas.shape[:2]
        cx, cy = w // 2, h // 2
        progress = 1.0 - (seconds_remaining / total)
        num = max(1, int(np.ceil(seconds_remaining)))

        overlay = canvas.copy()
        cv2.circle(overlay, (cx, cy), 105, (12, 14, 20), -1, cv2.LINE_AA)
        cv2.circle(overlay, (cx, cy), 105, (180, 30, 45), 2, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.80, canvas, 0.20, 0, canvas)

        angle = int(progress * 360)
        cv2.ellipse(canvas, (cx, cy), (109, 109), -90, 0, angle, (0, 50, 255), 5, cv2.LINE_AA)

        num_img = Image.new("RGBA", (140, 110), (0, 0, 0, 0))
        draw = ImageDraw.Draw(num_img)
        text = str(num)
        tw = draw.textlength(text, font=_F_COUNTDOWN)
        draw.text(((140 - tw) / 2, 12), text, font=_F_COUNTDOWN, fill=(250, 245, 240, 255))
        _overlay_bgra(canvas, _pil_to_cv(num_img), cx - 70, cy - 55)

    def draw_flash(self, canvas: np.ndarray, intensity: float):
        """Studio flash."""
        flash = np.full_like(canvas, 255)
        cv2.addWeighted(flash, intensity, canvas, 1.0 - intensity, 0, canvas)

    def draw_capture_success(self, canvas: np.ndarray):
        """Banner on capture."""
        h, w = canvas.shape[:2]
        msg_img = Image.new("RGBA", (450, 46), (0, 0, 0, 0))
        draw = ImageDraw.Draw(msg_img)
        draw.rounded_rectangle([(0, 0), (449, 45)], radius=12,
                               fill=(20, 60, 35, 220),
                               outline=(60, 240, 140, 240), width=2)
        msg = "Temporal Capture Saved!  👍 Show QR  ✊ Hide"
        tw = draw.textlength(msg, font=_F_BTN)
        draw.text(((450 - tw) / 2, 12), msg, font=_F_BTN, fill=(255, 255, 255, 255))
        _overlay_bgra(canvas, _pil_to_cv(msg_img), w // 2 - 225, 75)

    def draw_qr_popup(self, canvas: np.ndarray, qr_image: Optional[np.ndarray]):
        """Rebranded TimeSensei QR Card at bottom-right."""
        if qr_image is None:
            return

        h, w = canvas.shape[:2]
        card_w = 230
        qr_size = 120
        card_h = qr_size + 70
        margin = 16

        cx = w - card_w - margin
        cy = h - card_h - margin - 42

        card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(card)
        draw.rounded_rectangle([(0, 0), (card_w - 1, card_h - 1)], radius=14,
                               fill=(14, 16, 24, 235),
                               outline=(180, 30, 45, 230), width=2)

        title = "TEMPORAL CAPTURE"
        tw = draw.textlength(title, font=_F_SMALL)
        draw.text(((card_w - tw) / 2, 8), title, font=_F_SMALL, fill=(240, 80, 95, 255))

        sub = "Scan with Phone  •  ✊ to close"
        sw = draw.textlength(sub, font=_F_SMALL)
        draw.text(((card_w - sw) / 2, 26), sub, font=_F_SMALL, fill=(180, 190, 205, 230))

        _overlay_bgra(canvas, _pil_to_cv(card), cx, cy)

        qr_resized = cv2.resize(qr_image, (qr_size, qr_size), interpolation=cv2.INTER_NEAREST)
        qx = cx + (card_w - qr_size) // 2
        qy = cy + 46
        if qy + qr_size < h and qx + qr_size < w and qx >= 0 and qy >= 0:
            canvas[qy:qy + qr_size, qx:qx + qr_size] = qr_resized
            cv2.rectangle(canvas, (qx - 1, qy - 1),
                          (qx + qr_size + 1, qy + qr_size + 1),
                          (240, 240, 240), 1, cv2.LINE_AA)

    def draw_diagnostics(self, canvas: np.ndarray, stats: Dict[str, Any]):
        """Developer/Operator Diagnostics Overlay (toggled with D key)."""
        lines = [
            f"=== TimeSensei Diagnostics ===",
            f"FPS: {stats.get('fps', 0):.1f} (Target: {settings.TARGET_FPS})",
            f"Display: {settings.CAPTURE_WIDTH}x{settings.CAPTURE_HEIGHT} | Vision: {settings.VISION_WIDTH}x{settings.VISION_HEIGHT}",
            f"Persons Detected: {stats.get('num_persons', 0)} | Hands: {stats.get('num_hands', 0)}",
            f"Frozen Clones: {stats.get('memory_count', 0)} / {settings.MAX_MEMORIES}",
            f"Active Mode: {stats.get('mode', 'PRESENT')}",
            f"Audio Enabled: {stats.get('audio_enabled', False)}",
            f"State: {stats.get('app_state', 'UNKNOWN')}",
            f"Server: http://{stats.get('lan_ip', '127.0.0.1')}:{settings.SHARING_PORT}",
        ]

        overlay = canvas.copy()
        box_w, box_h = 360, len(lines) * 20 + 20
        cv2.rectangle(overlay, (12, 65), (12 + box_w, 65 + box_h), (10, 12, 16), -1)
        cv2.addWeighted(overlay, 0.75, canvas, 0.25, 0, canvas)
        cv2.rectangle(canvas, (12, 65), (12 + box_w, 65 + box_h), (80, 90, 110), 1, cv2.LINE_AA)

        for i, line in enumerate(lines):
            color = (0, 240, 255) if i == 0 else (220, 225, 235)
            cv2.putText(canvas, line, (22, 90 + i * 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.44, color, 1, cv2.LINE_AA)

    def apply_watermark(self, photo_bgr: np.ndarray) -> np.ndarray:
        """Applies subtle TimeSensei watermark to captured photo."""
        h, w = photo_bgr.shape[:2]
        watermark = photo_bgr.copy()
        text = "TimeSensei // CONTROL YOUR TIMELINE"
        cv2.putText(watermark, text, (32, h - 28),
                    cv2.FONT_HERSHEY_DUPLEX, 0.65, (245, 240, 235), 1, cv2.LINE_AA)
        return watermark
