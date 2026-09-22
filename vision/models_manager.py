"""
Model Management & Caching
Ensures required vision models are present locally in `models/`.
"""
import os
import urllib.request
from pathlib import Path
from config import settings

MODEL_URLS = {
    "selfie_segmenter.tflite": "https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite",
    "gesture_recognizer.task": "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/latest/gesture_recognizer.task",
    "pose_landmarker_lite.task": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task",
}


def ensure_model(filename: str) -> str:
    """Returns local path to model, downloading if not already cached."""
    local_path = settings.MODELS_DIR / filename
    if local_path.exists() and local_path.stat().st_size > 1000:
        return str(local_path)

    if filename not in MODEL_URLS:
        raise ValueError(f"Unknown model filename: {filename}")

    url = MODEL_URLS[filename]
    print(f"[ModelManager] Fetching {filename} from {url}...")
    try:
        urllib.request.urlretrieve(url, str(local_path))
        print(f"[ModelManager] Successfully downloaded {filename} ({local_path.stat().st_size / 1024:.1f} KB)")
        return str(local_path)
    except Exception as e:
        print(f"[ModelManager] Warning: Could not download {filename}: {e}")
        return None
