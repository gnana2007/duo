"""
TimeSensei — CONTROL YOUR TIMELINE
───────────────────────────────────
Real-time gesture-controlled temporal installation.
Allows visitors to freeze versions of themselves in time, create temporal echoes,
physically combat past selves with timeline fracture, rewind recent movement,
switch realities, and receive photos via instant QR sharing.

States:
  BOOT -> ATTRACT -> ENTERING -> LIVE -> COUNTDOWN -> FLASH -> (SHARE) -> RESETTING
"""
import sys
import time
import os
import cv2
import numpy as np
from datetime import datetime

from config import settings
from camera.capture import CameraStream
from vision.segmentation import PersonSegmenter
from vision.pose import PoseTracker
from vision.hands import HandTracker
from vision.motion import MotionTracker
from vision.models_manager import ensure_model
from world.environments import EnvironmentManager
from world.scene import Scene
from interaction.memories import MemoryManager
from interaction.reactions import InteractionDetector
from interaction.gestures import GestureManager
from interaction.mirror_modes import PersonalityModeManager
from interaction.rewind import RewindBuffer
from interaction.audio import TimeSenseiAudio
from rendering.compositor import NaturalCompositor
from rendering.ui import UIRenderer
from rendering.intro import IntroRenderer
from sharing.server import start_sharing_server
from capture.qr import QRCodeGenerator, get_local_ip


def _startup_preflight() -> bool:
    """Preflight check: verifies essential models, directories, and assets."""
    print("=" * 64)
    print("           TimeSensei — CONTROL YOUR TIMELINE")
    print("=" * 64)
    print("[Preflight] Verifying runtime dependencies and vision models...")

    models = [
        "selfie_segmenter.tflite",
        "gesture_recognizer.task",
        "pose_landmarker_lite.task"
    ]
    all_ok = True
    for m in models:
        path = ensure_model(m)
        if path and os.path.exists(path) and os.path.getsize(path) > 1000:
            print(f"  • Model {m}: OK ({os.path.getsize(path) / 1024:.1f} KB)")
        else:
            print(f"  • Model {m}: FAILED / MISSING")
            all_ok = False

    settings.CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
    settings.ENVIRONMENTS_DIR.mkdir(parents=True, exist_ok=True)
    print("[Preflight] Storage directories verified.")
    return all_ok


def _capture_clean_background(camera: CameraStream, num_frames: int) -> np.ndarray:
    """Captures and averages frames for clean room reference."""
    print(f"[Main] Calibrating reality space ({num_frames} frames)...")
    accum = None
    count = 0
    for _ in range(num_frames + 8):
        ret, frame = camera.read()
        if not ret or frame is None:
            continue
        if count >= 8:
            if accum is None:
                accum = frame.astype(np.float64)
            else:
                accum += frame.astype(np.float64)
        count += 1
        if count >= num_frames + 8:
            break
        time.sleep(0.02)
    if accum is not None:
        bg = (accum / max(1, num_frames)).astype(np.uint8)
        print("[Main] Reality baseline calibrated.")
        return bg
    print("[Main] Baseline unavailable, using dark canvas.")
    return np.zeros((settings.CAPTURE_HEIGHT, settings.CAPTURE_WIDTH, 3), dtype=np.uint8)


def _is_person_in_capture_zone(mask: np.ndarray) -> bool:
    h, w = mask.shape[:2]
    zx = int(w * settings.CAPTURE_ZONE_X_RATIO)
    zy = int(h * settings.CAPTURE_ZONE_Y_RATIO)
    zw = int(w * settings.CAPTURE_ZONE_W_RATIO)
    zh = int(h * settings.CAPTURE_ZONE_H_RATIO)
    zone_mask = mask[zy:zy+zh, zx:zx+zw]
    return float(np.sum(zone_mask > 0.30)) > (zw * zh * 0.08)


def main():
    # ── 1. Startup Preflight ──
    preflight_ok = _startup_preflight()
    if not preflight_ok:
        print("[Main] Preflight notice: Some models could not be verified.")

    # ── 2. Audio Engine ──
    audio = TimeSenseiAudio()

    # ── 3. Mobile Sharing Daemon ──
    start_sharing_server()
    local_lan_ip = get_local_ip()

    # ── 4. Camera Stream ──
    print("[Main] Opening camera stream...")
    camera = CameraStream().start()

    # ── 5. Baseline Calibration ──
    clean_bg = _capture_clean_background(camera, settings.BG_CAPTURE_FRAMES)

    # ── 6. Vision Engines ──
    print("[Main] Pre-warming temporal vision models...")
    segmenter = PersonSegmenter()
    pose_tracker = PoseTracker(num_poses=2)
    hand_tracker = HandTracker(num_hands=4)
    motion_tracker = MotionTracker()

    # ── 7. World & Timelines ──
    env_manager = EnvironmentManager()
    env_manager.set_original_room(clean_bg)
    scene = Scene(env_manager)

    # ── 8. Temporal Interaction & Memory Systems ──
    memory_mgr = MemoryManager()
    interaction_detector = InteractionDetector(audio=audio)
    gesture_mgr = GestureManager()
    mode_mgr = PersonalityModeManager()
    rewind_buf = RewindBuffer(audio=audio)

    # ── 9. Renderers & UI ──
    compositor = NaturalCompositor()
    ui = UIRenderer()
    intro = IntroRenderer()
    qr_gen = QRCodeGenerator()

    # ── 10. Display Window & Mouse Callback ──
    cv2.namedWindow(settings.WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(settings.WINDOW_NAME, settings.CAPTURE_WIDTH, settings.CAPTURE_HEIGHT)

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            intro.check_mouse_click(x, y)

    cv2.setMouseCallback(settings.WINDOW_NAME, on_mouse)

    # ── Runtime State Variables ──
    app_state = settings.STATE_ATTRACT
    state_start_time = time.time()
    entering_start_time = 0.0
    countdown_start = 0.0
    flash_start = 0.0
    capture_success_time = 0.0

    last_person_seen_time = time.time()
    camera_fail_count = 0
    show_diagnostics = settings.SHOW_DIAGNOSTICS_DEFAULT

    last_photo_path = None
    last_qr_image = None
    show_qr = False

    cached_mask = np.zeros((settings.CAPTURE_HEIGHT, settings.CAPTURE_WIDTH), dtype=np.float32)
    cached_shadow = np.zeros_like(cached_mask)
    cached_hands = []
    cached_poses = []
    frame_idx = 0
    prev_time = time.time()
    fps = 30.0

    print()
    print("[TimeSensei] System ready. Entering ATTRACT mode.")
    print("             CONTROL YOUR TIMELINE")
    print()

    try:
        while True:
            t0 = time.time()

            ret, frame = camera.read()
            if not ret or frame is None:
                camera_fail_count += 1
                if camera_fail_count > settings.CAMERA_RETRY_COUNT:
                    app_state = settings.STATE_ERROR_RECOVERY
                time.sleep(0.01)
                continue
            else:
                camera_fail_count = 0
                if app_state == settings.STATE_ERROR_RECOVERY:
                    app_state = settings.STATE_ATTRACT

            dt = t0 - prev_time
            prev_time = t0
            if dt > 0:
                fps = 0.90 * fps + 0.10 * (1.0 / dt)

            now = time.time()

            # ── STAGGERED VISION PIPELINE ──
            if frame_idx % settings.SEG_EVERY_N == 0:
                cached_mask = segmenter.compute_mask(frame)
                cached_shadow = segmenter.generate_contact_shadow(cached_mask)
            if frame_idx % settings.HAND_EVERY_N == 0:
                cached_hands = hand_tracker.track(frame)
            if frame_idx % settings.POSE_EVERY_N == settings.POSE_OFFSET:
                cached_poses = pose_tracker.track(frame)
            frame_idx = (frame_idx + 1) % 120

            person_in_zone = _is_person_in_capture_zone(cached_mask)
            has_person = np.sum(cached_mask > 0.35) > 1500

            if has_person:
                last_person_seen_time = now

            # ────────────────────────────────────────────────────────
            # STATE: ATTRACT (Eerie Halloween-Inspired Intro)
            # ────────────────────────────────────────────────────────
            if app_state == settings.STATE_ATTRACT:
                display, start_triggered = intro.render_attract(frame, cached_hands)

                if start_triggered:
                    audio.play_rumble()
                    app_state = settings.STATE_ENTERING
                    entering_start_time = now
                    audio.play_scan()

            # ────────────────────────────────────────────────────────
            # STATE: ENTERING (Scanning Laser Transition)
            # ────────────────────────────────────────────────────────
            elif app_state == settings.STATE_ENTERING:
                elapsed_enter = now - entering_start_time
                progress = min(1.0, elapsed_enter / settings.INTRO_SCAN_DURATION_S)
                display = intro.render_entering(frame, progress)

                if elapsed_enter >= settings.INTRO_SCAN_DURATION_S:
                    app_state = settings.STATE_LIVE
                    ui.reset_tutorial()

            # ────────────────────────────────────────────────────────
            # STATE: LIVE / COUNTDOWN / FLASH
            # ────────────────────────────────────────────────────────
            elif app_state in (settings.STATE_LIVE, settings.STATE_COUNTDOWN, settings.STATE_FLASH):
                # Inactivity watchdog: Auto-reset to ATTRACT if empty room for IDLE_TIMEOUT_S
                if now - last_person_seen_time > settings.IDLE_TIMEOUT_S:
                    memory_mgr.clear_all()
                    ui.reset_tutorial()
                    show_qr = False
                    app_state = settings.STATE_ATTRACT
                    continue

                # Record foreground into Rewind ring buffer
                rewind_buf.record_frame(frame, cached_mask)

                # Build Base Display (Active Timeline)
                env = scene.current_environment()
                if scene.is_original_room():
                    display = frame.copy()
                else:
                    bg = scene.get_background()
                    display = compositor.composite(frame, bg, cached_mask, cached_shadow, env)

                # Apply Active Temporal Mode (Echo, Paradox, Rift, Anomaly)
                display = mode_mgr.process_frame(display, cached_mask, cached_hands, cached_poses)

                # Render Frozen Temporal Clones
                memory_mgr.update_all()
                memory_mgr.render_all(display, env.ambient_tint_bgr)

                # ── LIVE INTERACTIONS ──
                if app_state == settings.STATE_LIVE:
                    # Timeline navigation via fast single-palm swipe
                    swipe = motion_tracker.update(cached_hands)
                    if swipe != 0:
                        scene.trigger_swipe(swipe)

                    # QR Popup toggle: Fist dismisses, Thumb opens
                    if last_qr_image is not None:
                        if gesture_mgr.check_fist(cached_hands):
                            show_qr = False
                        elif gesture_mgr.check_thumb_trigger(cached_hands):
                            show_qr = True

                    # ✌️ Signature Gesture: Two-Finger Victory Hold -> FREEZE TIME
                    freeze_trig, freeze_prog, victory_pos = gesture_mgr.check_victory_freeze(cached_hands, qr_active=show_qr)
                    if freeze_prog > 0.05 and victory_pos:
                        ui.draw_victory_freeze_progress(display, victory_pos, freeze_prog)

                    if freeze_trig and person_in_zone:
                        new_mem = memory_mgr.create_memory(frame, cached_mask)
                        if new_mem:
                            audio.play_freeze()
                            # Re-render clone onto display
                            memory_mgr.render_all(display, env.ambient_tint_bgr)
                            capture_success_time = now

                    # Photo Countdown Trigger (Thumbs-Up or P key)
                    if gesture_mgr.check_capture_trigger(cached_hands):
                        app_state = settings.STATE_COUNTDOWN
                        countdown_start = now

                    # ☝️ Pointing Up -> Trigger Rewind
                    if gesture_mgr.check_rewind_trigger(cached_hands):
                        rewind_buf.trigger_rewind()

                    # Handle active rewind playback overlay
                    is_rewinding, rewind_display = rewind_buf.update_and_render(display, frame if scene.is_original_room() else scene.get_background())
                    if is_rewinding:
                        display = rewind_display

                # ── COUNTDOWN PHASE ──
                elif app_state == settings.STATE_COUNTDOWN:
                    remaining = settings.COUNTDOWN_SECONDS - (now - countdown_start)
                    if remaining <= 0:
                        # Capture Photo with subtle TimeSensei watermark
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        photo_id = f"capture_{ts}"
                        path = settings.CAPTURES_DIR / f"{photo_id}.jpg"

                        watermarked = ui.apply_watermark(display)
                        cv2.imwrite(str(path), watermarked)
                        last_photo_path = str(path)
                        last_qr_image = qr_gen.generate_qr_image(photo_id)

                        audio.play_shutter()
                        app_state = settings.STATE_FLASH
                        flash_start = now
                        show_qr = False
                    else:
                        ui.draw_countdown(display, remaining, settings.COUNTDOWN_SECONDS)

                # ── FLASH PHASE ──
                elif app_state == settings.STATE_FLASH:
                    elapsed = now - flash_start
                    if elapsed < settings.FLASH_DURATION_S:
                        intensity = max(0.0, 0.85 * (1.0 - elapsed / settings.FLASH_DURATION_S))
                        ui.draw_flash(display, intensity)
                    else:
                        app_state = settings.STATE_LIVE

                # ── UI Overlays ──
                if app_state in (settings.STATE_LIVE, settings.STATE_COUNTDOWN):
                    ui.draw_capture_zone(display, person_in_zone)

                ui.draw_hud(
                    display,
                    timeline_name=env.name,
                    timeline_accent=env.accent_color_bgr,
                    memory_count=len(memory_mgr.memories),
                    mode_name=mode_mgr.current_mode,
                    fps=fps,
                    grabbed=memory_mgr.grabbed_memory is not None,
                )

                # Micro-tutorial for first-time visitors
                ui.draw_micro_tutorial(display, has_person, len(memory_mgr.memories))

                # Capture success banner
                if capture_success_time > 0 and (now - capture_success_time) < 3.0:
                    ui.draw_capture_success(display)

                # QR Sharing Popup (revealed by 👍, hidden by ✊)
                if last_qr_image is not None and show_qr:
                    ui.draw_qr_popup(display, last_qr_image)

            # ────────────────────────────────────────────────────────
            # STATE: ERROR_RECOVERY (Camera reconnection)
            # ────────────────────────────────────────────────────────
            elif app_state == settings.STATE_ERROR_RECOVERY:
                display = np.zeros((settings.CAPTURE_HEIGHT, settings.CAPTURE_WIDTH, 3), dtype=np.uint8)
                cv2.putText(display, "RECALIBRATING TIMELINE...", (settings.CAPTURE_WIDTH // 2 - 220, settings.CAPTURE_HEIGHT // 2),
                            cv2.FONT_HERSHEY_DUPLEX, 0.9, (0, 80, 255), 2, cv2.LINE_AA)
                time.sleep(settings.CAMERA_RETRY_DELAY_S)
                camera.release()
                camera = CameraStream().start()

            # ── Developer Diagnostics Overlay (D Key) ──
            if show_diagnostics:
                stats = {
                    "fps": fps,
                    "num_persons": len(cached_poses),
                    "num_hands": len(cached_hands),
                    "memory_count": len(memory_mgr.memories),
                    "mode": mode_mgr.current_mode,
                    "audio_enabled": audio.enabled,
                    "app_state": app_state,
                    "lan_ip": local_lan_ip,
                }
                ui.draw_diagnostics(display, stats)

            # ── Display Frame ──
            cv2.imshow(settings.WINDOW_NAME, display)

            # ── Operator Keyboard Shortcuts ──
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), ord('Q'), 27):  # ESC or Q -> Exit
                break
            elif key in (13, 32):  # ENTER or SPACE
                if app_state == settings.STATE_ATTRACT:
                    audio.play_rumble()
                    app_state = settings.STATE_ENTERING
                    entering_start_time = time.time()
                    audio.play_scan()
                elif app_state == settings.STATE_LIVE:
                    app_state = settings.STATE_COUNTDOWN
                    countdown_start = time.time()
            elif key in (ord('r'), ord('R')):  # R -> Reset whole session to ATTRACT
                memory_mgr.clear_all()
                ui.reset_tutorial()
                show_qr = False
                app_state = settings.STATE_ATTRACT
            elif key in (ord('f'), ord('F')) and app_state == settings.STATE_LIVE:  # F -> Force freeze
                new_mem = memory_mgr.create_memory(frame, cached_mask)
                if new_mem:
                    audio.play_freeze()
                    capture_success_time = time.time()
            elif key in (ord('w'), ord('W')) and app_state == settings.STATE_LIVE:  # W -> Rewind
                rewind_buf.trigger_rewind()
            elif key in (ord('e'), ord('E')) and app_state == settings.STATE_LIVE:  # E -> Toggle Echo
                mode_mgr.toggle_echo()
            elif key in (ord('m'), ord('M')):  # M -> Cycle mode or mute
                mode_mgr.cycle_mode()
            elif key in (ord('c'), ord('C')) and app_state == settings.STATE_LIVE:  # C -> Clear clones
                memory_mgr.clear_all()
            elif key in (ord('d'), ord('D')):  # D -> Diagnostics
                show_diagnostics = not show_diagnostics
            elif key in (ord('t'), ord('T')):  # T -> Show QR
                show_qr = True
            elif key in (ord('p'), ord('P')) and app_state == settings.STATE_LIVE:  # P -> Trigger photo
                app_state = settings.STATE_COUNTDOWN
                countdown_start = time.time()
            elif key in (81, 2, ord('a'), ord('A')):  # Left Arrow -> Previous Timeline
                scene.trigger_swipe(-1)
            elif key in (83, 3, ord('s'), ord('S')):  # Right Arrow -> Next Timeline
                scene.trigger_swipe(1)

    except KeyboardInterrupt:
        print("\n[Main] Terminating TimeSensei gracefully...")
    finally:
        camera.release()
        cv2.destroyAllWindows()
        print(f"[Main] TimeSensei session closed. Photos archived at: {settings.CAPTURES_DIR}")


if __name__ == "__main__":
    main()
