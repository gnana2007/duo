# Interactive Mirror World 🪞✨

A real-time, gesture-controlled **Interactive Mirror World** built with **Python, OpenCV, and MediaPipe**. Users step in front of the screen and are naturally embedded inside dynamic virtual environments with environmental lighting adaptation, ground contact shadows, hand gesture controls, dual-person ("duo") tracking, interactive physics objects, and instant mobile QR sharing to WhatsApp.

---

## 🌟 Key Features

1. **Natural Vision & Duo Segmentation**:
   - High-throughput person segmentation via MediaPipe with temporal IIR mask smoothing ($\alpha_t = 0.75 \alpha_{t-1} + 0.25 \alpha_{new}$) to eliminate jitter.
   - Dual-person ("duo") tracking supporting two individuals simultaneously in frame.
   - Realistic ground contact shadows synthesized under feet/silhouette anchors.
   - Edge defringing to remove real-world background light spill and halos.
   - Ambient lighting color adaptation (matches foreground color temperature, contrast, and brightness to each virtual world).

2. **6 Rich Virtual Worlds**:
   - **Cyberpunk Metropolis**: Neon pink/cyan skyline, rainy reflections, perspective asphalt grid.
   - **Luxury Penthouse**: Twilight city skyline, amber chandelier spotlight, polished marble floor.
   - **Tropical Sunset Beach**: Golden hour sunset, turquoise ocean waves, warm sandy shore.
   - **Cosmic Deep Space**: Swirling nebula clouds, starfield, orbital station observation deck.
   - **Serene Bamboo Grove**: Lush misty forest, emerald bamboo stalks, mossy stone path.
   - **Holo Game Arena**: Electric cyan & red holographic laser rings with hexagonal floor grid.

3. **Gesture-Driven World Switching**:
   - **Swipe Left (`<-`)**: Fast horizontal hand sweep slides the scene left to reveal the next environment.
   - **Swipe Right (`->`)**: Fast horizontal hand sweep slides the scene right to reveal the previous environment.
   - Smooth cubic ease-out sliding transitions.

4. **Hands-Free Capture & Burst/Timelapse**:
   - **Top-Center Virtual Touch Button**: Hover your hand over the top-center target zone to trigger capture with a circular progress fill.
   - **Peace / Victory Sign (`V`)**: Hold up a peace sign for 0.6s to initiate a 3-second countdown ring.
   - **Burst / Timelapse Photography**: Capture 4 sequential poses with on-screen guidance and studio flash animations.
   - **Photo Review Screen**: Preview your composite image, with Thumbs-up (`Thumbs_Up`) or `[K]` to keep, and `[D]` to discard.

5. **Instant QR Mobile Sharing & WhatsApp**:
   - Automatically resolves local Wi-Fi / Ethernet LAN IP (`http://<LAN_IP>:8080/photo/<photo_id>`).
   - Generates an on-screen high-contrast QR code.
   - Scanning opens a mobile-optimized gallery page on your phone with **1-Tap Save to Photos** and **Direct Share to WhatsApp**.

6. **Interactive Physics Objects & Mirror Personality Modes**:
   - Floating dynamic energy orbs that bounce, spark, or pop when you **touch, punch (fist), kick (foot), or wave**.
   - **Pinch & Drag**: Pinching fingertips grips virtual objects.
   - **Personality Modes**:
     - `Mirror`: Pure real-time reflection with configurable latency buffer (`[` and `]` to adjust).
     - `Opposite`: Inverted horizontal interaction dynamics.
     - `Lazy`: Heavy sluggish inertia with lingering ethereal motion blur trails.
     - `Angry`: Flaming ember particles and red lightning aura crackling from hands.
     - `Curious`: Autonomous glowing wisps that orbit and gravitate toward fingertips.

---

## 📁 Project Structure

```text
d:\duo\
├── main.py                     # Primary runtime loop & orchestrator
├── requirements.txt            # Project dependencies
├── README.md                   # Complete documentation & usage guide
├── camera/
│   ├── __init__.py
│   └── capture.py              # Real-time threaded camera stream + synthetic duo fallback
├── vision/
│   ├── __init__.py
│   ├── models_manager.py       # Auto-downloads and caches MediaPipe task models
│   ├── segmentation.py         # Selfie segmentation, temporal smoothing, contact shadow
│   ├── pose.py                 # Multi-person skeletal pose estimation (duo tracking)
│   ├── hands.py                # Multi-hand tracking (up to 4 hands), pinch & gesture detection
│   └── motion.py               # Hand velocity analysis for swipe gesture triggers
├── world/
│   ├── __init__.py
│   ├── environments.py         # 6 procedural HD virtual worlds with ambient tint profiles
│   ├── scene.py                # Scene transition state & smooth sliding animations
│   └── objects.py              # Interactive physics objects (energy orbs, bubbles, sparks)
├── interaction/
│   ├── __init__.py
│   ├── button.py               # Top-center virtual touch button with hover progress ring
│   ├── gestures.py             # Gesture evaluation (Peace sign, Thumbs-up, Open palm, Fist)
│   └── mirror_modes.py         # Mirror delay, Opposite, Lazy, Angry, Curious modes
├── rendering/
│   ├── __init__.py
│   ├── compositor.py           # Natural matting, edge defringing, lighting match, alpha blending
│   ├── effects.py              # Full-screen camera flash and countdown ring
│   └── ui.py                   # Glassmorphic HUD overlay, review screen, QR modal
├── capture/
│   ├── __init__.py
│   ├── photo_capture.py        # Single & burst capture state machine
│   ├── timelapse.py            # Timelapse sequencer for multi-pose burst captures
│   └── qr.py                   # QR code generator with local LAN IP resolution
├── sharing/
│   ├── __init__.py
│   ├── server.py               # Lightweight background Flask server on port 8080
│   └── templates/
│       └── index.html          # Mobile web app with WhatsApp & native share buttons
├── assets/
│   └── environments/           # Cached 1280x720 environment background images
└── models/                     # Cached MediaPipe model weights (.tflite and .task)
```

---

## 🚀 Quickstart

### 1. Prerequisites
- Python 3.10, 3.11, or 3.12 (64-bit recommended)
- Standard USB webcam or built-in laptop camera

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

*(All required packages: `opencv-python`, `mediapipe`, `numpy`, `pillow`, `qrcode`, `flask`, `scipy`)*

### 3. Run the Interactive Mirror World
```bash
python main.py
```

*Note: On first startup, the required lightweight models (`selfie_segmenter.tflite`, `gesture_recognizer.task`, `pose_landmarker_lite.task`) and high-aesthetic background worlds are automatically prepared and cached.*

---

## 🎮 Controls & Interactions

### Hands-Free Gestures (Stand in front of camera)
| Action | Gesture / Physical Movement | Effect |
|---|---|---|
| **Take Photo** | Raise hand into **Top-Center circle** (hover 0.8s) | Triggers 3-second countdown & photo capture |
| **Take Photo** | Hold up a **Peace / Victory Sign (`V`)** | Hands-free countdown trigger |
| **Change World** | **Swipe Hand Left / Right** | Slides smoothly to next / previous environment |
| **Confirm Photo** | Give a **Thumbs-Up (`Thumb_Up`)** | Keeps photo and displays QR code on review screen |
| **Punch Object** | Move a **Closed Fist** into an orb | Strikes orb with high impulse and shockwave sparks |
| **Grip Object** | **Pinch** thumb & index near an orb | Grabs and drags the floating orb |
| **Kick Object** | Swing leg / ankle near an orb | Kicks orb with dynamic velocity |

### Keyboard Shortcuts (Studio Operator Mode)
- **`SPACE` / `C`**: Trigger Photo Countdown (or close QR screen)
- **`B`**: Start 4-Pose Burst / Timelapse Capture
- **`M`**: Cycle Personality Mode (*Mirror* → *Opposite* → *Lazy* → *Angry* → *Curious*)
- **`[` / `]`**: Decrease / Increase Mirror Latency Delay
- **`N` / `P`** or **Arrow Left / Right**: Switch Virtual Environment
- **`K`**: Keep Photo on Review Screen
- **`D` / `X`**: Discard Photo
- **`Q` / `ESC`**: Exit Application

---

## 📱 Mobile Sharing & WhatsApp Workflow

1. Trigger photo capture via top button or peace sign.
2. Review photo on screen and select **Keep Photo** (or show Thumbs-Up).
3. A large QR code appears on the display encoding `http://<YOUR_LAN_IP>:8080/photo/<id>`.
4. Open the native Camera app on your smartphone (connected to the same Wi-Fi) and point at the QR code.
5. Tap the link to open the mobile web page:
   - Tap **"Save Photo to Phone"** to download the high-res JPEG.
   - Tap **"Share to WhatsApp"** to instantly share with friends or family!

---

## ⚙️ Performance Tuning & Architecture Notes

- **Processing Resolution**: Vision models run at an optimized internal resolution (`640x360`), while rendering and display run at full HD (`1280x720`). This guarantees smooth **25–35+ FPS** on standard consumer laptops.
- **Temporal IIR Alpha Smoothing**: Suppresses edge jitter between successive frames without adding perceptible lag.
- **Defringing & Lighting Matching**: Automatically analyzes the ambient color tone of each world and applies Reinhard color transfer and boundary defringing to avoid green-screen halos.
- **Synthetic Stream Fallback**: If no physical webcam is detected (or camera is occupied by another app), the system automatically activates a simulated duo stream for instant testing.
