"""
Application Configuration — Interactive Memory Wall v3.3
"""
from pathlib import Path

# --- Base Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
ENVIRONMENTS_DIR = ASSETS_DIR / "environments"
CAPTURES_DIR = BASE_DIR / "captures"
MODELS_DIR = BASE_DIR / "models"

ENVIRONMENTS_DIR.mkdir(parents=True, exist_ok=True)
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# --- Camera & Display ---
CAMERA_INDEX = 0
CAPTURE_WIDTH = 1280
CAPTURE_HEIGHT = 720
TARGET_FPS = 30
WINDOW_NAME = "Interactive Memory Wall"

# --- Vision Pipeline (staggered) ---
VISION_WIDTH = 480
VISION_HEIGHT = 270
SEG_EVERY_N = 2
HAND_EVERY_N = 3
POSE_EVERY_N = 6
POSE_OFFSET = 1

# --- Segmentation Quality (Fast, Crisp, No Ghost Trails) ---
MASK_TEMPORAL_ALPHA = 0.22        # Fast update — eliminates ghosting/lagging silhouettes
MASK_MORPH_KERNEL = 5
MASK_GUIDED_RADIUS = 6
MASK_GUIDED_EPS = 0.01
MASK_EDGE_FEATHER = 2

# --- Capture Zone (center of screen) ---
CAPTURE_ZONE_X_RATIO = 0.375     # left edge as fraction of width
CAPTURE_ZONE_W_RATIO = 0.25      # width as fraction
CAPTURE_ZONE_Y_RATIO = 0.075     # top edge
CAPTURE_ZONE_H_RATIO = 0.85      # height

# --- Gesture Thresholds ---
GESTURE_HOLD_S = 0.6
TRIPLE_SWIPE_WINDOW_S = 2.0
TRIPLE_SWIPE_COOLDOWN_S = 2.5
SWIPE_MIN_VELOCITY_X = 400

# --- Background Capture ---
BG_CAPTURE_FRAMES = 25  # average frames for clean background

# --- Countdown & Flash ---
COUNTDOWN_SECONDS = 3
FLASH_DURATION_S = 0.25

# --- Naturalism & VFX Compositing ---
COLOR_MATCH_INTENSITY = 0.20
ENABLE_CONTACT_SHADOW = True
SHADOW_OPACITY = 0.45
SHADOW_BLUR = 25
DEFRINGE_RADIUS = 2

# Naturalism features:
ENABLE_LIGHT_WRAP = True         # Background light softly wraps around edges
LIGHT_WRAP_INTENSITY = 0.22      # Subtlety of edge light wrap
LIGHT_WRAP_RADIUS = 19           # Softness of the light wrap
ENABLE_FLOOR_REFLECTION = True   # Subtle floor reflections on polished surfaces
ENABLE_PORTRAIT_DOF = True       # Subtle photographic lens blur on backgrounds
ENABLE_CINEMATIC_VIGNETTE = True # Subtle corner vignette for unified look

# --- Sharing Server ---
SHARING_PORT = 8080
SERVER_HOST = "0.0.0.0"

# --- Environment Transition ---
ENV_TRANSITION_DURATION = 0.45  # seconds for slide animation
