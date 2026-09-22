// Virtual Environment Manager
// Matches world/environments.py exactly.

use image::{ImageBuffer, Rgb};
use std::collections::HashMap;
use crate::config;

#[derive(Clone)]
pub struct Environment {
    pub id: String,
    pub name: String,
    pub accent_color_bgr: (u8, u8, u8),
    pub ambient_tint_bgr: (f32, f32, f32),
    pub brightness_multiplier: f32,
    pub contrast_multiplier: f32,
    pub image: ImageBuffer<Rgb<u8>, Vec<u8>>,
}

pub struct EnvironmentManager {
    pub width: u32,
    pub height: u32,
    pub environments: Vec<Environment>,
    pub current_index: usize,
    lut_cache: HashMap<String, [[u8; 3]; 256]>,
}

impl EnvironmentManager {
    pub fn new(width: u32, height: u32) -> Self {
        let mut mgr = Self {
            width,
            height,
            environments: Vec::new(),
            current_index: 0,
            lut_cache: HashMap::new(),
        };
        mgr.add_original_room_placeholder();
        mgr.load_or_generate_environments();
        mgr
    }

    fn add_original_room_placeholder(&mut self) {
        let placeholder = ImageBuffer::from_pixel(self.width, self.height, Rgb([0, 0, 0]));
        self.environments.push(Environment {
            id: "original_room".to_string(),
            name: "Present Reality".to_string(),
            accent_color_bgr: (180, 190, 200),
            ambient_tint_bgr: (1.0, 1.0, 1.0),
            brightness_multiplier: 1.0,
            contrast_multiplier: 1.0,
            image: placeholder,
        });
    }

    pub fn set_original_room(&mut self, bg_frame: ImageBuffer<Rgb<u8>, Vec<u8>>) {
        if !self.environments.is_empty() {
            self.environments[0].image = bg_frame;
        }
    }

    fn load_or_generate_environments(&mut self) {
        struct EnvDef {
            id: &'static str,
            name: &'static str,
            files: &'static [&'static str],
            accent: (u8, u8, u8),
            tint: (f32, f32, f32),
            brightness: f32,
            contrast: f32,
        }

        let configs = [
            EnvDef {
                id: "haunted_castle",
                name: "Haunted Castle",
                files: &["haunted_castle.jpg", "haunted_room.png"],
                accent: (40, 45, 190),
                tint: (0.85, 0.85, 0.92),
                brightness: 0.88,
                contrast: 1.18,
            },
            EnvDef {
                id: "cyberpunk",
                name: "Cyberpunk Metropolis",
                files: &["cyberpunk_loft.png", "neon_metropolis.jpg"],
                accent: (240, 60, 220),
                tint: (1.15, 0.90, 1.15),
                brightness: 1.05,
                contrast: 1.15,
            },
            EnvDef {
                id: "sunlit_penthouse",
                name: "Luxury Penthouse",
                files: &["sunlit_penthouse.png"],
                accent: (80, 190, 240),
                tint: (0.95, 1.05, 1.10),
                brightness: 1.05,
                contrast: 1.05,
            },
            EnvDef {
                id: "space_nebula",
                name: "Cosmic Nebula",
                files: &["space_nebula.jpg", "space.png"],
                accent: (220, 100, 180),
                tint: (1.20, 0.85, 1.15),
                brightness: 0.95,
                contrast: 1.20,
            },
            EnvDef {
                id: "tropical_beach",
                name: "Sunset Beach",
                files: &["tropical_beach.jpg"],
                accent: (60, 180, 255),
                tint: (0.90, 1.05, 1.15),
                brightness: 1.05,
                contrast: 1.05,
            },
            EnvDef {
                id: "zen_sanctuary",
                name: "Zen Sanctuary",
                files: &["zen_sanctuary.png"],
                accent: (80, 210, 120),
                tint: (0.95, 1.08, 1.02),
                brightness: 1.02,
                contrast: 1.05,
            },
            EnvDef {
                id: "mystic_forest",
                name: "Mystic Forest",
                files: &["mystic_forest.jpg"],
                accent: (60, 190, 140),
                tint: (0.90, 1.10, 0.95),
                brightness: 0.95,
                contrast: 1.10,
            },
            EnvDef {
                id: "gallery_studio",
                name: "Modern Gallery",
                files: &["gallery_studio.png"],
                accent: (220, 220, 230),
                tint: (1.0, 1.0, 1.0),
                brightness: 1.0,
                contrast: 1.05,
            },
        ];

        let env_dir = config::environments_dir();
        for cfg in configs {
            let mut loaded_img = None;
            for fn_str in cfg.files {
                let p = env_dir.join(fn_str);
                if p.exists() {
                    if let Ok(dyn_img) = image::open(&p) {
                        let rgb = dyn_img.to_rgb8();
                        if rgb.width() == self.width && rgb.height() == self.height {
                            loaded_img = Some(rgb);
                        } else {
                            let resized = image::imageops::resize(
                                &rgb,
                                self.width,
                                self.height,
                                image::imageops::FilterType::Triangle,
                            );
                            loaded_img = Some(resized);
                        }
                        break;
                    }
                }
            }

            let final_img = loaded_img.unwrap_or_else(|| {
                // Procedural gradient fallback
                let mut img = ImageBuffer::new(self.width, self.height);
                for y in 0..self.height {
                    let ty = y as f32 / self.height as f32;
                    let r = (cfg.accent.2 as f32 * ty * 0.4) as u8;
                    let g = (cfg.accent.1 as f32 * ty * 0.4) as u8;
                    let b = (cfg.accent.0 as f32 * ty * 0.4) as u8;
                    for x in 0..self.width {
                        img.put_pixel(x, y, Rgb([r, g, b]));
                    }
                }
                img
            });

            self.environments.push(Environment {
                id: cfg.id.to_string(),
                name: cfg.name.to_string(),
                accent_color_bgr: cfg.accent,
                ambient_tint_bgr: cfg.tint,
                brightness_multiplier: cfg.brightness,
                contrast_multiplier: cfg.contrast,
                image: final_img,
            });
        }
    }

    pub fn current(&self) -> &Environment {
        &self.environments[self.current_index]
    }

    pub fn next(&mut self) -> &Environment {
        self.current_index = (self.current_index + 1) % self.environments.len();
        self.current()
    }

    pub fn previous(&mut self) -> &Environment {
        if self.current_index == 0 {
            self.current_index = self.environments.len() - 1;
        } else {
            self.current_index -= 1;
        }
        self.current()
    }

    pub fn is_original_room(&self) -> bool {
        self.current_index == 0
    }

    pub fn get_lut(&mut self, env: &Environment) -> [[u8; 3]; 256] {
        if let Some(lut) = self.lut_cache.get(&env.id) {
            return *lut;
        }

        let tint = [
            env.ambient_tint_bgr.0,
            env.ambient_tint_bgr.1,
            env.ambient_tint_bgr.2,
        ];
        let intensity = config::COLOR_MATCH_INTENSITY;
        let mut eff_tint = [1.0f32; 3];
        for c in 0..3 {
            eff_tint[c] = (1.0 - intensity) + (tint[c] * intensity);
        }

        let mut lut = [[0u8; 3]; 256];
        for i in 0..256 {
            for c in 0..3 {
                let val = ((i as f32 * eff_tint[c]) - 128.0) * env.contrast_multiplier + 128.0;
                let scaled = (val * env.brightness_multiplier).clamp(0.0, 255.0);
                lut[i][c] = scaled as u8;
            }
        }

        self.lut_cache.insert(env.id.clone(), lut);
        lut
    }
}
