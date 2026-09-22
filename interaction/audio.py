"""
TimeSensei Procedural Audio Synthesizer
───────────────────────────────────────
Generates low-latency temporal audio effects procedurally using sounddevice and NumPy.
Requires zero external audio files. Gracefully disables if no audio device is available.
"""
import threading
import numpy as np
from config import settings

try:
    import sounddevice as sd
    _SD_AVAILABLE = True
except Exception:
    _SD_AVAILABLE = False


class TimeSenseiAudio:
    """Procedural audio engine for temporal interactions and ambient cues."""

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.enabled = settings.AUDIO_ENABLED and _SD_AVAILABLE
        self.volume = settings.AUDIO_VOLUME
        self._cache = {}
        if self.enabled:
            try:
                # Pre-synthesize core audio clips to avoid any synthesis latency during runtime
                self._pregenerate_clips()
            except Exception as e:
                print(f"[Audio] Audio initialization warning: {e}. Running in silent mode.")
                self.enabled = False

    def _pregenerate_clips(self):
        sr = self.sample_rate

        # 1. Rumble: Eerie intro sub-bass swell (65 Hz -> 40 Hz)
        t_rum = np.linspace(0, 0.8, int(sr * 0.8), endpoint=False)
        freq_rum = np.linspace(65, 38, len(t_rum))
        phase_rum = 2 * np.pi * np.cumsum(freq_rum) / sr
        env_rum = np.sin(np.pi * (t_rum / 0.8)) ** 1.5
        rumble = (np.sin(phase_rum) * 0.7 + np.sin(phase_rum * 2) * 0.3) * env_rum * 0.8
        self._cache["rumble"] = rumble.astype(np.float32)

        # 2. Scan: Vertical timeline locking resonance sweep (180 Hz -> 680 Hz)
        t_scan = np.linspace(0, 0.45, int(sr * 0.45), endpoint=False)
        freq_scan = np.geomspace(180, 680, len(t_scan))
        phase_scan = 2 * np.pi * np.cumsum(freq_scan) / sr
        env_scan = np.sin(np.pi * (t_scan / 0.45))
        scan = np.sin(phase_scan) * env_scan * 0.5
        self._cache["scan"] = scan.astype(np.float32)

        # 3. Freeze: Sharp temporal tick + sub impact drop
        t_frz = np.linspace(0, 0.35, int(sr * 0.35), endpoint=False)
        tick = np.sin(2 * np.pi * 950 * t_frz) * np.exp(-t_frz * 45) * 0.5
        sub = np.sin(2 * np.pi * 55 * t_frz) * np.exp(-t_frz * 9) * 0.7
        freeze = tick + sub
        self._cache["freeze"] = freeze.astype(np.float32)

        # 4. Rewind: Reverse tape pitch glide (700 Hz -> 200 Hz) with warble
        t_rew = np.linspace(0, 0.45, int(sr * 0.45), endpoint=False)
        freq_rew = np.geomspace(700, 200, len(t_rew))
        warble = 1.0 + 0.15 * np.sin(2 * np.pi * 18 * t_rew)
        phase_rew = 2 * np.pi * np.cumsum(freq_rew * warble) / sr
        env_rew = np.exp(-t_rew * 3.5)
        rewind = np.sin(phase_rew) * env_rew * 0.4
        self._cache["rewind"] = rewind.astype(np.float32)

        # 5. Punch: Heavy physical impact thud + crisp transient pop
        t_pnch = np.linspace(0, 0.28, int(sr * 0.28), endpoint=False)
        pop = np.sin(2 * np.pi * 580 * t_pnch) * np.exp(-t_pnch * 75) * 0.55
        bass_freq = np.linspace(125, 42, len(t_pnch))
        phase_bass = 2 * np.pi * np.cumsum(bass_freq) / sr
        bass = np.sin(phase_bass) * np.exp(-t_pnch * 14) * 0.75
        noise = (np.random.uniform(-1.0, 1.0, len(t_pnch))) * np.exp(-t_pnch * 35) * 0.25
        punch = pop + bass + noise
        self._cache["punch"] = punch.astype(np.float32)

        # 6. Fracture: Shatter noise burst + resonant crack
        t_frc = np.linspace(0, 0.40, int(sr * 0.40), endpoint=False)
        noise = (np.random.uniform(-1.0, 1.0, len(t_frc))) * np.exp(-t_frc * 18) * 0.4
        thud = np.sin(2 * np.pi * 75 * t_frc) * np.exp(-t_frc * 12) * 0.6
        crack = np.sin(2 * np.pi * 420 * t_frc) * np.exp(-t_frc * 30) * 0.3
        fracture = noise + thud + crack
        self._cache["fracture"] = fracture.astype(np.float32)

        # 7. Shutter: Dual metallic camera click
        t_sht = np.linspace(0, 0.18, int(sr * 0.18), endpoint=False)
        click1 = np.sin(2 * np.pi * 1200 * t_sht) * np.exp(-t_sht * 90) * 0.5
        offset = int(sr * 0.06)
        click2 = np.zeros_like(t_sht)
        if offset < len(t_sht):
            t_rem = t_sht[offset:]
            click2[offset:] = np.sin(2 * np.pi * 900 * (t_rem - t_sht[offset])) * np.exp(-(t_rem - t_sht[offset]) * 80) * 0.6
        shutter = click1 + click2
        self._cache["shutter"] = shutter.astype(np.float32)

        # 8. Drop: Soft floor contact thud
        t_drp = np.linspace(0, 0.22, int(sr * 0.22), endpoint=False)
        drop = np.sin(2 * np.pi * 65 * t_drp) * np.exp(-t_drp * 18) * 0.5
        self._cache["drop"] = drop.astype(np.float32)

        # 9. Countdown Beeps (Photobooth countdown audio cues)
        t_bp = np.linspace(0, 0.12, int(sr * 0.12), endpoint=False)
        beep_low = np.sin(2 * np.pi * 780 * t_bp) * np.exp(-t_bp * 28) * 0.45
        beep_high = (np.sin(2 * np.pi * 1560 * t_bp) + 0.3 * np.sin(2 * np.pi * 2340 * t_bp)) * np.exp(-t_bp * 25) * 0.55
        self._cache["beep_low"] = beep_low.astype(np.float32)
        self._cache["beep_high"] = beep_high.astype(np.float32)

        # 10. Whoosh / Timeline Slide
        t_wh = np.linspace(0, 0.28, int(sr * 0.28), endpoint=False)
        noise_wh = np.random.uniform(-1.0, 1.0, len(t_wh))
        env_wh = np.sin(np.pi * (t_wh / 0.28)) ** 2
        f_glide = np.linspace(350, 750, len(t_wh))
        tone_wh = np.sin(2 * np.pi * np.cumsum(f_glide) / sr) * 0.35
        whoosh = (noise_wh * 0.35 + tone_wh) * env_wh * 0.5
        self._cache["whoosh"] = whoosh.astype(np.float32)

    def _play_raw(self, audio_data: np.ndarray):
        if not self.enabled:
            return

        def _worker():
            try:
                scaled = audio_data * float(self.volume)
                sd.play(scaled, self.sample_rate, blocking=False)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def play_rumble(self):
        clip = self._cache.get("rumble")
        if clip is not None:
            self._play_raw(clip)

    def play_scan(self):
        clip = self._cache.get("scan")
        if clip is not None:
            self._play_raw(clip)

    def play_freeze(self):
        clip = self._cache.get("freeze")
        if clip is not None:
            self._play_raw(clip)

    def play_rewind(self):
        clip = self._cache.get("rewind")
        if clip is not None:
            self._play_raw(clip)

    def play_punch(self):
        clip = self._cache.get("punch")
        if clip is not None:
            self._play_raw(clip)

    def play_fracture(self):
        # Fractures now play the punch impact
        clip = self._cache.get("punch") or self._cache.get("fracture")
        if clip is not None:
            self._play_raw(clip)

    def play_shutter(self):
        clip = self._cache.get("shutter")
        if clip is not None:
            self._play_raw(clip)

    def play_countdown_beep(self, num: int):
        """Crisp countdown beep (high-pitch chime on 1, solid beep on 3 and 2)."""
        clip = self._cache.get("beep_high" if num <= 1 else "beep_low")
        if clip is not None:
            self._play_raw(clip)

    def play_whoosh(self):
        """Whoosh sound for background timeline transition."""
        clip = self._cache.get("whoosh")
        if clip is not None:
            self._play_raw(clip)

    def play_drop(self):
        clip = self._cache.get("drop")
        if clip is not None:
            self._play_raw(clip)

    def toggle_mute(self) -> bool:
        """Toggles audio mute state. Returns new muted boolean."""
        self.enabled = not self.enabled
        return not self.enabled
