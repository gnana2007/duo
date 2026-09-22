// TimeSensei Cinematic Startup & Attract Experience
// Matches rendering/intro.py.

use std::time::Instant;
use image::{ImageBuffer, Rgb, Rgba};
use crate::config;
use crate::vision::hands::HandData;

struct DustParticle {
    x: f32,
    y: f32,
    speed: f32,
    size: i32,
}

pub struct IntroRenderer {
    width: u32,
    height: u32,
    btn_x: u32,
    btn_y: u32,
    btn_w: u32,
    btn_h: u32,
    particles: Vec<DustParticle>,
    start_time: Instant,
    pub mouse_clicked_start: bool,
    watermark: Option<ImageBuffer<Rgba<u8>, Vec<u8>>>,
}

impl IntroRenderer {
    pub fn new(width: u32, height: u32) -> Self {
        let btn_w = 340u32;
        let btn_h = 54u32;
        let btn_x = (width - btn_w) / 2;
        let btn_y = (height as f32 * 0.74) as u32;

        let mut particles = Vec::new();
        for i in 0..40 {
            particles.push(DustParticle {
                x: ((i * 32) % width as usize) as f32,
                y: ((i * 19) % height as usize) as f32,
                speed: 15.0 + (i % 20) as f32,
                size: (i % 2 + 1) as i32,
            });
        }

        let wm_path = config::assets_dir().join("watermark.png");
        let mut wm = None;
        if wm_path.exists() {
            if let Ok(dyn_img) = image::open(&wm_path) {
                wm = Some(image::imageops::resize(
                    &dyn_img.to_rgba8(),
                    68,
                    68,
                    image::imageops::FilterType::Lanczos3,
                ));
            }
        }

        Self {
            width,
            height,
            btn_x,
            btn_y,
            btn_w,
            btn_h,
            particles,
            start_time: Instant::now(),
            mouse_clicked_start: false,
            watermark: wm,
        }
    }

    pub fn check_mouse_click(&mut self, x: u32, y: u32) -> bool {
        if x >= self.btn_x && x <= self.btn_x + self.btn_w && y >= self.btn_y && y <= self.btn_y + self.btn_h {
            self.mouse_clicked_start = true;
            return true;
        }
        false
    }

    pub fn render_attract(
        &mut self,
        live_frame: &ImageBuffer<Rgb<u8>, Vec<u8>>,
        _hands: &[HandData],
    ) -> (ImageBuffer<Rgb<u8>, Vec<u8>>, bool) {
        let mut canvas = ImageBuffer::new(self.width, self.height);
        let elapsed = self.start_time.elapsed().as_secs_f32();

        // 1. Desaturate & Darken Live Camera Feed
        for y in 0..self.height {
            for x in 0..self.width {
                let px = live_frame.get_pixel(x, y);
                let gray = (px.0[0] as f32 * 0.299 + px.0[1] as f32 * 0.587 + px.0[2] as f32 * 0.114) * 0.22;
                canvas.put_pixel(
                    x,
                    y,
                    Rgb([
                        (gray + 12.0).min(255.0) as u8,
                        (gray + 10.0).min(255.0) as u8,
                        (gray + 16.0).min(255.0) as u8,
                    ]),
                );
            }
        }

        // 2. Dust particles
        for p in &mut self.particles {
            p.y = (p.y + p.speed * 0.033) % self.height as f32;
            let px = p.x as i32;
            let py = p.y as i32;
            for dy in -p.size..=p.size {
                for dx in -p.size..=p.size {
                    let cx = px + dx;
                    let cy = py + dy;
                    if cx >= 0 && cx < self.width as i32 && cy >= 0 && cy < self.height as i32 {
                        canvas.put_pixel(cx as u32, cy as u32, Rgb([65, 60, 75]));
                    }
                }
            }
        }

        // 3. EXPO 2026 Watermark Logo
        if let Some(ref wm) = self.watermark {
            crate::rendering::ui::UIRenderer::overlay_rgba(&mut canvas, wm, 18, 14);
        }

        // 4. Start Button
        let btn_active = self.mouse_clicked_start;
        let col = if btn_active { (220, 40, 60) } else { (160, 20, 35) };
        for y in self.btn_y..(self.btn_y + self.btn_h) {
            for x in self.btn_x..(self.btn_x + self.btn_w) {
                let is_border = x == self.btn_x || x == self.btn_x + self.btn_w - 1 || y == self.btn_y || y == self.btn_y + self.btn_h - 1;
                let c = if is_border { (255, 60, 80) } else { col };
                canvas.put_pixel(x, y, Rgb([c.0, c.1, c.2]));
            }
        }

        let triggered = self.mouse_clicked_start;
        self.mouse_clicked_start = false;

        (canvas, triggered)
    }

    pub fn render_entering(
        &self,
        frame: &ImageBuffer<Rgb<u8>, Vec<u8>>,
        progress: f32,
    ) -> ImageBuffer<Rgb<u8>, Vec<u8>> {
        let mut display = frame.clone();
        let laser_y = (progress * self.height as f32) as i32;

        // Draw laser scan line
        for dy in -3..=3 {
            let y = laser_y + dy;
            if y >= 0 && y < self.height as i32 {
                for x in 0..self.width {
                    display.put_pixel(x, y as u32, Rgb([0, 220, 255]));
                }
            }
        }

        // EXPO 2026 Watermark Logo
        if let Some(ref wm) = self.watermark {
            crate::rendering::ui::UIRenderer::overlay_rgba(&mut display, wm, 18, 14);
        }

        display
    }
}
