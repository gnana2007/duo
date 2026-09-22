// TimeSensei Temporal Memory System
// Matches interaction/memories.py exactly.

use std::time::Instant;
use image::{ImageBuffer, Rgb};
use crate::config;

#[derive(Clone)]
pub struct FrozenMemory {
    pub memory_id: usize,
    pub capture_time: Instant,
    pub frame_w: u32,
    pub frame_h: u32,
    pub origin_x: f32,
    pub origin_y: f32,
    pub width: u32,
    pub height: u32,
    pub crop_rgb: ImageBuffer<Rgb<u8>, Vec<u8>>,
    pub crop_alpha: Vec<f32>,
}

impl FrozenMemory {
    pub fn center_x(&self) -> i32 {
        (self.origin_x + self.width as f32 * 0.5) as i32
    }

    pub fn center_y(&self) -> i32 {
        (self.origin_y + self.height as f32 * 0.5) as i32
    }

    pub fn render_shadow(&self, canvas: &mut ImageBuffer<Rgb<u8>, Vec<u8>>) {
        let (cw, ch) = (canvas.width(), canvas.height());
        let dx = self.origin_x as i32;
        let dy = self.origin_y as i32;
        let mw = self.width as i32;
        let mh = self.height as i32;

        let shadow_cx = dx + mw / 2;
        let shadow_cy = (dy + mh - 2).min(ch as i32 - 4);
        let shadow_rx = (mw as f32 * 0.36) as i32;
        let shadow_ry = ((mh as f32 * 0.032) as i32).max(5);

        let x1 = (shadow_cx - shadow_rx * 2).max(0);
        let x2 = (shadow_cx + shadow_rx * 2).min(cw as i32);
        let y1 = (shadow_cy - shadow_ry * 2).max(0);
        let y2 = (shadow_cy + shadow_ry * 2).min(ch as i32);

        if x2 > x1 && y2 > y1 && shadow_cy > 0 {
            for y in y1..y2 {
                for x in x1..x2 {
                    let edx = (x - shadow_cx) as f32 / shadow_rx as f32;
                    let edy = (y - shadow_cy) as f32 / shadow_ry as f32;
                    let d2 = edx * edx + edy * edy;
                    if d2 <= 1.0 {
                        let falloff = (1.0 - d2).clamp(0.0, 1.0) * 0.40;
                        let factor = 1.0 - falloff;
                        let p = canvas.get_pixel_mut(x as u32, y as u32);
                        p.0[0] = (p.0[0] as f32 * factor) as u8;
                        p.0[1] = (p.0[1] as f32 * factor) as u8;
                        p.0[2] = (p.0[2] as f32 * factor) as u8;
                    }
                }
            }
        }
    }

    pub fn render_person(
        &self,
        canvas: &mut ImageBuffer<Rgb<u8>, Vec<u8>>,
        lut: Option<&[[u8; 3]; 256]>,
    ) {
        let (cw, ch) = (canvas.width(), canvas.height());
        let dx = self.origin_x as i32;
        let dy = self.origin_y as i32;
        let mw = self.width as i32;
        let mh = self.height as i32;

        let src_x1 = (-dx).max(0);
        let src_y1 = (-dy).max(0);
        let dst_x1 = dx.max(0);
        let dst_y1 = dy.max(0);
        let src_x2 = mw.min(cw as i32 - dx);
        let src_y2 = mh.min(ch as i32 - dy);

        if src_x1 < src_x2 && src_y1 < src_y2 && dst_x1 < cw as i32 && dst_y1 < ch as i32 {
            let copy_w = (src_x2 - src_x1) as u32;
            let copy_h = (src_y2 - src_y1) as u32;

            for r in 0..copy_h {
                let sy = src_y1 as u32 + r;
                let cy = dst_y1 as u32 + r;
                for c in 0..copy_w {
                    let sx = src_x1 as u32 + c;
                    let cx = dst_x1 as u32 + c;

                    let alpha = self.crop_alpha[(sy * self.width + sx) as usize];
                    if alpha <= 0.001 {
                        continue;
                    }

                    let src_px = self.crop_rgb.get_pixel(sx, sy);
                    let mut adapted_r = src_px.0[0];
                    let mut adapted_g = src_px.0[1];
                    let mut adapted_b = src_px.0[2];

                    if let Some(lut_table) = lut {
                        adapted_r = lut_table[src_px.0[0] as usize][2];
                        adapted_g = lut_table[src_px.0[1] as usize][1];
                        adapted_b = lut_table[src_px.0[2] as usize][0];
                    }

                    let dst_px = canvas.get_pixel_mut(cx, cy);
                    let inv = 1.0 - alpha;
                    dst_px.0[0] = (adapted_r as f32 * alpha + dst_px.0[0] as f32 * inv) as u8;
                    dst_px.0[1] = (adapted_g as f32 * alpha + dst_px.0[1] as f32 * inv) as u8;
                    dst_px.0[2] = (adapted_b as f32 * alpha + dst_px.0[2] as f32 * inv) as u8;
                }
            }
        }
    }
}

pub struct MemoryManager {
    pub memories: Vec<FrozenMemory>,
    next_id: usize,
}

impl MemoryManager {
    pub fn new() -> Self {
        Self {
            memories: Vec::new(),
            next_id: 1,
        }
    }

    pub fn create_memory(
        &mut self,
        frame: &ImageBuffer<Rgb<u8>, Vec<u8>>,
        alpha_mask: &[f32],
    ) -> Option<FrozenMemory> {
        let (fw, fh) = (frame.width() as usize, frame.height() as usize);

        // Find bounding box where alpha > 0.04
        let mut min_x = fw;
        let mut max_x = 0;
        let mut min_y = fh;
        let mut max_y = 0;

        for y in 0..fh {
            let row = y * fw;
            for x in 0..fw {
                if alpha_mask[row + x] > 0.04 {
                    if x < min_x { min_x = x; }
                    if x > max_x { max_x = x; }
                    if y < min_y { min_y = y; }
                    if y > max_y { max_y = y; }
                }
            }
        }

        if max_x <= min_x || max_y <= min_y {
            return None;
        }

        let bw = max_x - min_x;
        let bh = max_y - min_y;
        if bw < 10 || bh < 10 {
            return None;
        }

        // Generous safety padding (48px) to guarantee zero clipping of fingers or gestures
        let pad = 48usize;
        let x1 = min_x.saturating_sub(pad);
        let y1 = min_y.saturating_sub(pad);
        let x2 = (max_x + pad).min(fw);
        let y2 = (max_y + pad).min(fh);
        let crop_w = (x2 - x1) as u32;
        let crop_h = (y2 - y1) as u32;

        let mut crop_rgb = ImageBuffer::new(crop_w, crop_h);
        let mut clean_alpha = vec![0.0f32; (crop_w * crop_h) as usize];

        // Step 1: Smooth Hermite S-curve preserving fine fingers, gestures, and hair
        let span = 0.30f32;
        for cy in 0..crop_h {
            for cx in 0..crop_w {
                let sx = x1 as u32 + cx;
                let sy = y1 as u32 + cy;
                let raw_a = alpha_mask[sy as usize * fw + sx as usize];

                let t = ((raw_a - 0.10) / span).clamp(0.0, 1.0);
                let a = t * t * (3.0 - 2.0 * t);
                let idx = (cy * crop_w + cx) as usize;
                clean_alpha[idx] = a;

                if a > 0.001 {
                    crop_rgb.put_pixel(cx, cy, *frame.get_pixel(sx, sy));
                } else {
                    crop_rgb.put_pixel(cx, cy, Rgb([0, 0, 0]));
                }
            }
        }

        // Step 2: Multi-scale boundary color extension (eliminates black/dark halos)
        // Propagate inner body colors into the boundary transition zone (alpha between 0.01 and 0.70)
        let mut border_pixels = Vec::new();
        for cy in 0..crop_h {
            for cx in 0..crop_w {
                let a = clean_alpha[(cy * crop_w + cx) as usize];
                if a > 0.01 && a < 0.70 {
                    border_pixels.push((cx, cy));
                }
            }
        }

        for (bx, by) in border_pixels {
            // Find nearest inner pixel within radius 5
            let mut found_color = None;
            'search: for r in 1..=5 {
                for dy in -r..=r {
                    for dx in -r..=r {
                        let nx = bx as i32 + dx;
                        let ny = by as i32 + dy;
                        if nx >= 0 && nx < crop_w as i32 && ny >= 0 && ny < crop_h as i32 {
                            let n_idx = (ny as u32 * crop_w + nx as u32) as usize;
                            if clean_alpha[n_idx] >= 0.70 {
                                found_color = Some(*crop_rgb.get_pixel(nx as u32, ny as u32));
                                break 'search;
                            }
                        }
                    }
                }
            }
            if let Some(col) = found_color {
                crop_rgb.put_pixel(bx, by, col);
            }
        }

        // Bottom edge feathering if person was cut off at the bottom frame edge
        if y2 >= fh - 2 && crop_h > 12 {
            for r in 0..6.min(crop_h) {
                let factor = r as f32 / 6.0;
                let row = crop_h - 1 - r;
                for cx in 0..crop_w {
                    clean_alpha[(row * crop_w + cx) as usize] *= factor;
                }
            }
        }

        // FIFO eviction at MAX_MEMORIES
        if self.memories.len() >= config::MAX_MEMORIES {
            self.memories.remove(0);
        }

        let memory = FrozenMemory {
            memory_id: self.next_id,
            capture_time: Instant::now(),
            frame_w: fw as u32,
            frame_h: fh as u32,
            origin_x: x1 as f32,
            origin_y: y1 as f32,
            width: crop_w,
            height: crop_h,
            crop_rgb,
            crop_alpha: clean_alpha,
        };

        self.next_id += 1;
        self.memories.push(memory.clone());
        Some(memory)
    }

    pub fn render_all(
        &self,
        canvas: &mut ImageBuffer<Rgb<u8>, Vec<u8>>,
        lut: Option<&[[u8; 3]; 256]>,
    ) {
        if self.memories.is_empty() {
            return;
        }

        // Pass 1: Floor contact shadows underneath all clones
        for m in self.memories.iter().rev() {
            m.render_shadow(canvas);
        }

        // Pass 2: Person cutouts in strict depth ordering:
        // Later pictures (P2) drawn first (in background)
        // First picture (P1) drawn last (in foreground, at first)
        for m in self.memories.iter().rev() {
            m.render_person(canvas, lut);
        }
    }

    pub fn clear_all(&mut self) {
        self.memories.clear();
        self.next_id = 1;
    }
}
