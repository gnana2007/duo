// TimeSensei Gesture Arbitration & Manager
// Matches interaction/gestures.py exactly.

use std::collections::HashMap;
use std::time::Instant;
use crate::config;
use crate::vision::hands::HandData;

pub fn is_fist(hand: &HandData) -> bool {
    hand.is_fist
        || (hand.gesture == "Closed_Fist" && hand.gesture_confidence >= 0.40)
}

pub fn is_thumb_up(hand: &HandData) -> bool {
    if is_fist(hand) {
        return false;
    }
    hand.is_thumb_open
        || (hand.gesture == "Thumb_Up" && hand.gesture_confidence >= 0.45)
}

pub fn is_peace_sign(hand: &HandData) -> bool {
    if is_fist(hand) {
        return false;
    }
    hand.is_victory
        || (hand.gesture == "Victory" && hand.gesture_confidence >= 0.40)
}

pub struct GestureManager {
    hold: HashMap<String, Instant>,
    last_seen: HashMap<String, Instant>,
    cooldown: HashMap<String, Instant>,
    pub last_fist_time: Instant,
    pub last_freeze_time: Instant,
    pub grace_period: f32,
}

impl GestureManager {
    pub fn new() -> Self {
        let long_ago = Instant::now() - std::time::Duration::from_secs(60);
        Self {
            hold: HashMap::new(),
            last_seen: HashMap::new(),
            cooldown: HashMap::new(),
            last_fist_time: long_ago,
            last_freeze_time: long_ago,
            grace_period: config::GESTURE_GRACE_PERIOD_S,
        }
    }

    pub fn check_hold_progress(
        &mut self,
        key: &str,
        active: bool,
        duration: f32,
        cooldown: f32,
    ) -> (bool, f32) {
        let now = Instant::now();

        // Check if key is still in cooldown
        if let Some(&last_trig) = self.cooldown.get(key) {
            if now.duration_since(last_trig).as_secs_f32() < cooldown {
                self.hold.remove(key);
                return (false, 0.0);
            }
        }

        if active {
            self.last_seen.insert(key.to_string(), now);
            if !self.hold.contains_key(key) {
                self.hold.insert(key.to_string(), now);
                return (false, 0.0);
            }

            let start = self.hold[key];
            let elapsed = now.duration_since(start).as_secs_f32();
            let progress = (elapsed / duration.max(0.01)).min(1.0);

            if elapsed >= duration {
                self.cooldown.insert(key.to_string(), now);
                self.hold.remove(key);
                self.last_seen.remove(key);
                return (true, 1.0);
            }
            (false, progress)
        } else {
            // Tolerant hysteresis: don't reset immediately if tracking blipped for < grace_period
            let last_active = self.last_seen.get(key).copied();
            if let Some(la) = last_active {
                if now.duration_since(la).as_secs_f32() > self.grace_period {
                    self.hold.remove(key);
                    self.last_seen.remove(key);
                } else if let Some(&start) = self.hold.get(key) {
                    let elapsed = now.duration_since(start).as_secs_f32();
                    let progress = (elapsed / duration.max(0.01)).min(1.0);
                    return (false, progress);
                }
            } else {
                self.hold.remove(key);
            }
            (false, 0.0)
        }
    }

    // 1. ✌️ Peace Sign: Photo Capture Trigger (Latched)
    pub fn check_peace_capture(&mut self, hands: &[HandData]) -> bool {
        let has_peace = hands.iter().any(is_peace_sign);
        let duration = config::PEACE_PHOTO_HOLD_S;
        let cooldown = config::PEACE_PHOTO_COOLDOWN_S;
        let (triggered, _) = self.check_hold_progress("peace_photo", has_peace, duration, cooldown);
        triggered
    }

    // 2. 👍 Open Thumb: Reveal QR Popup at Bottom-Right
    pub fn check_thumb_trigger(&mut self, hands: &[HandData]) -> bool {
        let now = Instant::now();
        // Cooldown guard: cannot open QR within 0.8s of seeing a fist
        if now.duration_since(self.last_fist_time).as_secs_f32() < 0.8 {
            self.hold.remove("thumb_qr");
            return false;
        }

        let has_thumb = hands.iter().any(is_thumb_up);
        let duration = config::THUMB_HOLD_S;
        let (triggered, _) = self.check_hold_progress("thumb_qr", has_thumb, duration, 1.0);
        triggered
    }

    // 3. ✊ Closed Fist: Close QR Popup
    pub fn check_fist(&mut self, hands: &[HandData]) -> bool {
        let has_fist = hands.iter().any(is_fist);
        if has_fist {
            self.last_fist_time = Instant::now();
            self.hold.remove("thumb_qr");
        }
        has_fist
    }

    pub fn check_fist_close_qr(&mut self, hands: &[HandData]) -> bool {
        let has_fist = hands.iter().any(is_fist);
        let duration = config::FIST_HOLD_S;
        let (triggered, _) = self.check_hold_progress("fist_close", has_fist, duration, 0.6);
        if triggered || has_fist {
            self.last_fist_time = Instant::now();
            self.hold.remove("thumb_qr");
            return true;
        }
        false
    }

    // 4. ✋ Open Palm: Freeze Time
    pub fn check_open_palm_freeze(
        &mut self,
        hands: &[HandData],
        qr_active: bool,
    ) -> (bool, f32, Option<(i32, i32)>) {
        if qr_active || hands.iter().any(is_fist) {
            self.hold.remove("palm_freeze");
            return (false, 0.0, None);
        }

        let palm_hands: Vec<&HandData> = hands
            .iter()
            .filter(|h| h.is_open_palm || (h.gesture == "Open_Palm" && h.gesture_confidence > 0.40))
            .collect();
        let has_palm = !palm_hands.is_empty();
        let palm_pos = palm_hands.first().map(|h| h.palm_center);

        let duration = config::PALM_FREEZE_HOLD_S;
        let cooldown = config::PALM_FREEZE_COOLDOWN_S;
        let (triggered, progress) = self.check_hold_progress("palm_freeze", has_palm, duration, cooldown);
        if triggered {
            self.last_freeze_time = Instant::now();
        }
        (triggered, progress, palm_pos)
    }

    // 5. 👈👉 Pointing Index Finger: Environment Navigation (Left / Right)
    pub fn check_pointing_swipe(&mut self, hands: &[HandData]) -> (i32, f32, i32) {
        let mut active_dir = 0;
        for h in hands {
            if is_fist(h) || is_peace_sign(h) || h.is_open_palm {
                continue;
            }
            if h.pointing_direction == -1 || h.pointing_direction == 1 {
                active_dir = h.pointing_direction;
                break;
            }
        }

        let duration = config::POINTING_HOLD_S;
        let cooldown = config::POINTING_COOLDOWN_S;

        if active_dir == -1 {
            self.hold.remove("point_right");
            let (trig, prog) = self.check_hold_progress("point_left", true, duration, cooldown);
            let dir_trig = if trig { -1 } else { 0 };
            (dir_trig, prog, -1)
        } else if active_dir == 1 {
            self.hold.remove("point_left");
            let (trig, prog) = self.check_hold_progress("point_right", true, duration, cooldown);
            let dir_trig = if trig { 1 } else { 0 };
            (dir_trig, prog, 1)
        } else {
            self.check_hold_progress("point_left", false, duration, cooldown);
            self.check_hold_progress("point_right", false, duration, cooldown);
            (0, 0.0, 0)
        }
    }
}
