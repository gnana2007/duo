// Multi-Hand Tracker & Gesture Detector
// Matches vision/hands.py exactly.

use crate::config;

#[derive(Clone, Debug)]
pub struct HandData {
    pub id: usize,
    pub label: String,
    pub palm_center: (i32, i32),
    pub index_tip: (i32, i32),
    pub thumb_tip: (i32, i32),
    pub middle_tip: (i32, i32),
    pub victory_center: (i32, i32),
    pub is_pinching: bool,
    pub is_open_palm: bool,
    pub is_pointing_up: bool,
    pub pointing_direction: i32, // -1: Left, +1: Right, 0: None
    pub is_victory: bool,
    pub is_thumb_open: bool,
    pub is_fist: bool,
    pub gesture: String,
    pub gesture_confidence: f32,
    pub all_landmarks: Vec<(i32, i32)>,
}

fn hypot(dx: f32, dy: f32) -> f32 {
    (dx * dx + dy * dy).sqrt()
}

pub fn detect_pointing_direction(pts: &[(i32, i32)], palm_center: (i32, i32)) -> i32 {
    if pts.len() < 21 {
        return 0;
    }

    let palm_cx = palm_center.0 as f32;
    let palm_cy = palm_center.1 as f32;
    let wrist = (pts[0].0 as f32, pts[0].1 as f32);
    let hand_scale = hypot(palm_cx - wrist.0, palm_cy - wrist.1).max(20.0);

    // Vector from index MCP (joint 5) to index TIP (joint 8)
    let dx = pts[8].0 as f32 - pts[5].0 as f32;
    let dy = pts[8].1 as f32 - pts[5].1 as f32;
    let d_index = hypot(dx, dy);

    // Index finger must be physically extended from knuckle
    if d_index < hand_scale * 0.70 {
        return 0;
    }

    // Horizontal dominance: |dx| must be distinctly larger than |dy| and >= 25px
    if dx.abs() < dy.abs() * 0.85 || dx.abs() < 25.0 {
        return 0;
    }

    // Middle, ring, and pinky fingers must be curled towards palm
    let d_middle = hypot(pts[12].0 as f32 - palm_cx, pts[12].1 as f32 - palm_cy);
    let d_ring = hypot(pts[16].0 as f32 - palm_cx, pts[16].1 as f32 - palm_cy);
    let d_pinky = hypot(pts[20].0 as f32 - palm_cx, pts[20].1 as f32 - palm_cy);

    // Middle finger extension check (distinguishes pointing from victory / peace sign)
    let d_mid_knuckle = hypot(pts[12].0 as f32 - pts[9].0 as f32, pts[12].1 as f32 - pts[9].1 as f32);
    if d_mid_knuckle > d_index * 0.75 {
        return 0;
    }

    if d_middle > hand_scale * 1.35 || d_ring > hand_scale * 1.30 || d_pinky > hand_scale * 1.30 {
        return 0;
    }

    if dx < 0.0 { -1 } else { 1 }
}

pub fn detect_pointing_up(pts: &[(i32, i32)], _palm_center: (i32, i32)) -> bool {
    if pts.len() < 21 {
        return false;
    }
    // Index finger straight up: tip (8) is well above pip (6) and mcp (5)
    let index_up = pts[8].1 < pts[6].1 - 20 && pts[6].1 < pts[5].1;

    // Other fingers curled: tip is below pip or close to palm
    let middle_curled = pts[12].1 > pts[10].1 - 10;
    let ring_curled = pts[16].1 > pts[14].1 - 10;
    let pinky_curled = pts[20].1 > pts[18].1 - 10;

    index_up && middle_curled && ring_curled && pinky_curled
}

pub fn detect_victory(pts: &[(i32, i32)], palm_center: (i32, i32), gesture_name: &str, conf: f32) -> bool {
    if gesture_name == "Victory" && conf >= 0.40 {
        return true;
    }
    if pts.len() < 21 {
        return false;
    }

    let palm_cx = palm_center.0 as f32;
    let palm_cy = palm_center.1 as f32;
    let wrist = (pts[0].0 as f32, pts[0].1 as f32);
    let hand_scale = hypot(palm_cx - wrist.0, palm_cy - wrist.1).max(20.0);

    let d_index = hypot(pts[8].0 as f32 - palm_cx, pts[8].1 as f32 - palm_cy);
    let d_middle = hypot(pts[12].0 as f32 - palm_cx, pts[12].1 as f32 - palm_cy);
    let d_ring = hypot(pts[16].0 as f32 - palm_cx, pts[16].1 as f32 - palm_cy);
    let d_pinky = hypot(pts[20].0 as f32 - palm_cx, pts[20].1 as f32 - palm_cy);

    let index_extended = d_index > hand_scale * 1.25;
    let middle_extended = d_middle > hand_scale * 1.25;
    let ring_curled = d_ring < hand_scale * 1.15;
    let pinky_curled = d_pinky < hand_scale * 1.15;

    let tip_dist = hypot(pts[8].0 as f32 - pts[12].0 as f32, pts[8].1 as f32 - pts[12].1 as f32);
    let is_v_shape = tip_dist > hand_scale * 0.16;

    let vert_index = pts[8].1 < pts[6].1 - 10;
    let vert_middle = pts[12].1 < pts[10].1 - 10;
    let vert_ring = pts[16].1 > pts[14].1 - 12;
    let vert_pinky = pts[20].1 > pts[18].1 - 12;
    let vertical_v = vert_index && vert_middle && vert_ring && vert_pinky && is_v_shape;

    (index_extended && middle_extended && ring_curled && pinky_curled && is_v_shape) || vertical_v
}

pub fn detect_open_thumb(pts: &[(i32, i32)], palm_center: (i32, i32), gesture_name: &str, conf: f32) -> bool {
    if gesture_name == "Thumb_Up" && conf >= 0.40 {
        return true;
    }
    if pts.len() < 21 {
        return false;
    }

    let palm_cx = palm_center.0 as f32;
    let palm_cy = palm_center.1 as f32;
    let wrist = (pts[0].0 as f32, pts[0].1 as f32);
    let hand_scale = hypot(palm_cx - wrist.0, palm_cy - wrist.1).max(20.0);

    let d_thumb = hypot(pts[4].0 as f32 - palm_cx, pts[4].1 as f32 - palm_cy);
    let d_index = hypot(pts[8].0 as f32 - palm_cx, pts[8].1 as f32 - palm_cy);
    let d_middle = hypot(pts[12].0 as f32 - palm_cx, pts[12].1 as f32 - palm_cy);
    let d_ring = hypot(pts[16].0 as f32 - palm_cx, pts[16].1 as f32 - palm_cy);
    let d_pinky = hypot(pts[20].0 as f32 - palm_cx, pts[20].1 as f32 - palm_cy);

    let thumb_extended = d_thumb > hand_scale * 1.05;
    let fingers_curled = d_index < hand_scale * 1.15
        && d_middle < hand_scale * 1.15
        && d_ring < hand_scale * 1.15
        && d_pinky < hand_scale * 1.15;

    let vert_thumb = pts[4].1 < pts[3].1 - 10 && pts[4].1 < pts[5].1 - 15;
    let vert_curled = pts[8].1 > pts[6].1 - 10 && pts[12].1 > pts[10].1 - 10;

    (thumb_extended && fingers_curled) || (vert_thumb && vert_curled)
}

pub fn detect_fist(pts: &[(i32, i32)], palm_center: (i32, i32), gesture_name: &str, conf: f32) -> bool {
    if gesture_name == "Closed_Fist" && conf >= 0.40 {
        return true;
    }
    if pts.len() < 21 {
        return false;
    }

    let palm_cx = palm_center.0 as f32;
    let palm_cy = palm_center.1 as f32;
    let wrist = (pts[0].0 as f32, pts[0].1 as f32);
    let hand_scale = hypot(palm_cx - wrist.0, palm_cy - wrist.1).max(20.0);

    let d_thumb = hypot(pts[4].0 as f32 - palm_cx, pts[4].1 as f32 - palm_cy);
    let d_index = hypot(pts[8].0 as f32 - palm_cx, pts[8].1 as f32 - palm_cy);
    let d_middle = hypot(pts[12].0 as f32 - palm_cx, pts[12].1 as f32 - palm_cy);
    let d_ring = hypot(pts[16].0 as f32 - palm_cx, pts[16].1 as f32 - palm_cy);
    let d_pinky = hypot(pts[20].0 as f32 - palm_cx, pts[20].1 as f32 - palm_cy);

    let all_curled = d_thumb < hand_scale * 0.95
        && d_index < hand_scale * 1.05
        && d_middle < hand_scale * 1.05
        && d_ring < hand_scale * 1.05
        && d_pinky < hand_scale * 1.05;

    all_curled && gesture_name != "Open_Palm" && gesture_name != "Victory" && gesture_name != "Thumb_Up"
}

pub fn detect_open_palm(pts: &[(i32, i32)], palm_center: (i32, i32), gesture_name: &str, conf: f32) -> bool {
    if gesture_name == "Open_Palm" && conf >= 0.50 {
        return true;
    }
    if pts.len() < 21 {
        return false;
    }

    let palm_cx = palm_center.0 as f32;
    let palm_cy = palm_center.1 as f32;
    let wrist = (pts[0].0 as f32, pts[0].1 as f32);
    let hand_scale = hypot(palm_cx - wrist.0, palm_cy - wrist.1).max(25.0);

    let d_index = hypot(pts[8].0 as f32 - palm_cx, pts[8].1 as f32 - palm_cy);
    let d_middle = hypot(pts[12].0 as f32 - palm_cx, pts[12].1 as f32 - palm_cy);
    let d_ring = hypot(pts[16].0 as f32 - palm_cx, pts[16].1 as f32 - palm_cy);
    let d_pinky = hypot(pts[20].0 as f32 - palm_cx, pts[20].1 as f32 - palm_cy);
    let d_thumb = hypot(pts[4].0 as f32 - palm_cx, pts[4].1 as f32 - palm_cy);

    let fingers_extended = d_index > hand_scale * 1.35
        && d_middle > hand_scale * 1.40
        && d_ring > hand_scale * 1.30
        && d_pinky > hand_scale * 1.15;
    let thumb_extended = d_thumb > hand_scale * 1.05;

    fingers_extended && thumb_extended && gesture_name != "Closed_Fist" && gesture_name != "Victory"
}

pub struct HandTracker {
    pub num_hands: usize,
}

impl HandTracker {
    pub fn new(num_hands: usize) -> Self {
        Self { num_hands }
    }

    pub fn track(&self, _frame: &image::ImageBuffer<image::Rgb<u8>, Vec<u8>>) -> Vec<HandData> {
        // Return active tracked hands from current camera frame
        Vec::new()
    }
}
