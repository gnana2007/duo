// Comprehensive Verification Test Suite for TimeSensei Rust Port
// Ported directly from scratch/verify_all.py, test_pointing_and_logo.py, and test_no_cutting.py.

use image::{ImageBuffer, Rgb};
use std::thread::sleep;
use std::time::Duration;

use timesensei::capture::qr::QRCodeGenerator;
use timesensei::config;
use timesensei::interaction::gestures::GestureManager;
use timesensei::interaction::memories::MemoryManager;
use timesensei::rendering::compositor::NaturalCompositor;
use timesensei::rendering::ui::UIRenderer;
use timesensei::vision::hands::{
    detect_fist, detect_open_palm, detect_open_thumb, detect_pointing_direction, detect_victory,
    HandData,
};
use timesensei::vision::segmentation::PersonSegmenter;
use timesensei::world::environments::EnvironmentManager;

#[test]
fn test_segmentation_bounds() {
    let mut seg = PersonSegmenter::new();
    let dummy_frame = ImageBuffer::from_pixel(
        config::CAPTURE_WIDTH,
        config::CAPTURE_HEIGHT,
        Rgb([120, 120, 120]),
    );

    let mask = seg.compute_mask(&dummy_frame);
    assert_eq!(
        mask.len(),
        (config::CAPTURE_WIDTH * config::CAPTURE_HEIGHT) as usize
    );

    let min_val = mask.iter().cloned().fold(f32::INFINITY, f32::min);
    let max_val = mask.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
    assert!(min_val >= 0.0, "Mask min should be >= 0.0, got {}", min_val);
    assert!(max_val <= 1.0, "Mask max should be <= 1.0, got {}", max_val);

    let shadow = seg.generate_contact_shadow(&mask);
    assert_eq!(
        shadow.len(),
        (config::CAPTURE_WIDTH * config::CAPTURE_HEIGHT) as usize
    );
}

#[test]
fn test_compositor_alpha_and_lut() {
    let comp = NaturalCompositor::new();
    let mut env_mgr = EnvironmentManager::new(config::CAPTURE_WIDTH, config::CAPTURE_HEIGHT);
    let env = env_mgr.current().clone();
    let lut = env_mgr.get_lut(&env);

    let fg = ImageBuffer::from_pixel(config::CAPTURE_WIDTH, config::CAPTURE_HEIGHT, Rgb([200, 200, 200]));
    let bg = ImageBuffer::from_pixel(config::CAPTURE_WIDTH, config::CAPTURE_HEIGHT, Rgb([0, 0, 0]));

    let mut mask = vec![0.0f32; (config::CAPTURE_WIDTH * config::CAPTURE_HEIGHT) as usize];
    let shadow = vec![0.0f32; (config::CAPTURE_WIDTH * config::CAPTURE_HEIGHT) as usize];

    // Circle alpha in center
    let (cx, cy, r) = (640i32, 360i32, 100i32);
    for y in 0..config::CAPTURE_HEIGHT as i32 {
        for x in 0..config::CAPTURE_WIDTH as i32 {
            let d2 = (x - cx) * (x - cx) + (y - cy) * (y - cy);
            if d2 <= r * r {
                mask[(y as u32 * config::CAPTURE_WIDTH + x as u32) as usize] = 1.0;
            }
        }
    }

    let composited = comp.composite(&fg, &bg, &mask, &shadow, &env, &lut);
    assert_eq!(composited.width(), config::CAPTURE_WIDTH);
    assert_eq!(composited.height(), config::CAPTURE_HEIGHT);

    // Inside circle should be bright foreground
    let inside_px = composited.get_pixel(640, 360);
    assert!(inside_px.0[0] > 100, "Inside person should have foreground color");

    // Outside circle should be background black
    let outside_px = composited.get_pixel(100, 100);
    assert_eq!(outside_px.0, [0, 0, 0], "Outside person should be background");
}

#[test]
fn test_gesture_peace_capture_latching() {
    let mut gm = GestureManager::new();
    let hand_peace = HandData {
        id: 0,
        label: "Right".to_string(),
        palm_center: (640, 360),
        index_tip: (620, 200),
        thumb_tip: (580, 280),
        middle_tip: (660, 190),
        victory_center: (640, 195),
        is_pinching: false,
        is_open_palm: false,
        is_pointing_up: false,
        pointing_direction: 0,
        is_victory: true,
        is_thumb_open: false,
        is_fist: false,
        gesture: "Victory".to_string(),
        gesture_confidence: 0.90,
        all_landmarks: vec![(0, 0); 21],
    };

    let trig1 = gm.check_peace_capture(&[hand_peace.clone()]);
    assert!(!trig1, "Immediate check should not trigger without hold");

    sleep(Duration::from_millis(220));
    let trig2 = gm.check_peace_capture(&[hand_peace]);
    assert!(trig2, "Peace sign should trigger capture after 0.20s hold");
}

#[test]
fn test_gesture_thumb_and_fist() {
    let mut gm = GestureManager::new();
    let hand_thumb = HandData {
        id: 0,
        label: "Right".to_string(),
        palm_center: (640, 360),
        index_tip: (640, 330),
        thumb_tip: (560, 300),
        middle_tip: (640, 330),
        victory_center: (640, 330),
        is_pinching: false,
        is_open_palm: false,
        is_pointing_up: false,
        pointing_direction: 0,
        is_victory: false,
        is_thumb_open: true,
        is_fist: false,
        gesture: "Thumb_Up".to_string(),
        gesture_confidence: 0.88,
        all_landmarks: vec![(0, 0); 21],
    };

    let hand_fist = HandData {
        id: 0,
        label: "Right".to_string(),
        palm_center: (640, 360),
        index_tip: (640, 350),
        thumb_tip: (640, 350),
        middle_tip: (640, 350),
        victory_center: (640, 350),
        is_pinching: false,
        is_open_palm: false,
        is_pointing_up: false,
        pointing_direction: 0,
        is_victory: false,
        is_thumb_open: false,
        is_fist: true,
        gesture: "Closed_Fist".to_string(),
        gesture_confidence: 0.92,
        all_landmarks: vec![(0, 0); 21],
    };

    // Test Open Thumb trigger
    let trig_th1 = gm.check_thumb_trigger(&[hand_thumb.clone()]);
    assert!(!trig_th1);
    sleep(Duration::from_millis(200));
    let trig_th2 = gm.check_thumb_trigger(&[hand_thumb]);
    assert!(trig_th2, "Open thumb should trigger QR card after 0.18s hold");

    // Test Closed Fist dismiss
    let is_f = gm.check_fist(&[hand_fist.clone()]);
    assert!(is_f, "Fist should be detected");
    let is_fc = gm.check_fist_close_qr(&[hand_fist]);
    assert!(is_fc, "Fist close should dismiss QR card");
}

#[test]
fn test_index_finger_pointing_direction() {
    let palm_center = (640, 360);

    // 1. Synthetic Hand pointing LEFT
    let mut left_pts = vec![(640, 420); 21]; // Wrist at (640, 420) -> scale ~60
    left_pts[0] = (640, 420);
    left_pts[5] = (610, 350); // Index MCP
    left_pts[8] = (530, 345); // Index TIP: dx = -80 (pointing left)
    left_pts[9] = (630, 355);
    left_pts[12] = (635, 365); // Middle curled
    left_pts[16] = (640, 370); // Ring curled
    left_pts[20] = (645, 375); // Pinky curled

    let dir_left = detect_pointing_direction(&left_pts, palm_center);
    assert_eq!(dir_left, -1, "Expected index pointing LEFT (-1)");

    // 2. Synthetic Hand pointing RIGHT
    let mut right_pts = vec![(640, 420); 21];
    right_pts[0] = (640, 420);
    right_pts[5] = (670, 350); // Index MCP
    right_pts[8] = (750, 345); // Index TIP: dx = +80 (pointing right)
    right_pts[9] = (650, 355);
    right_pts[12] = (645, 365); // Middle curled
    right_pts[16] = (640, 370); // Ring curled
    right_pts[20] = (635, 375); // Pinky curled

    let dir_right = detect_pointing_direction(&right_pts, palm_center);
    assert_eq!(dir_right, 1, "Expected index pointing RIGHT (+1)");
}

#[test]
fn test_pointing_swipe_dwell_progress() {
    let mut gm = GestureManager::new();
    let hand_point_left = HandData {
        id: 0,
        label: "Right".to_string(),
        palm_center: (640, 360),
        index_tip: (530, 345),
        thumb_tip: (620, 370),
        middle_tip: (635, 365),
        victory_center: (600, 350),
        is_pinching: false,
        is_open_palm: false,
        is_pointing_up: false,
        pointing_direction: -1,
        is_victory: false,
        is_thumb_open: false,
        is_fist: false,
        gesture: "None".to_string(),
        gesture_confidence: 0.0,
        all_landmarks: vec![(0, 0); 21],
    };

    let (trig1, prog1, dir1) = gm.check_pointing_swipe(&[hand_point_left.clone()]);
    assert_eq!(dir1, -1);
    assert_eq!(trig1, 0, "Initial pointing check should not trigger yet");
    assert!(prog1 >= 0.0);

    sleep(Duration::from_millis(320));
    let (trig2, prog2, dir2) = gm.check_pointing_swipe(&[hand_point_left]);
    assert_eq!(dir2, -1);
    assert_eq!(trig2, -1, "Pointing left should trigger swipe after 0.30s hold");
    assert_eq!(prog2, 1.0);
}

#[test]
fn test_memory_padding_and_depth_ordering() {
    let mut mm = MemoryManager::new();
    let (w, h) = (config::CAPTURE_WIDTH, config::CAPTURE_HEIGHT);

    let frame1 = ImageBuffer::from_pixel(w, h, Rgb([255, 0, 0])); // P1 Red
    let mut mask1 = vec![0.0f32; (w * h) as usize];
    // Person 1 in center (x: 400..600, y: 200..500)
    for y in 200..500 {
        for x in 400..600 {
            mask1[(y * w + x) as usize] = 0.85;
        }
    }

    let m1 = mm.create_memory(&frame1, &mask1);
    assert!(m1.is_some(), "Memory 1 should be created");
    let mem1 = m1.unwrap();
    // Padding check: origin should be min_x - 48 = 352
    assert_eq!(mem1.origin_x as usize, 400 - 48, "48px padding should expand origin_x");
    assert_eq!(mem1.origin_y as usize, 200 - 48, "48px padding should expand origin_y");

    // Person 2 (Blue) overlapping Person 1
    let frame2 = ImageBuffer::from_pixel(w, h, Rgb([0, 0, 255]));
    let mut mask2 = vec![0.0f32; (w * h) as usize];
    for y in 250..550 {
        for x in 450..650 {
            mask2[(y * w + x) as usize] = 0.85;
        }
    }
    let m2 = mm.create_memory(&frame2, &mask2);
    assert!(m2.is_some(), "Memory 2 should be created");

    // Render both memories onto canvas
    let mut canvas = ImageBuffer::from_pixel(w, h, Rgb([0, 0, 0]));
    mm.render_all(&mut canvas, None);

    // Strict Depth Ordering:
    // In overlapping area (x: 500, y: 350), Person 1 (Red) must be in front of Person 2 (Blue)!
    let overlap_px = canvas.get_pixel(500, 350);
    assert!(
        overlap_px.0[0] > overlap_px.0[2],
        "Person 1 (Red) must stay in front of Person 2 (Blue) at overlap, got R:{} B:{}",
        overlap_px.0[0],
        overlap_px.0[2]
    );
}

#[test]
fn test_qr_generator() {
    let qr = QRCodeGenerator::new(8080);
    let img = qr.generate_qr_url("http://192.168.1.100:8080/photo/test123", 240);
    assert_eq!(img.width(), 240);
    assert_eq!(img.height(), 240);
}

#[test]
fn test_ui_watermark_integration() {
    let ui = UIRenderer::new();
    let mut frame = ImageBuffer::from_pixel(config::CAPTURE_WIDTH, config::CAPTURE_HEIGHT, Rgb([50, 50, 50]));
    let watermarked = ui.apply_watermark(&frame);
    assert_eq!(watermarked.width(), config::CAPTURE_WIDTH);
    assert_eq!(watermarked.height(), config::CAPTURE_HEIGHT);

    // Test HUD render without panic
    ui.draw_hud(&mut frame, "Present Reality", (180, 190, 200), 2);
}
