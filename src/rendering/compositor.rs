// Natural Compositor Engine
// Matches rendering/compositor.py exactly.

use image::{ImageBuffer, Rgb};
use crate::config;
use crate::world::environments::Environment;

pub struct NaturalCompositor;

impl NaturalCompositor {
    pub fn new() -> Self {
        Self
    }

    pub fn composite(
        &self,
        fg_frame: &ImageBuffer<Rgb<u8>, Vec<u8>>,
        bg_frame: &ImageBuffer<Rgb<u8>, Vec<u8>>,
        alpha_mask: &[f32],
        shadow_mask: &[f32],
        env: &Environment,
        lut: &[[u8; 3]; 256],
    ) -> ImageBuffer<Rgb<u8>, Vec<u8>> {
        let (w, h) = (fg_frame.width() as usize, fg_frame.height() as usize);
        let mut out = bg_frame.clone();

        // 1. Fast Bounding Box Detection
        let mut min_x = w;
        let mut max_x = 0;
        let mut min_y = h;
        let mut max_y = 0;

        for y in 0..h {
            let row = y * w;
            for x in 0..w {
                if alpha_mask[row + x] > 0.01 {
                    if x < min_x { min_x = x; }
                    if x > max_x { max_x = x; }
                    if y < min_y { min_y = y; }
                    if y > max_y { max_y = y; }
                }
            }
        }

        if max_x <= min_x || max_y <= min_y {
            return out;
        }

        let margin_x = 18usize;
        let margin_y_top = 18usize;
        let margin_y_bottom = 45usize;

        let x1 = min_x.saturating_sub(margin_x);
        let y1 = min_y.saturating_sub(margin_y_top);
        let x2 = (max_x + margin_x).min(w);
        let y2 = (max_y + margin_y_bottom).min(h);

        // 2. Composite within active ROI slice
        for y in y1..y2 {
            let row = y * w;
            for x in x1..x2 {
                let idx = row + x;
                let alpha = alpha_mask[idx];
                let shadow = shadow_mask[idx];

                let bg_px = out.get_pixel_mut(x as u32, y as u32);
                let mut bg_r = bg_px.0[0] as f32;
                let mut bg_g = bg_px.0[1] as f32;
                let mut bg_b = bg_px.0[2] as f32;

                // Ground contact shadow
                if shadow > 0.01 {
                    let s_factor = (1.0 - shadow.clamp(0.0, 0.75)).max(0.0);
                    bg_r *= s_factor;
                    bg_g *= s_factor;
                    bg_b *= s_factor;
                }

                if alpha > 0.001 {
                    let fg_px = fg_frame.get_pixel(x as u32, y as u32);
                    // Adapt lighting via hardware LUT
                    let adapted_r = lut[fg_px.0[0] as usize][2] as f32;
                    let adapted_g = lut[fg_px.0[1] as usize][1] as f32;
                    let adapted_b = lut[fg_px.0[2] as usize][0] as f32;

                    // Lerp alpha blend
                    let inv = 1.0 - alpha;
                    let final_r = (adapted_r * alpha + bg_r * inv).clamp(0.0, 255.0);
                    let final_g = (adapted_g * alpha + bg_g * inv).clamp(0.0, 255.0);
                    let final_b = (adapted_b * alpha + bg_b * inv).clamp(0.0, 255.0);

                    bg_px.0[0] = final_r as u8;
                    bg_px.0[1] = final_g as u8;
                    bg_px.0[2] = final_b as u8;
                } else if shadow > 0.01 {
                    bg_px.0[0] = bg_r as u8;
                    bg_px.0[1] = bg_g as u8;
                    bg_px.0[2] = bg_b as u8;
                }
            }
        }

        out
    }
}
