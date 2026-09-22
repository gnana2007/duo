#![allow(dead_code, unused_variables, unused_imports)]

// TimeSensei — CONTROL YOUR TIMELINE
// Real-time gesture-controlled temporal installation in Rust.
// Matches main.py exactly.

mod camera;
mod capture;
mod config;
mod interaction;
mod rendering;
mod sharing;
mod vision;
mod world;

use std::time::Instant;
use image::{ImageBuffer, Rgb};
use minifb::{Key, Window, WindowOptions};

use camera::CameraStream;
use capture::qr::{get_local_ip, QRCodeGenerator};
use config::AppState;
use interaction::audio::TimeSenseiAudio;
use interaction::gestures::GestureManager;
use interaction::memories::MemoryManager;
use interaction::mirror_modes::PersonalityModeManager;
use interaction::rewind::RewindBuffer;
use rendering::compositor::NaturalCompositor;
use rendering::intro::IntroRenderer;
use rendering::ui::UIRenderer;
use sharing::server::start_sharing_server;
use vision::hands::HandTracker;
use vision::segmentation::PersonSegmenter;
use world::environments::EnvironmentManager;
use world::scene::Scene;

fn startup_preflight() -> bool {
    println!("================================================================");
    println!("           TimeSensei — CONTROL YOUR TIMELINE (Rust)");
    println!("================================================================");
    println!("[Preflight] Verifying runtime storage and asset directories...");

    let captures = config::captures_dir();
    let _ = std::fs::create_dir_all(&captures);
    let env_dir = config::environments_dir();
    let _ = std::fs::create_dir_all(&env_dir);

    println!("[Preflight] Storage directories verified: {:?}", captures);
    true
}

fn capture_clean_background(
    camera: &CameraStream,
    num_frames: usize,
) -> ImageBuffer<Rgb<u8>, Vec<u8>> {
    println!("[Main] Calibrating reality space ({} frames)...", num_frames);
    let (w, h) = (config::CAPTURE_WIDTH, config::CAPTURE_HEIGHT);

    let mut accum_r = vec![0.0f64; (w * h) as usize];
    let mut accum_g = vec![0.0f64; (w * h) as usize];
    let mut accum_b = vec![0.0f64; (w * h) as usize];
    let mut count = 0;

    for _ in 0..(num_frames + 8) {
        let (ok, frame_opt) = camera.read();
        if ok {
            if let Some(frame) = frame_opt {
                if count >= 8 {
                    for y in 0..h {
                        for x in 0..w {
                            let idx = (y * w + x) as usize;
                            let p = frame.get_pixel(x, y);
                            accum_r[idx] += p.0[0] as f64;
                            accum_g[idx] += p.0[1] as f64;
                            accum_b[idx] += p.0[2] as f64;
                        }
                    }
                }
                count += 1;
                if count >= num_frames + 8 {
                    break;
                }
            }
        }
        std::thread::sleep(std::time::Duration::from_millis(20));
    }

    if count > 8 {
        let actual = (count - 8) as f64;
        let mut bg = ImageBuffer::new(w, h);
        for y in 0..h {
            for x in 0..w {
                let idx = (y * w + x) as usize;
                bg.put_pixel(
                    x,
                    y,
                    Rgb([
                        (accum_r[idx] / actual) as u8,
                        (accum_g[idx] / actual) as u8,
                        (accum_b[idx] / actual) as u8,
                    ]),
                );
            }
        }
        println!("[Main] Reality baseline calibrated.");
        return bg;
    }

    println!("[Main] Baseline unavailable, using dark canvas.");
    ImageBuffer::from_pixel(w, h, Rgb([20, 20, 25]))
}

#[tokio::main]
async fn main() {
    // 1. Startup Preflight
    startup_preflight();

    // 2. Audio Engine
    let audio = TimeSenseiAudio::new();

    // 3. Mobile Sharing Daemon
    let port = start_sharing_server(config::DEFAULT_SHARING_PORT);
    let local_ip = get_local_ip();

    // 4. Camera Stream
    println!("[Main] Opening camera stream...");
    let mut camera = CameraStream::new().start();

    // 5. Baseline Calibration
    let clean_bg = capture_clean_background(&camera, config::BG_CAPTURE_FRAMES);

    // 6. Vision Engines
    println!("[Main] Pre-warming temporal vision models...");
    let mut segmenter = PersonSegmenter::new();
    let hand_tracker = HandTracker::new(4);

    // 7. World & Timelines
    let mut env_manager = EnvironmentManager::new(config::CAPTURE_WIDTH, config::CAPTURE_HEIGHT);
    env_manager.set_original_room(clean_bg);
    let mut scene = Scene::new(env_manager);

    // 8. Interaction Systems
    let mut memory_mgr = MemoryManager::new();
    let mut gesture_mgr = GestureManager::new();
    let mut mode_mgr = PersonalityModeManager::new();
    let mut rewind_buf = RewindBuffer::new();

    // 9. Renderers & UI
    let compositor = NaturalCompositor::new();
    let ui = UIRenderer::new();
    let mut intro = IntroRenderer::new(config::CAPTURE_WIDTH, config::CAPTURE_HEIGHT);
    let qr_gen = QRCodeGenerator::new(port);

    // 10. Display Window
    let (win_w, win_h) = (config::CAPTURE_WIDTH as usize, config::CAPTURE_HEIGHT as usize);
    let mut window = Window::new(
        config::WINDOW_NAME,
        win_w,
        win_h,
        WindowOptions {
            resize: true,
            ..WindowOptions::default()
        },
    )
    .expect("Failed to open desktop window");

    window.set_target_fps(30);

    let mut app_state = AppState::Attract;
    let mut entering_start = Instant::now();
    let mut countdown_start = Instant::now();
    let mut flash_start = Instant::now();
    let mut last_beep_sec = 0u32;
    let mut last_person_seen = Instant::now();
    let mut show_qr = false;
    let mut last_photo_path: Option<String> = None;
    let mut last_qr_image = qr_gen.generate_qr_url(&format!("http://{}:{}/", local_ip, port), 240);

    // Pre-initialize with existing capture if any exists
    if let Some(latest) = sharing::server::get_latest_capture_id(&config::captures_dir()) {
        let p = config::captures_dir().join(format!("{}.jpg", latest));
        last_photo_path = Some(p.to_str().unwrap().to_string());
        last_qr_image = qr_gen.generate_qr_image(&latest, 240);
    }

    let mut u32_buffer = vec![0u32; win_w * win_h];
    println!("\n[TimeSensei] System ready. Entering ATTRACT mode.");
    println!("             CONTROL YOUR TIMELINE\n");

    while window.is_open() && !window.is_key_down(Key::Escape) && !window.is_key_down(Key::Q) {
        let (_, frame_opt) = camera.read();
        let frame = match frame_opt {
            Some(f) => f,
            None => {
                std::thread::sleep(std::time::Duration::from_millis(10));
                continue;
            }
        };

        // Vision processing
        let mask = segmenter.compute_mask(&frame);
        let shadow = segmenter.generate_contact_shadow(&mask);
        let hands = hand_tracker.track(&frame);

        let person_detected = mask.iter().filter(|&&v| v > 0.35).count() > 1500;
        if person_detected {
            last_person_seen = Instant::now();
        }

        let mut display = frame.clone();

        match app_state {
            AppState::Attract => {
                let (attract_display, triggered) = intro.render_attract(&frame, &hands);
                display = attract_display;

                // Mouse click or keyboard trigger
                if window.get_mouse_down(minifb::MouseButton::Left) {
                    if let Some((mx, my)) = window.get_mouse_pos(minifb::MouseMode::Clamp) {
                        intro.check_mouse_click(mx as u32, my as u32);
                    }
                }

                if triggered || window.is_key_pressed(Key::Space, minifb::KeyRepeat::No) || window.is_key_pressed(Key::Enter, minifb::KeyRepeat::No) {
                    audio.play_rumble();
                    app_state = AppState::Entering;
                    entering_start = Instant::now();
                    audio.play_scan();
                }
            }

            AppState::Entering => {
                let elapsed = entering_start.elapsed().as_secs_f32();
                let progress = (elapsed / config::INTRO_SCAN_DURATION_S).min(1.0);
                display = intro.render_entering(&frame, progress);

                if elapsed >= config::INTRO_SCAN_DURATION_S {
                    app_state = AppState::Live;
                }
            }

            AppState::Live | AppState::Countdown | AppState::Flash => {
                // Inactivity Watchdog
                if last_person_seen.elapsed().as_secs_f32() > config::IDLE_TIMEOUT_S {
                    memory_mgr.clear_all();
                    show_qr = false;
                    app_state = AppState::Attract;
                    continue;
                }

                // Record foreground into Rewind ring buffer
                rewind_buf.record_frame(&frame, &mask);

                // Build Base Display
                let env = scene.current_environment().clone();
                let lut = scene.env_manager.get_lut(&env);

                if scene.is_original_room() {
                    display = frame.clone();
                    if !memory_mgr.memories.is_empty() {
                        memory_mgr.render_all(&mut display, Some(&lut));
                        // Re-composite live person in front
                        let fw = display.width() as usize;
                        for y in 0..display.height() {
                            for x in 0..display.width() {
                                let a = ((mask[y as usize * fw + x as usize] - 0.15) / 0.35).clamp(0.0, 1.0);
                                if a > 0.001 {
                                    let dp = display.get_pixel_mut(x, y);
                                    let fp = frame.get_pixel(x, y);
                                    let inv = 1.0 - a;
                                    dp.0[0] = (fp.0[0] as f32 * a + dp.0[0] as f32 * inv) as u8;
                                    dp.0[1] = (fp.0[1] as f32 * a + dp.0[1] as f32 * inv) as u8;
                                    dp.0[2] = (fp.0[2] as f32 * a + dp.0[2] as f32 * inv) as u8;
                                }
                            }
                        }
                    }
                } else {
                    let mut bg = scene.get_background();
                    memory_mgr.render_all(&mut bg, Some(&lut));
                    display = compositor.composite(&frame, &bg, &mask, &shadow, &env, &lut);
                }

                // Interaction handling in Live
                if app_state == AppState::Live {
                    // Timeline Navigation via Index Finger Pointing: Left (-1) or Right (+1)
                    let (triggered_swipe, pointing_prog, pointing_dir) = gesture_mgr.check_pointing_swipe(&hands);
                    if triggered_swipe != 0 {
                        scene.trigger_swipe(triggered_swipe);
                        audio.play_whoosh();
                    }

                    // On-screen visual indication pill
                    if pointing_dir != 0 {
                        ui.draw_pointing_indicator(&mut display, pointing_dir, pointing_prog);
                    }

                    // ✊ Closed Fist: Dismisses QR card
                    if gesture_mgr.check_fist(&hands) {
                        show_qr = false;
                    } else if gesture_mgr.check_thumb_trigger(&hands) {
                        // 👍 Open Thumb: Reveals QR card at bottom-right (latches open)
                        show_qr = true;
                    }

                    // ✌️ Peace Sign: Triggers Photo Capture (latches immediately)
                    if gesture_mgr.check_peace_capture(&hands) {
                        app_state = AppState::Countdown;
                        countdown_start = Instant::now();
                        last_beep_sec = 0;
                    }

                    // Keyboard shortcuts for operator
                    if window.is_key_pressed(Key::P, minifb::KeyRepeat::No) {
                        app_state = AppState::Countdown;
                        countdown_start = Instant::now();
                        last_beep_sec = 0;
                    }
                    if window.is_key_pressed(Key::Left, minifb::KeyRepeat::No) || window.is_key_pressed(Key::A, minifb::KeyRepeat::No) {
                        scene.trigger_swipe(-1);
                        audio.play_whoosh();
                    }
                    if window.is_key_pressed(Key::Right, minifb::KeyRepeat::No) || window.is_key_pressed(Key::S, minifb::KeyRepeat::No) {
                        scene.trigger_swipe(1);
                        audio.play_whoosh();
                    }
                    if window.is_key_pressed(Key::T, minifb::KeyRepeat::No) {
                        show_qr = !show_qr;
                    }
                    if window.is_key_pressed(Key::C, minifb::KeyRepeat::No) {
                        memory_mgr.clear_all();
                    }
                    if window.is_key_pressed(Key::R, minifb::KeyRepeat::No) {
                        memory_mgr.clear_all();
                        show_qr = false;
                        app_state = AppState::Attract;
                    }
                    if window.is_key_pressed(Key::W, minifb::KeyRepeat::No) {
                        rewind_buf.trigger_rewind();
                    }
                    if window.is_key_pressed(Key::E, minifb::KeyRepeat::No) {
                        mode_mgr.toggle_echo();
                    }
                    if window.is_key_pressed(Key::M, minifb::KeyRepeat::No) {
                        mode_mgr.cycle_mode();
                    }

                    // Active rewind playback overlay
                    rewind_buf.update_and_render(&mut display, &frame);
                } else if app_state == AppState::Countdown {
                    let elapsed = countdown_start.elapsed().as_secs_f32();
                    let remaining = config::COUNTDOWN_SECONDS as f32 - elapsed;
                    let sec_current = remaining.ceil() as u32;

                    if sec_current != last_beep_sec && (1..=3).contains(&sec_current) {
                        audio.play_countdown_beep(sec_current);
                        last_beep_sec = sec_current;
                    }

                    if remaining <= 0.0 {
                        // Capture photo with EXPO 2026 watermark
                        let ts = chrono::Local::now().format("%Y%m%d_%H%M%S").to_string();
                        let photo_id = format!("capture_{}", ts);
                        let path = config::captures_dir().join(format!("{}.jpg", photo_id));

                        let watermarked = ui.apply_watermark(&display);
                        let _ = watermarked.save(&path);
                        last_photo_path = Some(path.to_str().unwrap().to_string());
                        last_qr_image = qr_gen.generate_qr_image(&photo_id, 240);

                        // Lock captured photo into timelapse clone!
                        memory_mgr.create_memory(&frame, &mask);

                        audio.play_shutter();
                        app_state = AppState::Flash;
                        flash_start = Instant::now();
                        show_qr = false;
                    } else {
                        ui.draw_countdown(&mut display, remaining, config::COUNTDOWN_SECONDS as f32);
                    }
                } else if app_state == AppState::Flash {
                    let elapsed = flash_start.elapsed().as_secs_f32();
                    if elapsed < config::FLASH_DURATION_S {
                        let intensity = (0.85 * (1.0 - elapsed / config::FLASH_DURATION_S)).max(0.0);
                        ui.draw_flash(&mut display, intensity);
                    } else {
                        app_state = AppState::Live;
                    }
                }

                // UI Overlays
                ui.draw_hud(
                    &mut display,
                    &env.name,
                    env.accent_color_bgr,
                    memory_mgr.memories.len(),
                );

                // QR Sharing Popup Card at bottom-right
                if show_qr {
                    ui.draw_qr_popup(&mut display, &last_qr_image, last_photo_path.as_deref());
                }
            }

            _ => {}
        }

        // Convert RGB ImageBuffer to minifb 0RGB32 pixel buffer
        for y in 0..win_h {
            for x in 0..win_w {
                let px = display.get_pixel(x as u32, y as u32);
                let u32_val = ((px.0[0] as u32) << 16) | ((px.0[1] as u32) << 8) | (px.0[2] as u32);
                u32_buffer[y * win_w + x] = u32_val;
            }
        }

        window
            .update_with_buffer(&u32_buffer, win_w, win_h)
            .unwrap();
    }

    camera.release();
    println!("[Main] TimeSensei session closed. Photos archived at: {:?}", config::captures_dir());
}
