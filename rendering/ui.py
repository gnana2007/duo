"""
Premium UI Renderer v3.1 — Interactive Memory Wall
───────────────────────────────────────────────────
Crisp PIL-rendered overlays with:
  • Capture zone indicator
  • Memory count & status
  • Environment pill
  • Review screen with QR code
  • Grab indicator
  • Gesture hints
"""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from config import settings


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


_F_TITLE = _get_font(18, bold=True)
_F_SUB = _get_font(13)
_F_LARGE = _get_font(28, bold=True)
_F_SMALL = _get_font(12)
_F_COUNTDOWN = _get_font(80, bold=True)
_F_STATUS = _get_font(15, bold=True)
_F_HINT = _get_font(13)
_F_BTN = _get_font(15, bold=True)
_F_MODAL_TITLE = _get_font(22, bold=True)
_F_MODAL_BODY = _get_font(14)


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
    patch = overlay_bgra[oy1:oy1+(y2-y1), ox1:ox1+(x2-x1)]
    alpha = patch[:, :, 3:4].astype(np.float32) / 255.0
    bgr = patch[:, :, :3].astype(np.float32)
    roi = canvas_bgr[y1:y2, x1:x2].astype(np.float32)
    blended = bgr * alpha + roi * (1.0 - alpha)
    canvas_bgr[y1:y2, x1:x2] = blended.astype(np.uint8)


def _make_pill(width: int, height: int, text: str, subtext: str,
               accent: Tuple[int, int, int], bg_alpha: int = 180) -> np.ndarray:
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([(0, 0), (width - 1, height - 1)], radius=12,
                           fill=(18, 22, 30, bg_alpha),
                           outline=(accent[0], accent[1], accent[2], 200), width=1)
    draw.ellipse([(10, height // 2 - 4), (18, height // 2 + 4)],
                 fill=(accent[0], accent[1], accent[2], 255))
    draw.text((26, 5), text, font=_F_TITLE, fill=(240, 244, 248, 255))
    if subtext:
        draw.text((26, 25), subtext, font=_F_SUB, fill=(150, 165, 185, 230))
    return _pil_to_cv(img)


class UIRenderer:
    def __init__(self):
        self._pill_cache = {}

    def draw_capture_zone(self, canvas: np.ndarray, person_in_zone: bool):
        h, w = canvas.shape[:2]
        zx = int(w * settings.CAPTURE_ZONE_X_RATIO)
        zy = int(h * settings.CAPTURE_ZONE_Y_RATIO)
        zw = int(w * settings.CAPTURE_ZONE_W_RATIO)
        zh = int(h * settings.CAPTURE_ZONE_H_RATIO)

        color = (0, 220, 120) if person_in_zone else (100, 120, 140)
        thick = 2 if person_in_zone else 1
        cl = 35  # corner length

        corners = [
            ((zx, zy), (zx + cl, zy), (zx, zy + cl)),
            ((zx + zw, zy), (zx + zw - cl, zy), (zx + zw, zy + cl)),
            ((zx, zy + zh), (zx + cl, zy + zh), (zx, zy + zh - cl)),
            ((zx + zw, zy + zh), (zx + zw - cl, zy + zh), (zx + zw, zy + zh - cl)),
        ]
        for origin, h_end, v_end in corners:
            cv2.line(canvas, origin, h_end, color, thick, cv2.LINE_AA)
            cv2.line(canvas, origin, v_end, color, thick, cv2.LINE_AA)

        # Status text
        status_img = Image.new("RGBA", (420, 30), (0, 0, 0, 0))
        draw = ImageDraw.Draw(status_img)
        if person_in_zone:
            msg = "Ready -- Peace sign to capture!"
            col = (80, 255, 160, 255)
        else:
            msg = "Stand inside the capture area"
            col = (180, 190, 200, 200)
        tw = draw.textlength(msg, font=_F_STATUS)
        draw.text(((420 - tw) / 2, 4), msg, font=_F_STATUS, fill=col)
        _overlay_bgra(canvas, _pil_to_cv(status_img), w // 2 - 210, zy + zh + 10)

    def draw_hud(self, canvas: np.ndarray, env_name: str,
                 env_accent: Tuple[int, int, int], memory_count: int,
                 fps: float, person_in_zone: bool, grabbed: bool = False):
        h, w = canvas.shape[:2]

        # Top-Left: Environment
        key_env = f"env_{env_name}"
        if key_env not in self._pill_cache:
            self._pill_cache[key_env] = _make_pill(
                340, 46,
                f"<< {env_name.upper()} >>",
                "Left hand x3 / Right hand x3 to change",
                env_accent,
            )
        _overlay_bgra(canvas, self._pill_cache[key_env], 16, 16)

        # Top-Right: Status
        key_status = f"status_{memory_count}_{int(fps)}_{grabbed}"
        if key_status not in self._pill_cache:
            grab_text = " | GRABBING" if grabbed else ""
            self._pill_cache[key_status] = _make_pill(
                260, 46,
                f"MEMORIES: {memory_count}{grab_text}",
                f"{fps:.0f} FPS",
                (100, 220, 255) if memory_count > 0 else (150, 150, 150),
            )
        _overlay_bgra(canvas, self._pill_cache[key_status], w - 276, 16)

        # Bottom hints
        hints_img = Image.new("RGBA", (720, 36), (0, 0, 0, 0))
        draw = ImageDraw.Draw(hints_img)
        draw.rounded_rectangle([(0, 0), (719, 35)], radius=10,
                               fill=(15, 18, 25, 160),
                               outline=(80, 90, 110, 180), width=1)
        hints = "Peace=Capture | 👍 Thumb=Show QR | ✊ Fist=Hide QR / Grab | Swipe x3=World"
        tw = draw.textlength(hints, font=_F_HINT)
        draw.text(((720 - tw) / 2, 8), hints, font=_F_HINT, fill=(200, 210, 220, 230))
        _overlay_bgra(canvas, _pil_to_cv(hints_img), w // 2 - 360, h - 52)

    def draw_countdown(self, canvas: np.ndarray, seconds_remaining: float, total: float):
        h, w = canvas.shape[:2]
        cx, cy = w // 2, h // 2
        progress = 1.0 - (seconds_remaining / total)
        num = max(1, int(np.ceil(seconds_remaining)))

        overlay = canvas.copy()
        cv2.circle(overlay, (cx, cy), 110, (12, 14, 20), -1, cv2.LINE_AA)
        cv2.circle(overlay, (cx, cy), 110, (220, 220, 220), 2, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.80, canvas, 0.20, 0, canvas)

        angle = int(progress * 360)
        cv2.ellipse(canvas, (cx, cy), (114, 114), -90, 0, angle,
                    (0, 240, 255), 6, cv2.LINE_AA)

        num_img = Image.new("RGBA", (140, 110), (0, 0, 0, 0))
        draw = ImageDraw.Draw(num_img)
        text = str(num)
        tw = draw.textlength(text, font=_F_COUNTDOWN)
        draw.text(((140 - tw) / 2, 5), text, font=_F_COUNTDOWN, fill=(255, 255, 255, 255))
        _overlay_bgra(canvas, _pil_to_cv(num_img), cx - 70, cy - 55)

    def draw_flash(self, canvas: np.ndarray, intensity: float):
        flash = np.full_like(canvas, 255)
        cv2.addWeighted(flash, intensity, canvas, 1.0 - intensity, 0, canvas)

    def draw_capture_success(self, canvas: np.ndarray):
        """Notification on capture — no frame numbers."""
        h, w = canvas.shape[:2]
        msg_img = Image.new("RGBA", (430, 50), (0, 0, 0, 0))
        draw = ImageDraw.Draw(msg_img)
        draw.rounded_rectangle([(0, 0), (429, 49)], radius=14,
                               fill=(20, 90, 40, 210),
                               outline=(80, 255, 120, 255), width=2)
        msg = "Memory Saved!  👍 Show QR  ✊ Hide"
        tw = draw.textlength(msg, font=_F_BTN)
        draw.text(((430 - tw) / 2, 13), msg, font=_F_BTN, fill=(255, 255, 255, 255))
        _overlay_bgra(canvas, _pil_to_cv(msg_img), w // 2 - 215, 80)

    def draw_qr_popup(self, canvas: np.ndarray, qr_image: Optional[np.ndarray]):
        """Small QR popup at bottom-right corner — summoned by 👍, dismissed by ✊."""
        if qr_image is None:
            return

        h, w = canvas.shape[:2]

        card_w = 230
        qr_size = 120
        card_h = qr_size + 72
        margin = 16

        cx = w - card_w - margin
        cy = h - card_h - margin - 42  # above the hints bar

        card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(card)
        draw.rounded_rectangle([(0, 0), (card_w - 1, card_h - 1)], radius=14,
                               fill=(14, 18, 26, 230),
                               outline=(0, 220, 255, 220), width=2)

        # Title
        title = "Scan to Save"
        tw = draw.textlength(title, font=_F_BTN)
        draw.text(((card_w - tw) / 2, 8), title, font=_F_BTN, fill=(0, 240, 255, 255))

        # Subtitle
        sub = "Show ✊ to close"
        sw = draw.textlength(sub, font=_F_SMALL)
        draw.text(((card_w - sw) / 2, 28), sub, font=_F_SMALL, fill=(170, 185, 205, 230))

        _overlay_bgra(canvas, _pil_to_cv(card), cx, cy)

        qr_resized = cv2.resize(qr_image, (qr_size, qr_size), interpolation=cv2.INTER_NEAREST)
        qx = cx + (card_w - qr_size) // 2
        qy = cy + 48
        if qy + qr_size < h and qx + qr_size < w and qx >= 0 and qy >= 0:
            canvas[qy:qy+qr_size, qx:qx+qr_size] = qr_resized
            cv2.rectangle(canvas, (qx - 1, qy - 1),
                          (qx + qr_size + 1, qy + qr_size + 1),
                          (255, 255, 255), 1, cv2.LINE_AA)


