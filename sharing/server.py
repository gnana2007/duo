"""
TimeSensei Mobile Sharing Web Server
────────────────────────────────────
Lightweight background Flask daemon serving mobile downloads and WhatsApp sharing.
Includes input sanitization, safe fixed-directory path handling, and periodic storage pruning.
"""
import os
import re
import time
import threading
import logging
from pathlib import Path
from flask import Flask, render_template, send_from_directory, abort
from config import settings
from capture.qr import get_local_ip

# Suppress standard Flask request logs
log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

template_dir = Path(__file__).resolve().parent / "templates"
app = Flask(__name__, template_folder=str(template_dir))

# Sanitize photo IDs (alphanumeric, underscore, hyphen only)
_PHOTO_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def _is_valid_photo_id(photo_id: str) -> bool:
    return bool(_PHOTO_ID_PATTERN.match(photo_id))


def _prune_old_captures():
    """Periodic daemon pruning captures older than PHOTO_RETENTION_HOURS or exceeding MAX_CAPTURES_STORED."""
    while True:
        try:
            time.sleep(1800)  # Check every 30 minutes
            captures = sorted(settings.CAPTURES_DIR.glob("*.jpg"), key=os.path.getmtime)
            now = time.time()
            max_age_s = settings.PHOTO_RETENTION_HOURS * 3600

            # Prune by age
            for f in captures:
                if now - f.stat().st_mtime > max_age_s:
                    try:
                        f.unlink()
                    except Exception:
                        pass

            # Prune by count ceiling
            captures = sorted(settings.CAPTURES_DIR.glob("*.jpg"), key=os.path.getmtime)
            if len(captures) > settings.MAX_CAPTURES_STORED:
                to_remove = len(captures) - settings.MAX_CAPTURES_STORED
                for f in captures[:to_remove]:
                    try:
                        f.unlink()
                    except Exception:
                        pass
        except Exception:
            pass


@app.route("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}


@app.route("/photo/<photo_id>")
def view_photo(photo_id):
    if not _is_valid_photo_id(photo_id):
        abort(400)
    file_path = settings.CAPTURES_DIR / f"{photo_id}.jpg"
    if not file_path.exists():
        abort(404)
    return render_template("index.html", photo_id=photo_id)


@app.route("/image/<photo_id>")
def get_image(photo_id):
    if not _is_valid_photo_id(photo_id):
        abort(400)
    filename = f"{photo_id}.jpg"
    return send_from_directory(str(settings.CAPTURES_DIR), filename, mimetype="image/jpeg")


@app.route("/download/<photo_id>")
def download_image(photo_id):
    if not _is_valid_photo_id(photo_id):
        abort(400)
    filename = f"{photo_id}.jpg"
    return send_from_directory(
        str(settings.CAPTURES_DIR),
        filename,
        as_attachment=True,
        download_name=f"timesensei_{photo_id}.jpg"
    )


def _find_available_port(start_port: int, host: str = "0.0.0.0") -> int:
    import socket
    port = start_port
    while port < start_port + 20:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                port += 1
    return start_port


def start_sharing_server(host=settings.SERVER_HOST, port=settings.SHARING_PORT):
    """Starts the Flask sharing daemon and background cleanup worker."""
    chosen_port = _find_available_port(port, host)
    settings.SHARING_PORT = chosen_port

    def run():
        local_ip = get_local_ip()
        print(f"[SharingServer] TimeSensei mobile sharing live at http://{local_ip}:{chosen_port}")
        try:
            import logging
            log = logging.getLogger('werkzeug')
            log.setLevel(logging.ERROR)
            app.run(host=host, port=chosen_port, threaded=True, use_reloader=False)
        except Exception as e:
            print(f"[SharingServer] Server notice: {e}")

    server_thread = threading.Thread(target=run, daemon=True)
    server_thread.start()

    prune_thread = threading.Thread(target=_prune_old_captures, daemon=True)
    prune_thread.start()

    return server_thread
