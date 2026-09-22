"""
TimeSensei Configuration & Settings
───────────────────────────────────
Centralized settings for TimeSensei: CONTROL YOUR TIMELINE.
All timing thresholds, collection caps, rendering flags, and audio properties.
"""
from pathlib import Path

# ── Application Branding ──
APP_NAME = "TimeSensei"
APP_TAGLINE = "CONTROL YOUR TIMELINE"
WINDOW_NAME = "TimeSensei — CONTROL YOUR TIMELINE"

# ── Base Paths ──
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
ENVIRONMENTS_DIR = ASSETS_DIR / "environments"
CAPTURES_DIR = BASE_DIR / "captures"
MODELS_DIR = BASE_DIR / "models"

ENVIRONMENTS_DIR.mkdir(parents=True, exist_ok=True)
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# ── Camera & Display ──
CAMERA_INDEX = 0
CAPTURE_WIDTH = 1280
CAPTURE_HEIGHT = 720
TARGET_FPS = 30
CAMERA_RETRY_COUNT = 5
CAMERA_RETRY_DELAY_S = 0.8

# ── Vision Pipeline (Staggered for 30+ FPS) ──
VISION_WIDTH = 480
VISION_HEIGHT = 270
SEG_EVERY_N = 1                   # Run segmentation every frame for zero edge lag
HAND_EVERY_N = 2
POSE_EVERY_N = 5
POSE_OFFSET = 1

# ── Segmentation Quality ──
MASK_TEMPORAL_ALPHA = 0.04        # Ultra-responsive tracking — eliminates motion ghosting
MASK_MORPH_KERNEL = 3
MASK_EDGE_FEATHER = 2
MASK_CUTOFF_LOW = 0.45            # Clean background rejection (drops walls, boxes, furniture)
MASK_CUTOFF_HIGH = 0.70           # Solid foreground body opacity

# ── Capture Zone (Center of Screen) ──
CAPTURE_ZONE_X_RATIO = 0.375
CAPTURE_ZONE_W_RATIO = 0.25
CAPTURE_ZONE_Y_RATIO = 0.075
CAPTURE_ZONE_H_RATIO = 0.85

# ── State Machine States ──
STATE_BOOT = "BOOT"
STATE_ATTRACT = "ATTRACT"
STATE_ENTERING = "ENTERING"
STATE_LIVE = "LIVE"
STATE_COUNTDOWN = "COUNTDOWN"
STATE_FLASH = "FLASH"
STATE_SHARE = "SHARE"
STATE_RESETTING = "RESETTING"
STATE_ERROR_RECOVERY = "ERROR_RECOVERY"

# ── Startup & Attract Experience ──
INTRO_DURATION_S = 2.0
INTRO_SCAN_DURATION_S = 0.70
START_BUTTON_HOVER_S = 1.1        # Dwell time with open palm to trigger START
IDLE_TIMEOUT_S = 16.0             # Inactivity timer: return to ATTRACT if no person seen

# ── Snappy Gesture Recognition & Action Latching ──
PEACE_PHOTO_HOLD_S = 0.20         # Quick peace sign (✌️) triggers photo capture countdown
PEACE_PHOTO_COOLDOWN_S = 3.5      # Cooldown before peace sign can trigger next capture
THUMB_HOLD_S = 0.18               # Open thumb (👍) reveals QR code card at bottom-right
FIST_HOLD_S = 0.12                # Closed fist (✊) dismisses QR code card
PALM_FREEZE_HOLD_S = 0.35         # Open palm (✋) creates grounded temporal clone
PALM_FREEZE_COOLDOWN_S = 1.4      # Cooldown before next clone can be created
PALM_CONFIDENCE = 0.50
GESTURE_GRACE_PERIOD_S = 0.22     # Hysteresis buffer to tolerate brief tracking flickers
GESTURE_HOLD_S = 0.40

# Compatibility aliases
VICTORY_FREEZE_HOLD_S = PEACE_PHOTO_HOLD_S
VICTORY_FREEZE_COOLDOWN_S = PEACE_PHOTO_COOLDOWN_S
PHOTO_CAPTURE_HOLD_S = PEACE_PHOTO_HOLD_S

# ── Single-Palm Swipe Timeline Navigation ──
SWIPE_COOLDOWN_S = 0.45           # Fast background switching on palm swipe
SWIPE_MIN_VELOCITY_X = 280        # Minimum horizontal velocity for swipe
ENV_TRANSITION_DURATION = 0.28    # Smooth slide duration across environments

# ── Clean Background Capture ──
BG_CAPTURE_FRAMES = 20

# ── Photo Capture, Countdown & Flash ──
COUNTDOWN_SECONDS = 3
FLASH_DURATION_S = 0.25

# ── Naturalism & VFX Compositing ──
COLOR_MATCH_INTENSITY = 0.20
ENABLE_CONTACT_SHADOW = True
SHADOW_OPACITY = 0.45
SHADOW_BLUR = 25
DEFRINGE_RADIUS = 2
ENABLE_LIGHT_WRAP = True
LIGHT_WRAP_INTENSITY = 0.22
LIGHT_WRAP_RADIUS = 19
ENABLE_FLOOR_REFLECTION = True
ENABLE_PORTRAIT_DOF = True
ENABLE_CINEMATIC_VIGNETTE = True

# ── Temporal Echo Mode ──
AVAILABLE_MODES = ["PRESENT", "ECHO", "PARADOX", "RIFT", "ANOMALY"]
MIRROR_DELAY_FRAMES = 4
ECHO_DELAYS_MS = [0, 180, 360, 540, 720]
MAX_ECHOES = 4

# ── Real Rewind Buffer ──
REWIND_BUFFER_SECONDS = 3.0       # Duration of rewind motion ring buffer
REWIND_FPS = 12                   # Sample rate for rewind buffer
REWIND_PLAYBACK_SPEED = 1.0       # Replay speed factor

# ── Physical Combat & Recoil Physics ──
COMBAT_STRIKE_FORCE = 1.0          # Base multiplier for physical combat strikes
COMBAT_SPRING_RESTITUTION = 0.85   # Damping factor for elastic bounce recovery

# ── Expo Reliability Limits ──
MAX_MEMORIES = 4                  # Hard ceiling on frozen clones in scene
MAX_PARTICLES = 50                # Particle cap to protect frame rates
MAX_CAPTURES_STORED = 100         # Maximum local captures retained on disk
PHOTO_RETENTION_HOURS = 4         # Prune older captures during long expo runs

# ── Audio Synthesizer ──
AUDIO_ENABLED = True
AUDIO_VOLUME = 0.55

# ── Sharing Server ──
SHARING_PORT = 8080
SERVER_HOST = "0.0.0.0"

# ── Diagnostics & Development ──
SHOW_DIAGNOSTICS_DEFAULT = False
