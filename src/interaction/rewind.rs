// Real-Time Temporal Rewind Engine
// Matches interaction/rewind.py.

use std::collections::VecDeque;
use std::time::Instant;
use image::{ImageBuffer, Rgb};
use crate::config;

#[derive(Clone)]
struct HistoryFrame {
    timestamp: Instant,
    small_rgb: ImageBuffer<Rgb<u8>, Vec<u8>>,
    small_mask: Vec<u8>,
}

pub struct RewindBuffer {
    history: VecDeque<HistoryFrame>,
    max_frames: usize,
    frame_interval: f32,
    last_record_time: Instant,
    pub is_rewinding: bool,
    playback_frames: Vec<HistoryFrame>,
    playback_start_time: Instant,
}

impl RewindBuffer {
    pub fn new() -> Self {
        let fps = 12.0f32;
        let max_frames = (config::REWIND_BUFFER_SECONDS * fps) as usize;
        Self {
            history: VecDeque::with_capacity(max_frames),
            max_frames,
            frame_interval: 1.0 / fps,
            last_record_time: Instant::now() - std::time::Duration::from_secs(10),
            is_rewinding: false,
            playback_frames: Vec::new(),
            playback_start_time: Instant::now(),
        }
    }

    pub fn record_frame(&mut self, frame: &ImageBuffer<Rgb<u8>, Vec<u8>>, mask: &[f32]) {
        if self.is_rewinding {
            return;
        }

        let now = Instant::now();
        if now.duration_since(self.last_record_time).as_secs_f32() < self.frame_interval {
            return;
        }
        self.last_record_time = now;

        let sw = config::VISION_WIDTH;
        let sh = config::VISION_HEIGHT;
        let small_rgb = image::imageops::resize(frame, sw, sh, image::imageops::FilterType::Nearest);

        let fw = frame.width() as usize;
        let mut small_mask = vec![0u8; (sw * sh) as usize];
        for y in 0..sh {
            let fy = ((y as f32 / sh as f32) * frame.height() as f32) as usize;
            for x in 0..sw {
                let fx = ((x as f32 / sw as f32) * frame.width() as f32) as usize;
                let a = mask[fy * fw + fx];
                small_mask[(y * sw + x) as usize] = (a * 255.0) as u8;
            }
        }

        if self.history.len() >= self.max_frames {
            self.history.pop_front();
        }
        self.history.push_back(HistoryFrame {
            timestamp: now,
            small_rgb,
            small_mask,
        });
    }

    pub fn trigger_rewind(&mut self) -> bool {
        if self.is_rewinding || self.history.len() < 12 {
            return false;
        }
        self.is_rewinding = true;
        self.playback_frames = self.history.iter().cloned().collect();
        self.playback_start_time = Instant::now();
        true
    }

    pub fn update_and_render(
        &mut self,
        canvas: &mut ImageBuffer<Rgb<u8>, Vec<u8>>,
        _bg: &ImageBuffer<Rgb<u8>, Vec<u8>>,
    ) -> bool {
        if !self.is_rewinding {
            return false;
        }

        let elapsed = self.playback_start_time.elapsed().as_secs_f32();
        let total_time = self.playback_frames.len() as f32 * self.frame_interval;

        if elapsed >= total_time || self.playback_frames.is_empty() {
            self.is_rewinding = false;
            self.playback_frames.clear();
            return false;
        }

        let progress = elapsed / total_time;
        let idx = ((1.0 - progress) * (self.playback_frames.len() - 1) as f32) as usize;
        let idx = idx.min(self.playback_frames.len() - 1);

        let p_frame = &self.playback_frames[idx];
        let upscaled = image::imageops::resize(
            &p_frame.small_rgb,
            canvas.width(),
            canvas.height(),
            image::imageops::FilterType::Triangle,
        );

        // Blend onto canvas with temporal chromatic tint
        let (w, h) = (canvas.width(), canvas.height());
        for y in 0..h {
            for x in 0..w {
                let p = canvas.get_pixel_mut(x, y);
                let up = upscaled.get_pixel(x, y);
                p.0[0] = (p.0[0] as f32 * 0.35 + up.0[0] as f32 * 0.65) as u8;
                p.0[1] = (p.0[1] as f32 * 0.35 + up.0[1] as f32 * 0.65) as u8;
                p.0[2] = ((p.0[2] as f32 * 0.25 + up.0[2] as f32 * 0.75) * 1.15).min(255.0) as u8;
            }
        }

        true
    }
}
