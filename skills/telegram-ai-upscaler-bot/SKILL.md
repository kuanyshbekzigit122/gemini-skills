---
name: telegram-ai-upscaler-bot
description: >-
  Comprehensive guide, architecture, and scaffolding toolkit for building, deploying,
  and scaling an AI-powered Image & Video Upscaler Telegram Bot using Real-ESRGAN,
  ONNX Runtime (CPU/GPU), tiled inference with smooth seam blending, interactive
  inline wizard UX, live status updates, Before/After split collages, and FFmpeg video streaming.
---

# 🚀 AI Image & Video Upscaler Telegram Bot Skill

This skill provides an end-to-end, production-tested blueprint for creating a state-of-the-art **AI Image and Video Super-Resolution Telegram Bot**. It teaches developers, engineers, and AI assistants how to architect, implement, optimize, and deploy a robust bot powered by **Real-ESRGAN** and **ONNX Runtime**.

---

## 📑 Skill Structure

This skill is organized into a modular, multi-file toolkit:

```text
telegram-ai-upscaler-bot/
├── SKILL.md                          # Master guide & step-by-step workflow (this file)
├── references/                       # Deep-dive architectural & mathematical guides
│   ├── architecture.md               # System component layout & data lifecycle flows
│   ├── onnx-tiling-and-blending.md   # Mathematical formulation of 128x128 tiling & 2D ramp blending
│   ├── video-pipeline-ffmpeg.md      # Frame streaming, 15fps optimization & audio remuxing
│   ├── inline-wizard-ux.md           # Single-message dynamic cards, progress bars & split collages
│   └── deployment-and-docker.md      # Dockerfile optimization, Hugging Face Spaces & systemd
├── scripts/                          # Ready-to-run automation tools
│   ├── scaffold_bot.py               # One-command full project generator CLI
│   ├── download_models.py            # Automated Real-ESRGAN ONNX weights downloader
│   └── test_upscaler_pipeline.py     # Independent test & diagnostics suite
├── examples/                         # Minimal clean reference implementations
│   ├── onnx_tiler_minimal.py         # 60-line standalone tiling & blending script
│   └── wizard_flow_aiogram.py        # Aiogram 3.x in-place wizard handler pattern
└── resources/                        # Configuration & container templates
    ├── .env.template                 # Environment variables specification
    ├── Dockerfile.template           # Production-ready multi-stage Dockerfile
    └── requirements.txt.template     # Pinned Python package dependencies
```

---

## 🎯 Core Technical Highlights

1. **Memory-Safe Tiled Inference (Zero OOM Crashes):**
   - Cuts inputs into $128 \times 128$ tiles with a $16\text{ px}$ overlap ($112\text{ px}$ step).
   - Recombines $512 \times 512$ output tiles using a **2D smooth triangular/cosine ramp blending matrix** to eliminate visible seams and brightness shifts.
   - Enables upscaling $4K$ images on modest 2 GB RAM CPU instances without crashing.
2. **True Alpha (Transparency) Preservation:**
   - Detects RGBA PNGs, separates the RGB color channels from the Alpha mask, upscales both independently with Lanczos alignment, and seamlessly merges them.
3. **Dual Scale Logic (2× vs 4×):**
   - Runs the native 4× super-resolution model, then downsamples to 2× using the anti-aliased Lanczos filter. This yields dramatically superior sharpness compared to native 2x models.
4. **Streaming Video Super-Resolution Pipeline:**
   - Normalizes frame rates (e.g. 15 FPS for CPU or 30 FPS for GPU).
   - Extracts frames with FFmpeg and immediately deletes processed raw frames (`unlink`) to prevent disk exhaustion.
   - Extracts AAC audio losslessly and remuxes with temporal deflickering (`-vf deflicker=mode=pm:size=5`).
5. **Interactive Inline Wizard UX (No Message Clutter):**
   - Single dynamic card updated in-place (`edit_message_reply_markup` / `edit_message_caption`).
   - Toggles: `[ 📐 Scale: 2× ⇄ 4× ]`, `[ 🎨 Mode: Photo ⇄ Art ]`, `[ 💾 Format: PNG ⇄ JPG ]`.
   - Real-time animated progress bar (`[■■■■□□□□] 50%`) with keep-alive `sendChatAction` pulses.
6. **Before / After Split-View Comparison:**
   - Generates a side-by-side split collage showing original vs upscaled results with a center divider line and custom badges (`◀️ BEFORE` / `AFTER (AI) ▶️`).
7. **Concurrency Limiter:**
   - Protects the host machine from load spikes using an asynchronous semaphore (`asyncio.Semaphore(2)`).

---

## 🛠️ Step-by-Step Implementation Guide

### Step 1: Project Scaffolding
To instantly scaffold a complete bot project, run the provided scaffolding script:
```bash
python scripts/scaffold_bot.py --output ./my-upscaler-bot --bot-name "AI Upscaler Bot"
```
Or structure your directory following [architecture.md](references/architecture.md):
- `bot/config.py`: Environment configuration and limits.
- `bot/core/queue.py`: Concurrency limiter semaphore.
- `bot/core/status.py`: Telegram chat action pulse loop.
- `bot/engine/onnx_engine.py`: ONNX Runtime tiled inference engine.
- `bot/engine/image_processor.py`: Format & alpha channel handling.
- `bot/engine/video_processor.py`: FFmpeg frame streaming pipeline.
- `bot/handlers/`: Aiogram message and callback handlers.
- `bot/utils/file_utils.py`: Safe temporary folder context manager.

---

### Step 2: Download Real-ESRGAN ONNX Models
Download the pre-converted Real-ESRGAN ONNX model weights into the `models/` folder:
```bash
python scripts/download_models.py --output-dir ./models
```
Supported models:
- `RealESRGAN_x4plus.onnx` (67 MB): General photo super-resolution.
- `RealESRGAN_x4plus_anime_6B.onnx` (17.9 MB): Anime, illustrations, digital art.
- `real_esrgan_general_x4v3.onnx`: High-speed general compact model.

---

### Step 3: Implement the Tiled ONNX Engine
Read [onnx-tiling-and-blending.md](references/onnx-tiling-and-blending.md) and review [examples/onnx_tiler_minimal.py](examples/onnx_tiler_minimal.py).
Ensure your engine:
1. Generates tile indices stepping by $112\text{ px}$ with $128\text{ px}$ width/height.
2. Applies the precomputed 2D ramp weight matrix $W(x, y)$ of shape $(512, 512)$.
3. Accumulates outputs and weights in floating point canvases:
   $$\text{output\_canvas} \mathrel{+}= \text{tile} \odot W, \quad \text{weight\_canvas} \mathrel{+}= W$$
4. Divides output by weight canvas to normalize.

---

### Step 4: Implement Video Streaming Pipeline
Review [video-pipeline-ffmpeg.md](references/video-pipeline-ffmpeg.md):
1. Probe input video with `ffprobe` (validate duration $\le 30\text{s}$, check audio stream).
2. Extract audio to temporary `audio.m4a` using `-vn -c:a aac`.
3. Extract frames at target FPS (`-r 15.0`) to a temporary folder.
4. Loop through frames, upscale with ONNX, and **immediately delete** the raw input frame.
5. Remux with FFmpeg:
   ```bash
   ffmpeg -y -framerate 15 -i up_frame_%06d.png -i audio.m4a \
          -vf "deflicker=mode=pm:size=5" \
          -c:v libx264 -preset superfast -crf 18 -pix_fmt yuv420p \
          -c:a copy output.mp4
   ```

---

### Step 5: Implement Interactive Wizard & Split-View
Review [inline-wizard-ux.md](references/inline-wizard-ux.md) and [examples/wizard_flow_aiogram.py](examples/wizard_flow_aiogram.py):
1. In `bot/handlers/photo.py` and `bot/handlers/video.py`, intercept media messages and send the initial inline keyboard.
2. In `bot/handlers/callbacks.py`, handle toggle callbacks by editing the message reply markup in-place.
3. When processing starts, launch `keep_chat_action` in the background and update caption with `[■■■■□□□□] 50%`.
4. On completion, provide a `[ 🔄 Compare (Before / After) ]` button that dynamically generates the split-view comparison image.

---

### Step 6: Test and Verify Locally
Run the diagnostic test suite to ensure ONNX Runtime, tiling, and alpha pipelines function without errors:
```bash
python scripts/test_upscaler_pipeline.py
```

---

### Step 7: Containerize & Deploy
Review [deployment-and-docker.md](references/deployment-and-docker.md):
1. Build the Docker container using `resources/Dockerfile.template`.
2. Deploy to **Hugging Face Spaces** (Docker SDK, port 7860) or a standard Linux VPS using `systemd`.
3. Set your `TELEGRAM_BOT_TOKEN` in the environment secrets.

---

## ⚠️ Common Pitfalls & Best Practices

1. **Windows Unicode Path Crashes with OpenCV:**
   - Standard `cv2.imread()` fails on Windows if file paths contain non-ASCII characters.
   - **Fix:** Always use buffer decoding:
     ```python
     def imread_unicode(p):
         with open(p, 'rb') as f:
             return cv2.imdecode(np.frombuffer(f.read(), np.uint8), cv2.IMREAD_COLOR)
     ```
2. **Telegram Photo Dimension Limits:**
   - Telegram rejects photos whose total width + height exceeds $10,000\text{ px}$ or file size $>10\text{ MB}$.
   - **Fix:** If upscaled dimensions exceed limits, deliver the result as a Telegram Document (`send_document`) instead of Photo (`send_photo`).
3. **FFmpeg Subprocess Hangs:**
   - Never use `stdout=subprocess.PIPE` without reading it, as large FFmpeg stderr buffers cause deadlocks.
   - **Fix:** Use `capture_output=True` or redirect to temporary log files.
4. **Disk Overflow During Video Upscaling:**
   - Never leave uncompressed raw frames on disk. Always delete input frames as soon as the upscaled frame is written.
