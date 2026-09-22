// TimeSensei Configuration & Settings
// Centralized settings matching config/settings.py exactly.

use std::path::PathBuf;

pub const APP_NAME: &str = "TimeSensei";
pub const APP_TAGLINE: &str = "CONTROL YOUR TIMELINE";
pub const WINDOW_NAME: &str = "TimeSensei — CONTROL YOUR TIMELINE";

pub const CAMERA_INDEX: usize = 0;
pub const CAPTURE_WIDTH: u32 = 1280;
pub const CAPTURE_HEIGHT: u32 = 720;
pub const TARGET_FPS: u32 = 30;
pub const CAMERA_RETRY_COUNT: u32 = 5;
pub const CAMERA_RETRY_DELAY_S: f32 = 0.8;

// Vision Pipeline (Staggered for 30+ FPS)
pub const VISION_WIDTH: u32 = 480;
pub const VISION_HEIGHT: u32 = 270;
pub const SEG_EVERY_N: u32 = 1;
pub const HAND_EVERY_N: u32 = 1;
pub const POSE_EVERY_N: u32 = 5;
pub const POSE_OFFSET: u32 = 1;

// Segmentation Quality
pub const MASK_TEMPORAL_ALPHA: f32 = 0.04;
pub const MASK_MORPH_KERNEL: u32 = 3;
pub const MASK_EDGE_FEATHER: u32 = 2;
pub const MASK_CUTOFF_LOW: f32 = 0.22;
pub const MASK_CUTOFF_HIGH: f32 = 0.60;

// Capture Zone (Center of Screen)
pub const CAPTURE_ZONE_X_RATIO: f32 = 0.375;
pub const CAPTURE_ZONE_W_RATIO: f32 = 0.25;
pub const CAPTURE_ZONE_Y_RATIO: f32 = 0.075;
pub const CAPTURE_ZONE_H_RATIO: f32 = 0.85;

// Startup & Attract Experience
pub const INTRO_DURATION_S: f32 = 2.0;
pub const INTRO_SCAN_DURATION_S: f32 = 0.70;
pub const START_BUTTON_HOVER_S: f32 = 1.1;
pub const IDLE_TIMEOUT_S: f32 = 16.0;

// Gesture Recognition & Latching
pub const PEACE_PHOTO_HOLD_S: f32 = 0.20;
pub const PEACE_PHOTO_COOLDOWN_S: f32 = 3.5;
pub const THUMB_HOLD_S: f32 = 0.18;
pub const FIST_HOLD_S: f32 = 0.12;
pub const PALM_FREEZE_HOLD_S: f32 = 0.35;
pub const PALM_FREEZE_COOLDOWN_S: f32 = 1.4;
pub const PALM_CONFIDENCE: f32 = 0.50;
pub const GESTURE_GRACE_PERIOD_S: f32 = 0.22;
pub const GESTURE_HOLD_S: f32 = 0.40;

// Pointing Timeline Navigation
pub const POINTING_HOLD_S: f32 = 0.30;
pub const POINTING_COOLDOWN_S: f32 = 0.75;
pub const SWIPE_COOLDOWN_S: f32 = 0.45;
pub const SWIPE_MIN_VELOCITY_X: f32 = 280.0;
pub const ENV_TRANSITION_DURATION: f32 = 0.28;
pub const REWIND_BUFFER_SECONDS: f32 = 3.0;

// Clean Background Capture
pub const BG_CAPTURE_FRAMES: usize = 20;

// Photo Capture, Countdown & Flash
pub const COUNTDOWN_SECONDS: u32 = 3;
pub const FLASH_DURATION_S: f32 = 0.25;

// Naturalism & VFX Compositing
pub const COLOR_MATCH_INTENSITY: f32 = 0.20;
pub const ENABLE_CONTACT_SHADOW: bool = true;
pub const SHADOW_OPACITY: f32 = 0.45;
pub const SHADOW_BLUR: u32 = 25;
pub const DEFRINGE_RADIUS: u32 = 2;
pub const ENABLE_LIGHT_WRAP: bool = true;
pub const LIGHT_WRAP_INTENSITY: f32 = 0.22;
pub const LIGHT_WRAP_RADIUS: u32 = 19;

// Expo Reliability Limits
pub const MAX_MEMORIES: usize = 4;
pub const MAX_PARTICLES: usize = 50;
pub const MAX_CAPTURES_STORED: usize = 100;
pub const PHOTO_RETENTION_HOURS: u64 = 4;

// Audio
pub const AUDIO_ENABLED: bool = true;
pub const AUDIO_VOLUME: f32 = 0.55;

// Mobile Sharing Server
pub const DEFAULT_SHARING_PORT: u16 = 8080;
pub const SERVER_HOST: &str = "0.0.0.0";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AppState {
    Boot,
    Attract,
    Entering,
    Live,
    Countdown,
    Flash,
    Share,
    Resetting,
    ErrorRecovery,
}

pub fn base_dir() -> PathBuf {
    PathBuf::from(r"d:\duo")
}

pub fn assets_dir() -> PathBuf {
    base_dir().join("assets")
}

pub fn environments_dir() -> PathBuf {
    assets_dir().join("environments")
}

pub fn captures_dir() -> PathBuf {
    base_dir().join("captures")
}

pub fn models_dir() -> PathBuf {
    base_dir().join("models")
}
