"""
QR Code Generator & Local IP Resolver
Generates clean QR codes pointing to the mobile sharing web server.
"""
import socket
from pathlib import Path
from typing import Optional
import numpy as np
import cv2
from config import settings


def get_local_ip() -> str:
    """Attempts to discover the machine's local Wi-Fi / Ethernet LAN IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't need to be reachable, used to determine outbound network interface
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


class QRCodeGenerator:
    def __init__(self, port=settings.SHARING_PORT):
        self.port = port
        self.local_ip = get_local_ip()

    def get_share_url(self, photo_id: str) -> str:
        return f"http://{self.local_ip}:{self.port}/photo/{photo_id}"

    def generate_qr_image(self, photo_id: str, size: int = 240) -> np.ndarray:
        """
        Generates a crisp QR code BGR image for the given photo ID.
        Uses `qrcode` library or OpenCV fallback.
        """
        url = self.get_share_url(photo_id)

        try:
            import qrcode
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=8,
                border=2,
            )
            qr.add_data(url)
            qr.make(fit=True)
            pil_img = qr.make_image(fill_color="black", back_color="white")
            qr_np = np.array(pil_img.convert("RGB"))
            qr_bgr = cv2.cvtColor(qr_np, cv2.COLOR_RGB2BGR)
            return cv2.resize(qr_bgr, (size, size), interpolation=cv2.INTER_NEAREST)
        except Exception:
            # OpenCV fallback using cv2.QRCodeEncoder
            try:
                encoder = cv2.QRCodeEncoder_create()
                qr_code = encoder.encode(url)
                # Scale up to requested size
                qr_norm = (qr_code * 255).astype(np.uint8)
                qr_bgr = cv2.cvtColor(qr_norm, cv2.COLOR_GRAY2BGR)
                return cv2.resize(qr_bgr, (size, size), interpolation=cv2.INTER_NEAREST)
            except Exception:
                # Basic visual placeholder if both fail
                dummy = np.full((size, size, 3), 255, dtype=np.uint8)
                cv2.putText(dummy, "QR CODE", (size // 4, size // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
                return dummy
