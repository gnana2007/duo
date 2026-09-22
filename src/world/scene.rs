// Scene Transition Manager
// Matches world/scene.py exactly.

use std::time::Instant;
use image::{ImageBuffer, Rgb};
use crate::config;
use crate::world::environments::{Environment, EnvironmentManager};

pub struct Scene {
    pub env_manager: EnvironmentManager,
    pub transitioning: bool,
    pub transition_start_time: Instant,
    pub transition_duration: f32,
    pub transition_direction: i32,
    from_image: ImageBuffer<Rgb<u8>, Vec<u8>>,
    to_image: ImageBuffer<Rgb<u8>, Vec<u8>>,
}

impl Scene {
    pub fn new(env_manager: EnvironmentManager) -> Self {
        let cur_img = env_manager.current().image.clone();
        Self {
            env_manager,
            transitioning: false,
            transition_start_time: Instant::now(),
            transition_duration: config::ENV_TRANSITION_DURATION,
            transition_direction: 0,
            from_image: cur_img.clone(),
            to_image: cur_img,
        }
    }

    pub fn trigger_swipe(&mut self, direction: i32) {
        if self.transitioning {
            return;
        }
        self.from_image = self.env_manager.current().image.clone();
        if direction > 0 {
            self.to_image = self.env_manager.next().image.clone();
        } else {
            self.to_image = self.env_manager.previous().image.clone();
        }
        self.transition_direction = direction;
        self.transition_start_time = Instant::now();
        self.transitioning = true;
    }

    pub fn get_background(&mut self) -> ImageBuffer<Rgb<u8>, Vec<u8>> {
        if !self.transitioning {
            return self.env_manager.current().image.clone();
        }

        let elapsed = self.transition_start_time.elapsed().as_secs_f32();
        let progress = (elapsed / self.transition_duration).min(1.0);

        if progress >= 1.0 {
            self.transitioning = false;
            return self.env_manager.current().image.clone();
        }

        let w = self.env_manager.width;
        let h = self.env_manager.height;

        // Ease-out cubic: 1.0 - (1.0 - progress)^3
        let ease = 1.0 - (1.0 - progress).powi(3);
        let shift = ((ease * w as f32) as u32).min(w);

        let mut canvas = ImageBuffer::new(w, h);

        if self.transition_direction > 0 {
            // Slide right: old exits right, new enters from left
            for y in 0..h {
                // New entering on left: [0..shift] from to_image[w - shift..w]
                for x in 0..shift {
                    let src_x = w - shift + x;
                    canvas.put_pixel(x, y, *self.to_image.get_pixel(src_x, y));
                }
                // Old exiting on right: [shift..w] from from_image[0..w - shift]
                for x in shift..w {
                    let src_x = x - shift;
                    canvas.put_pixel(x, y, *self.from_image.get_pixel(src_x, y));
                }
            }
        } else {
            // Slide left: old exits left, new enters from right
            for y in 0..h {
                // Old exiting on left: [0..w - shift] from from_image[shift..w]
                for x in 0..(w - shift) {
                    let src_x = shift + x;
                    canvas.put_pixel(x, y, *self.from_image.get_pixel(src_x, y));
                }
                // New entering on right: [w - shift..w] from to_image[0..shift]
                for x in (w - shift)..w {
                    let src_x = x - (w - shift);
                    canvas.put_pixel(x, y, *self.to_image.get_pixel(src_x, y));
                }
            }
        }

        canvas
    }

    pub fn current_environment(&self) -> &Environment {
        self.env_manager.current()
    }

    pub fn is_original_room(&self) -> bool {
        self.env_manager.is_original_room() && !self.transitioning
    }
}
