// Personality Modes & Temporal Echo
// Matches interaction/mirror_modes.py.

pub struct PersonalityModeManager {
    pub current_mode: String,
    pub echo_enabled: bool,
    modes: Vec<&'static str>,
    mode_idx: usize,
}

impl PersonalityModeManager {
    pub fn new() -> Self {
        Self {
            current_mode: "PRESENT".to_string(),
            echo_enabled: false,
            modes: vec!["PRESENT", "ECHO", "PARADOX", "RIFT", "ANOMALY"],
            mode_idx: 0,
        }
    }

    pub fn cycle_mode(&mut self) -> &str {
        self.mode_idx = (self.mode_idx + 1) % self.modes.len();
        self.current_mode = self.modes[self.mode_idx].to_string();
        self.modes[self.mode_idx]
    }

    pub fn toggle_echo(&mut self) -> bool {
        self.echo_enabled = !self.echo_enabled;
        self.echo_enabled
    }
}
