# TimeSensei ⏳✨

> **CONTROL YOUR TIMELINE**

**TimeSensei** is a real-time, gesture-controlled interactive temporal installation built with **Python, OpenCV, MediaPipe, and Flask**. Visitors become masters of time: freezing versions of themselves in physical space, creating temporal echoes, physically combating their past clones to fracture the timeline, rewinding recent motion backward through time, traveling across realities, and instantly taking home their temporal captures via local QR-code mobile sharing to WhatsApp.

---

## 🌟 Flagship Interactions & Capabilities

1. **Cinematic Eerie Startup Experience**:
   - The camera opens behind an eerie, dark charcoal and dried-blood crimson aesthetic with subtle film grain, dust scratches, and slow-drifting fog.
   - Large stylized title: **TimeSensei** (*CONTROL YOUR TIMELINE*).
   - Interactive `[ ENTER THE TIMELINE ]` button activated via:
     - **Open Palm Dwell / Hover** for 1.1s
     - **Mouse Click**
     - **SPACE / ENTER** keyboard fallback
   - Luminous vertical scanning laser passes over the visitor with `TIMELINE LOCKED` transition.

2. **Open Palm Hold → Freeze Time**:
   - Holding an open palm for **700–900 ms** triggers **FREEZE TIME**.
   - A temporal ring fills clockwise around the visitor's hand.
   - The visitor's current body is frozen as a persistent temporal clone **anchored to the floor plane** (zero floating in mid-air).
   - Generates realistic ground-contact shadows beneath feet.
   - Visitors can physically walk away while their clone remains standing in place!

3. **Physical Combat & Elastic Recoil**:
   - Live visitors can physically punch (closed fist) or kick (swing ankle) their frozen clones:
     - Inflicts punchy physical displacement, rotational recoil, and impact shockwaves.
     - Smooth spring-damper physics naturally bounces the clone back to its resting stance.
     - The clone remains 100% intact and grounded (no breaking/shattering into shards).
     - Plays procedural impact sound effects and displays floating combat banners.

4. **Fist Grab, Drag & Floor Drop**:
   - Move a closed fist near any clone to reveal a targeting aura.
   - Holding a fist grabs the clone; dragging moves it smoothly with exponential moving average (EMA) anti-jitter smoothing.
   - Releasing the fist snaps the clone down to the floor plane and spawns a concentric floor contact wave.

5. **Real-Time Temporal Rewind**:
   - Maintains a circular ring buffer of the visitor's recent movement over the last **3.0 seconds** sampled at 12 FPS.
   - Triggered via **Pointing Up** gesture or **`W`** key:
   - Live video freezes and dims while the visitor's previous positions replay backward with reverse time scanlines, cyan chromatic ghosting, and `<< REWINDING TIME` progress bar before dissolving smoothly back to live reality.

6. **Temporal Echo Mode**:
   - Replaces ordinary reflection with **4 separated delayed past copies** (spaced at ~180 ms, 360 ms, 540 ms, 720 ms).
   - Each older echo is progressively more transparent and desaturated, creating distinct temporal trails.

7. **Virtual Timelines**:
   - **Haunted Timeline**: Atmospheric cobblestone room with candle flames, fog, and mystery.
   - **Cosmic Deep Space**: Nebula clouds, orbital observation deck, and distant ringed planets.
   - **Zen Sanctuary**: Warm ambient light, wooden architecture, and tranquil atmosphere.
   - **Holo Arena**: Laser spotlights, perspective floor grid, and energy targets.
   - **Present Reality**: The visitor's physical room with all virtual elements composited.
   - Switch Timelines via **Triple-Swipe Left/Right** or **Arrow Keys**.

8. **Temporal Capture & QR Mobile Sharing**:
   - Hold a **Peace / Victory (`V`)** sign to trigger a 3-second countdown.
   - Full composited photo saved with subtle `TimeSensei // CONTROL YOUR TIMELINE` watermark.
   - Show a **Thumbs-Up (`👍`)** to summon the on-screen QR code card.
   - Show a **Closed Fist (`✊`)** to dismiss the card.
   - Scanning the QR opens a dark glassmorphic mobile page on any phone connected to local Wi-Fi with **1-Tap Save to Photos** and **Direct Share to WhatsApp**.

---

## 🎮 Interaction & Controls Guide

### Visitor Gestures (Hands-Free)
| Action | Gesture / Physical Movement | Effect |
|---|---|---|
| **Freeze Time** | Hold up **Two Fingers / Victory (`✌️`)** for 0.65s | Spawns stationary temporal clone locked in physical space |
| **Switch Timeline** | **Palm Swipe (`✋`) Left / Right** | Instantly transitions to next / previous reality |
| **Rewind Time** | Hold **Pointing Up (`☝️`)** for 0.8s | Replays the last 3 seconds of motion in reverse |
| **Take Photo** | Press **`P`** or **`SPACE`** | Initiates 3-second countdown & studio flash |
| **Reveal QR** | Hold up **Thumbs-Up (`👍`)** for 0.35s | Displays high-contrast mobile download QR card |
| **Hide QR** | Show **Closed Fist (`✊`)** | Instantly dismisses the QR code card |

---

### Operator Keyboard Shortcuts (Expo Controls)
| Key | Function |
|---|---|
| **`ENTER` / `SPACE`** | Start from Attract screen / Trigger photo countdown |
| **`R`** | Emergency reset entire session back to Attract intro |
| **`F`** | Force freeze current visitor |
| **`W`** | Trigger 3-second Temporal Rewind |
| **`E`** | Toggle Temporal Echo mode (`PRESENT` ↔ `ECHO`) |
| **`M`** | Cycle personality modes (`PRESENT` → `ECHO` → `PARADOX` → `RIFT` → `ANOMALY`) |
| **`C`** | Clear all frozen temporal clones |
| **`LEFT` / `RIGHT`** | Switch Timeline |
| **`D`** | Toggle Developer / Diagnostics overlay (FPS, latency, model status) |
| **`P`** | Quick photo capture test |
| **`T`** | Force toggle QR popup |
| **`ESC` / `Q`** | Clean exit and resource shutdown |

---

## 🏗️ Architecture & Performance Design

```text
duo/
├── main.py                     # Primary runtime loop, state machine, and orchestration
├── requirements.txt            # Project dependencies
├── README.md                   # Documentation & operations guide
├── config/
│   ├── __init__.py
│   └── settings.py             # Centralized settings, timings, caps, and flags
├── camera/
│   ├── __init__.py
│   └── capture.py              # Threaded camera acquisition buffer + synthetic fallback
├── vision/
│   ├── __init__.py
│   ├── models_manager.py       # Local MediaPipe model downloader & cache verifier
│   ├── segmentation.py         # Selfie segmentation, guided filter, temporal smoothing
│   ├── pose.py                 # Multi-person skeletal pose estimation (duo tracking)
│   ├── hands.py                # Multi-hand tracking, pinch, open palm, pointing detection
│   └── motion.py               # Hand velocity history & triple-swipe detector
├── world/
│   ├── __init__.py
│   ├── environments.py         # Procedural virtual Timelines & ambient color profiles
│   ├── scene.py                # Smooth cubic ease-out scene sliding transitions
│   └── objects.py              # Interactive physics energy orbs and particle systems
├── interaction/
│   ├── __init__.py
│   ├── audio.py                # Procedural audio engine (sounddevice + NumPy waveforms)
│   ├── gestures.py             # State-aware gesture arbitration & hold hysteresis
│   ├── memories.py             # Frozen temporal clones, grounding, and shatter fracture
│   ├── reactions.py            # Combat collision evaluator (punches, kicks, grabs)
│   ├── rewind.py               # 3-second motion circular ring buffer & reverse playback
│   └── mirror_modes.py         # Temporal Echo, Paradox, Rift, and Anomaly modes
├── rendering/
│   ├── __init__.py
│   ├── intro.py                # Cinematic eerie Halloween startup experience & laser scan
│   ├── compositor.py           # Ambient lighting match, edge defringing, contact shadow
│   ├── effects.py              # Full-screen studio flash effect
│   └── ui.py                   # Minimalist visitor HUD, micro-tutorial, QR card, diagnostics
├── capture/
│   ├── __init__.py
│   └── qr.py                   # Local LAN IP resolver & high-contrast QR code generator
└── sharing/
    ├── __init__.py
    ├── server.py               # Background Flask daemon with input sanitization & auto-pruning
    └── templates/
        └── index.html          # Mobile web interface with direct WhatsApp share
```

### Performance Optimizations:
- **Dual Resolution Pipeline**: Rendering and UI run at full HD (`1280x720`), while vision ML inference runs at an optimized `480x270`.
- **Staggered Model Scheduling**:
  - Person Segmentation: every 2nd frame (`SEG_EVERY_N = 2`)
  - Hand Tracking: every 3rd frame (`HAND_EVERY_N = 3`)
  - Pose Estimation: every 6th frame (`POSE_EVERY_N = 6`)
  - Guarantees smooth **30+ FPS** with zero perceptible latency.
- **Ring Buffer Efficiency**: Rewind motion buffer stores downscaled 480x270 color and mask samples, consuming under 15 MB of RAM for the full 3-second history.
- **Inactivity Watchdog**: If no visitor is detected for 16 seconds in LIVE mode, automatically clears clones, resets the micro-tutorial, and returns to the Attract screen.
- **Photo Pruning**: Background thread prunes captures older than 4 hours or exceeding 100 images, protecting disk space during 8-hour college expos.

---

## 🚀 Quickstart & Setup

### Option A: High-Performance Native Rust (Recommended)
TimeSensei is fully ported to native Rust for ultra-low latency, blazing 60+ FPS execution, and instant standalone deployment.

```bash
# Run release build with Cargo
cargo run --release

# Run automated verification test suite
cargo test --test verify_all
```
The optimized native executable is located at `target/release/timesensei.exe`.

### Option B: Python Edition
```bash
pip install -r requirements.txt
python main.py
```
*(Packages: `opencv-python`, `mediapipe`, `numpy`, `pillow`, `qrcode`, `flask`, `scipy`, `sounddevice`)*

---

## 📱 Mobile Sharing & WhatsApp Workflow

1. Visitor poses with their temporal clones and holds up a **Peace (`✌️`) sign**.
2. 3-second countdown initiates, followed by a studio flash.
3. Visitor holds up a **Thumbs-Up (`👍`)** to summon the QR popup.
4. Visitor scans the QR code with their phone camera (connected to the same Wi-Fi network).
5. Opens the mobile page (`http://<LAN_IP>:8080/photo/<id>`):
   - Tap **"Save Photo to Phone"** to download the high-res JPEG.
   - Tap **"Share to WhatsApp"** to immediately forward the capture to friends or group chats.

---

## 🛠️ Expo Reliability & Troubleshooting

- **No physical camera detected**: TimeSensei automatically engages a synthetic simulated duo stream so you can demonstrate the system anywhere, even on machines without a camera.
- **No Wi-Fi available**: Core interaction, freezing time, combat fracture, rewind, and photo saving function 100% offline. The UI gracefully displays local save confirmation.
- **Audio Output**: Uses procedural real-time synthesis via `sounddevice`. If the computer has no speakers or audio permissions are denied, TimeSensei silently disables audio and runs smoothly without interruption.
- **Emergency Reset**: Press **`R`** on the keyboard at any time to flush the visitor session and return to the Attract title screen for the next visitor.
