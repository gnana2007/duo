// Motion Tracker & Swipe Velocity Estimator
// Matches vision/motion.py.

use std::time::Instant;

pub struct MotionTracker {
    last_positions: Vec<(Instant, f32, f32)>,
    last_swipe_time: Instant,
}

impl MotionTracker {
    pub fn new() -> Self {
        Self {
            last_positions: Vec::new(),
            last_swipe_time: Instant::now() - std::time::Duration::from_secs(10),
        }
    }

    pub fn update(&mut self, pos: Option<(f32, f32)>) -> i32 {
        let now = Instant::now();
        if let Some((x, y)) = pos {
            self.last_positions.push((now, x, y));
            self.last_positions.retain(|(t, _, _)| now.duration_since(*t).as_secs_f32() < 0.5);

            if self.last_positions.len() >= 3 && now.duration_since(self.last_swipe_time).as_secs_f32() > 0.45 {
                let first = self.last_positions.first().unwrap();
                let last = self.last_positions.last().unwrap();
                let dt = last.0.duration_since(first.0).as_secs_f32();
                if dt > 0.05 {
                    let vx = (last.1 - first.1) / dt;
                    if vx > 280.0 {
                        self.last_swipe_time = now;
                        return 1;
                    } else if vx < -280.0 {
                        self.last_swipe_time = now;
                        return -1;
                    }
                }
            }
        } else {
            self.last_positions.clear();
        }
        0
    }
}
