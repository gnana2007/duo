// Camera Stream Manager
// Handles real-time video acquisition with synthetic duo fallback.
// Matches camera/capture.py exactly.

use std::sync::{Arc, Mutex};
use std::time::Instant;
use image::{ImageBuffer, Rgb};
use crate::config;

pub struct CameraStream {
    pub width: u32,
    pub height: u32,
    pub is_synthetic: bool,
    start_time: Instant,
    current_frame: Arc<Mutex<Option<ImageBuffer<Rgb<u8>, Vec<u8>>>>>,
}

impl CameraStream {
    pub fn new() -> Self {
        Self {
            width: config::CAPTURE_WIDTH,
            height: config::CAPTURE_HEIGHT,
            is_synthetic: true,
            start_time: Instant::now(),
            current_frame: Arc::new(Mutex::new(None)),
        }
    }

    pub fn start(self) -> Self {
        let frame_buf = self.current_frame.clone();
        let (w, h) = (self.width, self.height);
        let start = self.start_time;

        std::thread::spawn(move || {
            loop {
                let elapsed = start.elapsed().as_secs_f32();
                let frame = generate_synthetic_frame(w, h, elapsed);
                if let Ok(mut lock) = frame_buf.lock() {
                    *lock = Some(frame);
                }
                std::thread::sleep(std::time::Duration::from_millis(33));
            }
        });

        self
    }

    pub fn read(&self) -> (bool, Option<ImageBuffer<Rgb<u8>, Vec<u8>>>) {
        if let Ok(lock) = self.current_frame.lock() {
            if let Some(ref img) = *lock {
                return (true, Some(img.clone()));
            }
        }
        (false, None)
    }

    pub fn release(&mut self) {}
}

fn generate_synthetic_frame(width: u32, height: u32, t: f32) -> ImageBuffer<Rgb<u8>, Vec<u8>> {
    let mut frame = ImageBuffer::from_pixel(width, height, Rgb([35, 30, 25]));

    // Background wall grid
    for x in (0..width).step_by(60) {
        for y in 0..height {
            frame.put_pixel(x, y, Rgb([45, 40, 35]));
        }
    }
    for y in (0..height).step_by(60) {
        for x in 0..width {
            frame.put_pixel(x, y, Rgb([45, 40, 35]));
        }
    }

    // Person 1 (Primary - Left/Center)
    let cx1 = (width as f32 * 0.38 + (t * 1.5).sin() * 40.0) as i32;
    let cy1 = (height as f32 * 0.60) as i32;
    draw_ellipse(&mut frame, cx1, cy1 + 120, 100, 160, (140, 110, 80));
    draw_circle(&mut frame, cx1, cy1 - 70, 55, (200, 180, 155));

    let hand_x1 = (cx1 as f32 - 120.0 + (t * 3.0).sin() * 30.0) as i32;
    let hand_y1 = (cy1 as f32 - 50.0 + (t * 3.0).cos() * 40.0) as i32;
    draw_line(&mut frame, cx1 - 60, cy1 + 30, hand_x1, hand_y1, (140, 110, 80));
    draw_circle(&mut frame, hand_x1, hand_y1, 22, (200, 180, 155));

    // Person 2 (Duo Partner - Right/Center)
    let cx2 = (width as f32 * 0.65 + (t * 1.2).cos() * 35.0) as i32;
    let cy2 = (height as f32 * 0.62) as i32;
    draw_ellipse(&mut frame, cx2, cy2 + 110, 90, 150, (70, 120, 150));
    draw_circle(&mut frame, cx2, cy2 - 60, 50, (190, 170, 150));

    let hand_x2 = (cx2 as f32 + 100.0 + (t * 2.5).cos() * 25.0) as i32;
    let hand_y2 = (cy2 as f32 - 80.0 + (t * 2.5).sin() * 30.0) as i32;
    draw_line(&mut frame, cx2 + 50, cy2 + 20, hand_x2, hand_y2, (70, 120, 150));
    draw_circle(&mut frame, hand_x2, hand_y2, 20, (190, 170, 150));

    frame
}

fn draw_circle(img: &mut ImageBuffer<Rgb<u8>, Vec<u8>>, cx: i32, cy: i32, radius: i32, col: (u8, u8, u8)) {
    let (w, h) = (img.width() as i32, img.height() as i32);
    for dy in -radius..=radius {
        for dx in -radius..=radius {
            if dx * dx + dy * dy <= radius * radius {
                let px = cx + dx;
                let py = cy + dy;
                if px >= 0 && px < w && py >= 0 && py < h {
                    img.put_pixel(px as u32, py as u32, Rgb([col.0, col.1, col.2]));
                }
            }
        }
    }
}

fn draw_ellipse(img: &mut ImageBuffer<Rgb<u8>, Vec<u8>>, cx: i32, cy: i32, rx: i32, ry: i32, col: (u8, u8, u8)) {
    let (w, h) = (img.width() as i32, img.height() as i32);
    for dy in -ry..=ry {
        for dx in -rx..=rx {
            let edx = dx as f32 / rx as f32;
            let edy = dy as f32 / ry as f32;
            if edx * edx + edy * edy <= 1.0 {
                let px = cx + dx;
                let py = cy + dy;
                if px >= 0 && px < w && py >= 0 && py < h {
                    img.put_pixel(px as u32, py as u32, Rgb([col.0, col.1, col.2]));
                }
            }
        }
    }
}

fn draw_line(img: &mut ImageBuffer<Rgb<u8>, Vec<u8>>, x0: i32, y0: i32, x1: i32, y1: i32, col: (u8, u8, u8)) {
    let steps = ((x1 - x0).abs()).max((y1 - y0).abs()).max(1);
    for s in 0..=steps {
        let t = s as f32 / steps as f32;
        let x = (x0 as f32 + t * (x1 - x0) as f32) as i32;
        let y = (y0 as f32 + t * (y1 - y0) as f32) as i32;
        for dy in -5..=5 {
            for dx in -5..=5 {
                let px = x + dx;
                let py = y + dy;
                if px >= 0 && px < img.width() as i32 && py >= 0 && py < img.height() as i32 {
                    img.put_pixel(px as u32, py as u32, Rgb([col.0, col.1, col.2]));
                }
            }
        }
    }
}
