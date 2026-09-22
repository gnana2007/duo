"""
Interactive Memory Wall — Main Loop v3.2
────────────────────────────────────────
1. Captures clean background at startup
2. Shows capture zone for full-body positioning
3. Peace sign → countdown → frozen memory at exact position
4. Memories firmly grounded to floor plane (zero floating, soft ground contact shadow)
5. Grab memories with fist, drag, drop to reposition (snapped to floor)
6. Punch/kick/tickle/touch reactions
7. Left hand x3 → prev env, Right hand x3 → next env
8. QR sharing: 👍 Thumb shows QR popup at bottom-right, ✊ Fist hides QR
9. No frame/memory numbers displayed
"""
import sys
import time
import cv2
import numpy as np
from datetime import datetime

from config import settings
from camera.capture import CameraStream
from vision.segmentation import PersonSegmenter
from vision.pose import PoseTracker
from vision.hands import HandTracker
from vision.motion import MotionTracker
from world.environments import EnvironmentManager
from world.scene import Scene
from interaction.memories import MemoryManager
from interaction.reactions import InteractionDetector
from interaction.gestures import GestureManager
from rendering.compositor import NaturalCompositor
from rendering.ui import UIRenderer
from sharing.server import start_sharing_server
from capture.qr import QRCodeGenerator


STATE_LIVE = "LIVE"
STATE_COUNTDOWN = "COUNTDOWN"
STATE_FLASH = "FLASH"


def _capture_clean_background(camera: CameraStream, num_frames: int) -> np.ndarray:
    """Average several frames to get a clean, stable background."""
    print(f"[Main] Capturing clean background ({num_frames} frames)...")
    print("[Main] Please step away from the camera for 3 seconds.")
    accum = None
    count = 0
    for _ in range(num_frames + 10):
        ret, frame = camera.read()
        if not ret or frame is None:
            continue
        if count >= 10:
            if accum is None:
                accum = frame.astype(np.float64)
            else:
                accum += frame.astype(np.float64)
        count += 1
        if count >= num_frames + 10:
            break
        time.sleep(0.03)
    if accum is not None:
        bg = (accum / max(1, num_frames)).astype(np.uint8)
        print("[Main] Background captured successfully.")
        return bg
    print("[Main] WARNING: Could not capture background, using black.")
    return np.zeros((settings.CAPTURE_HEIGHT, settings.CAPTURE_WIDTH, 3), dtype=np.uint8)


def _is_person_in_capture_zone(mask: np.ndarray) -> bool:
    h, w = mask.shape[:2]
    zx = int(w * settings.CAPTURE_ZONE_X_RATIO)
    zy = int(h * settings.CAPTURE_ZONE_Y_RATIO)
    zw = int(w * settings.CAPTURE_ZONE_W_RATIO)
    zh = int(h * settings.CAPTURE_ZONE_H_RATIO)
    zone_mask = mask[zy:zy+zh, zx:zx+zw]
    person_pixels = np.sum(zone_mask > 0.3)
    return person_pixels > (zw * zh * 0.08)


def main():
    print("=" * 62)
    print("   INTERACTIVE MEMORY WALL v3.2")
    print("=" * 62)

    # ── Sharing server ──
    start_sharing_server()

    # ── Camera ──
    print("[Main] Starting camera...")
    camera = CameraStream().start()

    # ── Clean background ──
    clean_bg = _capture_clean_background(camera, settings.BG_CAPTURE_FRAMES)

    # ── Vision models ──
    print("[Main] Loading vision models...")
    segmenter = PersonSegmenter()
    pose_tracker = PoseTracker(num_poses=2)
    hand_tracker = HandTracker(num_hands=4)
    motion_tracker = MotionTracker()

    # ── World & Scene ──
    print("[Main] Setting up environments...")
    env_manager = EnvironmentManager()
    env_manager.set_original_room(clean_bg)
    scene = Scene(env_manager)

    # ── Memory system ──
    memory_mgr = MemoryManager()
    interaction_detector = InteractionDetector()
    gesture_mgr = GestureManager()

    # ── QR ──
    qr_gen = QRCodeGenerator()

    # ── Renderers ──
    compositor = NaturalCompositor()
    ui = UIRenderer()

    # ── Display window ──
    cv2.namedWindow(settings.WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(settings.WINDOW_NAME, settings.CAPTURE_WIDTH, settings.CAPTURE_HEIGHT)

    # ── Cached vision results ──
    cached_mask = np.zeros((settings.CAPTURE_HEIGHT, settings.CAPTURE_WIDTH), dtype=np.float32)
    cached_shadow = np.zeros_like(cached_mask)
    cached_hands = []
    cached_poses = []
    frame_idx = 0
    prev_time = time.time()
    fps = 30.0

    # ── Capture state ──
    state = STATE_LIVE
    countdown_start = 0.0
    flash_start = 0.0
    capture_success_time = 0.0
    last_photo_path = None
    last_qr_image = None
    show_qr = False

    print()
    print("[Main] Memory Wall is ready!")
    print("[Main]   ✌️  Peace sign  = Capture photo")
    print("[Main]   👍 Thumb Up    = Show QR popup (bottom-right)")
    print("[Main]   ✊ Closed Fist = Hide QR popup / Grab & move memory")
    print("[Main]   Swipe x3       = Switch virtual worlds")
    print("[Main]   Keyboard: C=Capture | T=Show QR | F=Hide QR | Q=Quit")
    print()

    try:
        while True:
            t0 = time.time()

            ret, frame = camera.read()
            if not ret or frame is None:
                time.sleep(0.005)
                continue

            dt = t0 - prev_time
            prev_time = t0
            if dt > 0:
                fps = 0.90 * fps + 0.10 * (1.0 / dt)

            # ── STAGGERED VISION ──
            if frame_idx % settings.SEG_EVERY_N == 0:
                cached_mask = segmenter.compute_mask(frame)
                cached_shadow = segmenter.generate_contact_shadow(cached_mask)
            if frame_idx % settings.HAND_EVERY_N == 0:
                cached_hands = hand_tracker.track(frame)
            if frame_idx % settings.POSE_EVERY_N == settings.POSE_OFFSET:
                cached_poses = pose_tracker.track(frame)
            frame_idx = (frame_idx + 1) % 120

            person_in_zone = _is_person_in_capture_zone(cached_mask)

            # ── BUILD DISPLAY ──
            env = scene.current_environment()
            if scene.is_original_room():
                display = frame.copy()
            else:
                bg = scene.get_background()
                display = compositor.composite(frame, bg, cached_mask, cached_shadow, env)

            # ── Render frozen memories ──
            memory_mgr.update_all()
            memory_mgr.render_all(display, env.ambient_tint_bgr)

            # ── INTERACTIONS ──
            now = time.time()

            if state == STATE_LIVE:
                if len(memory_mgr.memories) > 0:
                    interaction_detector.update(memory_mgr, cached_hands, cached_poses)

                # Triple-swipe env switch
                swipe = motion_tracker.update(cached_hands)
                if swipe != 0:
                    scene.trigger_swipe(swipe)

                # ── QR popup toggle: ✊ Fist completely hides QR, 👍 Thumb shows QR ──
                if last_qr_image is not None:
                    if gesture_mgr.check_fist(cached_hands):
                        show_qr = False
                    elif gesture_mgr.check_thumb_trigger(cached_hands):
                        show_qr = True

                # Peace sign → capture
                if gesture_mgr.check_capture_trigger(cached_hands):
                    state = STATE_COUNTDOWN
                    countdown_start = now

            # ── CAPTURE STATE MACHINE ──
            if state == STATE_COUNTDOWN:
                remaining = settings.COUNTDOWN_SECONDS - (now - countdown_start)
                if remaining <= 0:
                    # CAPTURE — create memory grounded to floor, then save full composited frame
                    memory = memory_mgr.create_memory(frame, cached_mask)
                    if memory:
                        capture_success_time = now
                        # Re-render display with the new memory included
                        memory_mgr.render_all(display, env.ambient_tint_bgr)
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        photo_id = f"memory_{ts}"
                        path = settings.CAPTURES_DIR / f"{photo_id}.jpg"
                        # Save the FULL composited frame (all memories + env + user)
                        cv2.imwrite(str(path), display)
                        last_photo_path = str(path)
                        # Generate QR code ready to be summoned by thumb 👍
                        last_qr_image = qr_gen.generate_qr_image(photo_id)
                        # Do not force QR on screen — wait for thumb 👍 gesture
                        show_qr = False
                    state = STATE_FLASH
                    flash_start = now
                else:
                    ui.draw_countdown(display, remaining, settings.COUNTDOWN_SECONDS)

            elif state == STATE_FLASH:
                elapsed = now - flash_start
                if elapsed < settings.FLASH_DURATION_S:
                    intensity = max(0, 0.85 * (1.0 - elapsed / settings.FLASH_DURATION_S))
                    ui.draw_flash(display, intensity)
                else:
                    state = STATE_LIVE

            # ── UI OVERLAYS ──
            if state in (STATE_LIVE, STATE_COUNTDOWN):
                ui.draw_capture_zone(display, person_in_zone)

            ui.draw_hud(
                display,
                env_name=env.name,
                env_accent=env.accent_color_bgr,
                memory_count=len(memory_mgr.memories),
                fps=fps,
                person_in_zone=person_in_zone,
                grabbed=memory_mgr.grabbed_memory is not None,
            )

            # Banner on capture (no frame numbers)
            if capture_success_time > 0 and (now - capture_success_time) < 3.0:
                ui.draw_capture_success(display)

            # ── QR popup at bottom-right (shown when 👍 thumb is shown, hidden when ✊ fist is shown) ──
            if last_qr_image is not None and show_qr:
                ui.draw_qr_popup(display, last_qr_image)

            # ── DISPLAY ──
            cv2.imshow(settings.WINDOW_NAME, display)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), ord('Q'), 27):
                break
            if key in (ord('c'), ord('C')) and state == STATE_LIVE:
                state = STATE_COUNTDOWN
                countdown_start = time.time()
            elif key in (ord('t'), ord('T')):
                show_qr = True
            elif key in (ord('f'), ord('F')):
                show_qr = False
                gesture_mgr.last_fist_time = time.time()

    except KeyboardInterrupt:
        print("\n[Main] Interrupted.")
    finally:
        camera.release()
        cv2.destroyAllWindows()
        print(f"[Main] Session closed. {len(memory_mgr.memories)} memories created.")
        if last_photo_path:
            print(f"[Main] Photos saved to: {settings.CAPTURES_DIR}")


if __name__ == "__main__":
    main()
