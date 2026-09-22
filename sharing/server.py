"""
Mobile Sharing Web Server
Lightweight Flask daemon serving mobile downloads and WhatsApp sharing.
"""
import os
import threading
import logging
from pathlib import Path
from flask import Flask, render_template, send_from_directory, abort
from config import settings
from capture.qr import get_local_ip

# Suppress standard Flask request logs to keep terminal clean
log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

template_dir = Path(__file__).resolve().parent / "templates"
app = Flask(__name__, template_folder=str(template_dir))


@app.route("/health")
def health():
    return {"status": "ok"}


@app.route("/photo/<photo_id>")
def view_photo(photo_id):
    file_path = settings.CAPTURES_DIR / f"{photo_id}.jpg"
    if not file_path.exists():
        abort(404)
    return render_template("index.html", photo_id=photo_id)


@app.route("/image/<photo_id>")
def get_image(photo_id):
    filename = f"{photo_id}.jpg"
    return send_from_directory(str(settings.CAPTURES_DIR), filename, mimetype="image/jpeg")


@app.route("/download/<photo_id>")
def download_image(photo_id):
    filename = f"{photo_id}.jpg"
    return send_from_directory(str(settings.CAPTURES_DIR), filename, as_attachment=True, download_name=f"{photo_id}.jpg")


def start_sharing_server(host=settings.SERVER_HOST, port=settings.SHARING_PORT):
    """Starts the Flask server in a background daemon thread."""
    def run():
        local_ip = get_local_ip()
        print(f"[SharingServer] Mobile access server live at http://{local_ip}:{port}")
        app.run(host=host, port=port, threaded=True, use_reloader=False)

    server_thread = threading.Thread(target=run, daemon=True)
    server_thread.start()
    return server_thread
