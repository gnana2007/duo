// TimeSensei UI & Overlay Renderer
// Matches rendering/ui.py exactly.

use image::{ImageBuffer, Rgb, Rgba};
use std::path::Path;
use crate::config;

pub struct UIRenderer {
    pub watermark_hud: Option<ImageBuffer<Rgba<u8>, Vec<u8>>>,
    pub watermark_capture: Option<ImageBuffer<Rgba<u8>, Vec<u8>>>,
    pub watermark_mini: Option<ImageBuffer<Rgba<u8>, Vec<u8>>>,
}

impl UIRenderer {
    pub fn new() -> Self {
        let wm_path = config::assets_dir().join("watermark.png");
        let mut hud = None;
        let mut cap = None;
        let mut mini = None;

        if wm_path.exists() {
            if let Ok(dyn_img) = image::open(&wm_path) {
                let rgba = dyn_img.to_rgba8();
                hud = Some(image::imageops::resize(&rgba, 68, 68, image::imageops::FilterType::Lanczos3));
                cap = Some(image::imageops::resize(&rgba, 88, 88, image::imageops::FilterType::Lanczos3));
                mini = Some(image::imageops::resize(&rgba, 28, 28, image::imageops::FilterType::Lanczos3));
            }
        }

        Self {
            watermark_hud: hud,
            watermark_capture: cap,
            watermark_mini: mini,
        }
    }

    pub fn overlay_rgba(
        canvas: &mut ImageBuffer<Rgb<u8>, Vec<u8>>,
        overlay: &ImageBuffer<Rgba<u8>, Vec<u8>>,
        x: i32,
        y: i32,
    ) {
        let (cw, ch) = (canvas.width() as i32, canvas.height() as i32);
        let (ow, oh) = (overlay.width() as i32, overlay.height() as i32);

        let x1 = x.max(0);
        let y1 = y.max(0);
        let x2 = (x + ow).min(cw);
        let y2 = (y + oh).min(ch);

        if x1 >= x2 || y1 >= y2 {
            return;
        }

        for cy in y1..y2 {
            let oy = (cy - y) as u32;
            for cx in x1..x2 {
                let ox = (cx - x) as u32;
                let opx = overlay.get_pixel(ox, oy);
                let alpha = opx.0[3] as f32 / 255.0;
                if alpha <= 0.001 {
                    continue;
                }
                let cpx = canvas.get_pixel_mut(cx as u32, cy as u32);
                let inv = 1.0 - alpha;
                cpx.0[0] = (opx.0[0] as f32 * alpha + cpx.0[0] as f32 * inv) as u8;
                cpx.0[1] = (opx.0[1] as f32 * alpha + cpx.0[1] as f32 * inv) as u8;
                cpx.0[2] = (opx.0[2] as f32 * alpha + cpx.0[2] as f32 * inv) as u8;
            }
        }
    }

    pub fn draw_hud(
        &self,
        canvas: &mut ImageBuffer<Rgb<u8>, Vec<u8>>,
        timeline_name: &str,
        timeline_accent: (u8, u8, u8),
        memory_count: usize,
    ) {
        let (cw, ch) = (canvas.width(), canvas.height());

        // Top-Left: EXPO 2026 Watermark Logo
        if let Some(ref wm) = self.watermark_hud {
            Self::overlay_rgba(canvas, wm, 18, 14);
        }

        // Timeline Pill at top-left
        let pill_x = if self.watermark_hud.is_some() { 94 } else { 16 };
        draw_rounded_pill(canvas, pill_x, 16, 280, 42, (14, 16, 22), (160, 30, 45));
        // Accent dot
        fill_circle(canvas, pill_x + 16, 37, 5, timeline_accent);

        // Top-Right: Photo Count Pill
        let tr_w = if memory_count > 0 { 250 } else { 220 };
        let tr_x = cw.saturating_sub(tr_w + 16);
        draw_rounded_pill(canvas, tr_x, 16, tr_w, 42, (14, 16, 22), (60, 180, 100));
        fill_circle(canvas, tr_x + 16, 37, 4, (50, 220, 120));

        // Bottom Hints Bar
        let bar_w = 890u32;
        let bar_x = (cw.saturating_sub(bar_w)) / 2;
        let bar_y = ch.saturating_sub(48);
        draw_rounded_pill(canvas, bar_x, bar_y, bar_w, 34, (12, 14, 18), (60, 65, 80));
    }

    pub fn draw_pointing_indicator(
        &self,
        canvas: &mut ImageBuffer<Rgb<u8>, Vec<u8>>,
        direction: i32,
        progress: f32,
    ) {
        if direction == 0 {
            return;
        }

        let (cw, ch) = (canvas.width(), canvas.height());
        let is_left = direction < 0;

        let pill_w = 320u32;
        let pill_h = 56u32;
        let cx = if is_left { 36 } else { cw.saturating_sub(pill_w + 36) };
        let cy = ch / 2 - 28;

        let border_col = if is_left { (0, 210, 255) } else { (255, 130, 40) };
        let bg_col = if is_left { (10, 18, 28) } else { (28, 14, 10) };

        draw_rounded_pill(canvas, cx, cy, pill_w, pill_h, bg_col, border_col);

        // Progress bar at bottom of pill
        let prog_w = ((pill_w - 24) as f32 * progress.clamp(0.0, 1.0)) as u32;
        if prog_w > 0 {
            let fill_col = if is_left { (0, 240, 255) } else { (255, 140, 50) };
            for py in (cy + pill_h - 12)..(cy + pill_h - 6) {
                for px in (cx + 12)..(cx + 12 + prog_w) {
                    if px < cw && py < ch {
                        canvas.put_pixel(px, py, Rgb([fill_col.0, fill_col.1, fill_col.2]));
                    }
                }
            }
        }
    }

    pub fn draw_countdown(
        &self,
        canvas: &mut ImageBuffer<Rgb<u8>, Vec<u8>>,
        seconds_remaining: f32,
        total: f32,
    ) {
        let (cw, ch) = (canvas.width(), canvas.height());
        let cx = cw / 2;
        let cy = ch / 2;
        let progress = 1.0 - (seconds_remaining / total);

        // Circle dial
        let r = 115i32;
        for dy in -r..=r {
            for dx in -r..=r {
                let d2 = dx * dx + dy * dy;
                if d2 <= 105 * 105 {
                    let px = (cx as i32 + dx) as u32;
                    let py = (cy as i32 + dy) as u32;
                    if px < cw && py < ch {
                        let p = canvas.get_pixel_mut(px, py);
                        p.0[0] = (p.0[0] as f32 * 0.20 + 12.0 * 0.80) as u8;
                        p.0[1] = (p.0[1] as f32 * 0.20 + 14.0 * 0.80) as u8;
                        p.0[2] = (p.0[2] as f32 * 0.20 + 20.0 * 0.80) as u8;
                    }
                }
            }
        }

        // Progress ring
        let sweep = progress.clamp(0.0, 1.0);
        let ring_r = 109.0f32;
        let steps = (sweep * 360.0) as usize;
        for s in 0..steps {
            let angle = (s as f32 - 90.0).to_radians();
            let rx = (cx as f32 + angle.cos() * ring_r) as i32;
            let ry = (cy as f32 + angle.sin() * ring_r) as i32;
            for dy in -2..=2 {
                for dx in -2..=2 {
                    let px = (rx + dx) as u32;
                    let py = (ry + dy) as u32;
                    if px < cw && py < ch {
                        canvas.put_pixel(px, py, Rgb([255, 50, 0]));
                    }
                }
            }
        }
    }

    pub fn draw_flash(&self, canvas: &mut ImageBuffer<Rgb<u8>, Vec<u8>>, intensity: f32) {
        let (w, h) = (canvas.width(), canvas.height());
        let inv = 1.0 - intensity;
        for y in 0..h {
            for x in 0..w {
                let p = canvas.get_pixel_mut(x, y);
                p.0[0] = (255.0 * intensity + p.0[0] as f32 * inv) as u8;
                p.0[1] = (255.0 * intensity + p.0[1] as f32 * inv) as u8;
                p.0[2] = (255.0 * intensity + p.0[2] as f32 * inv) as u8;
            }
        }
    }

    pub fn draw_qr_popup(
        &self,
        canvas: &mut ImageBuffer<Rgb<u8>, Vec<u8>>,
        qr_image: &ImageBuffer<Rgb<u8>, Vec<u8>>,
        photo_path: Option<&str>,
    ) {
        let (cw, ch) = (canvas.width(), canvas.height());
        let margin = 18u32;

        let mut thumb_img: Option<ImageBuffer<Rgb<u8>, Vec<u8>>> = None;
        if let Some(pp) = photo_path {
            if Path::new(pp).exists() {
                if let Ok(dyn_img) = image::open(pp) {
                    thumb_img = Some(image::imageops::resize(
                        &dyn_img.to_rgb8(),
                        135,
                        95,
                        image::imageops::FilterType::Triangle,
                    ));
                }
            }
        }

        let has_thumb = thumb_img.is_some();
        let card_w = if has_thumb { 330u32 } else { 220u32 };
        let card_h = 180u32;
        let cx = cw.saturating_sub(card_w + margin);
        let cy = ch.saturating_sub(card_h + margin + 40);

        // Draw card background
        draw_rounded_pill(canvas, cx, cy, card_w, card_h, (14, 16, 24), (180, 30, 45));

        // Draw mini watermark in card header
        if let Some(ref wm) = self.watermark_mini {
            Self::overlay_rgba(canvas, wm, (cx + 12) as i32, (cy + 5) as i32);
        }

        // Draw thumbnail on left if present
        let qr_x = if has_thumb {
            let tx = cx + 18;
            let ty = cy + 34;
            if let Some(ref thumb) = thumb_img {
                for r in 0..95 {
                    for c in 0..135 {
                        let px = tx + c;
                        let py = ty + r;
                        if px < cw && py < ch {
                            canvas.put_pixel(px, py, *thumb.get_pixel(c, r));
                        }
                    }
                }
            }
            cx + card_w - 110 - 18
        } else {
            cx + (card_w - 110) / 2
        };

        // Draw QR code
        let qr_y = cy + 34;
        let qr_resized = image::imageops::resize(
            qr_image,
            110,
            110,
            image::imageops::FilterType::Nearest,
        );
        for r in 0..110 {
            for c in 0..110 {
                let px = qr_x + c;
                let py = qr_y + r;
                if px < cw && py < ch {
                    canvas.put_pixel(px, py, *qr_resized.get_pixel(c, r));
                }
            }
        }
    }

    pub fn apply_watermark(
        &self,
        photo: &ImageBuffer<Rgb<u8>, Vec<u8>>,
    ) -> ImageBuffer<Rgb<u8>, Vec<u8>> {
        let mut watermarked = photo.clone();
        if let Some(ref wm) = self.watermark_capture {
            Self::overlay_rgba(&mut watermarked, wm, 24, 20);
        } else if let Some(ref wm) = self.watermark_hud {
            Self::overlay_rgba(&mut watermarked, wm, 24, 20);
        }
        watermarked
    }
}

fn draw_rounded_pill(
    canvas: &mut ImageBuffer<Rgb<u8>, Vec<u8>>,
    x: u32,
    y: u32,
    w: u32,
    h: u32,
    bg_color: (u8, u8, u8),
    border_color: (u8, u8, u8),
) {
    let (cw, ch) = (canvas.width(), canvas.height());
    let x2 = (x + w).min(cw);
    let y2 = (y + h).min(ch);

    for cy in y..y2 {
        for cx in x..x2 {
            let is_border = cx == x || cx == x2 - 1 || cy == y || cy == y2 - 1;
            let col = if is_border { border_color } else { bg_color };
            let p = canvas.get_pixel_mut(cx, cy);
            let alpha = 0.88f32;
            let inv = 1.0 - alpha;
            p.0[0] = (col.0 as f32 * alpha + p.0[0] as f32 * inv) as u8;
            p.0[1] = (col.1 as f32 * alpha + p.0[1] as f32 * inv) as u8;
            p.0[2] = (col.2 as f32 * alpha + p.0[2] as f32 * inv) as u8;
        }
    }
}

fn fill_circle(
    canvas: &mut ImageBuffer<Rgb<u8>, Vec<u8>>,
    cx: u32,
    cy: u32,
    radius: i32,
    color: (u8, u8, u8),
) {
    let (cw, ch) = (canvas.width() as i32, canvas.height() as i32);
    let (icx, icy) = (cx as i32, cy as i32);
    for dy in -radius..=radius {
        for dx in -radius..=radius {
            if dx * dx + dy * dy <= radius * radius {
                let px = icx + dx;
                let py = icy + dy;
                if px >= 0 && px < cw && py >= 0 && py < ch {
                    canvas.put_pixel(px as u32, py as u32, Rgb([color.0, color.1, color.2]));
                }
            }
        }
    }
}
