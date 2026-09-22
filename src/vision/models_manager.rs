// Vision Models Manager
// Matches vision/models_manager.py.

use std::path::PathBuf;
use crate::config;

pub fn ensure_model(model_name: &str) -> Option<PathBuf> {
    let p = config::models_dir().join(model_name);
    if p.exists() {
        Some(p)
    } else {
        None
    }
}
