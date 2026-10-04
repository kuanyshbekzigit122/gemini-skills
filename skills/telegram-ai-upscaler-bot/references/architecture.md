# AI Upscaler Telegram Bot: Core Architecture

This document details the architectural blueprint of the production-grade AI Image and Video Upscaler Telegram Bot.

```
                      +---------------------------------------+
                      |           Telegram User               |
                      +---------------------------------------+
                                          |
                                          | (Photo / Video / Callback)
                                          v
                      +---------------------------------------+
                      |         Aiogram Dispatcher            |
                      |   (Handlers: photo, video, callback)  |
                      +---------------------------------------+
                                          |
                        +-----------------+-----------------+
                        |                                   |
                        v                                   v
             +--------------------+               +--------------------+
             |   Inline Wizard    |               | Concurrency Limiter|
             |  (Interactive UI)  |               | (asyncio.Semaphore)|
             +--------------------+               +--------------------+
                        |                                   |
                        +-----------------+-----------------+
                                          |
                                          v
                      +---------------------------------------+
                      |            Temp Workspace             |
                      | (Isolated sandbox with auto-cleanup)  |
                      +---------------------------------------+
                                          |
                        +-----------------+-----------------+
                        |                                   |
                        v                                   v
             +--------------------+               +--------------------+
             |   Image Pipeline   |               |   Video Pipeline   |
             | (Alpha split/merge)|               |  (FFmpeg streaming)|
             +--------------------+               +--------------------+
                        \                                   /
                         \                                 /
                          v                               v
                      +---------------------------------------+
                      |     FreeUpscaler ONNX Engine          |
                      |  - 128x128 Overlapping Tiling         |
                      |  - 16px Overlap / 112px Step          |
                      |  - 2D Cosine/Linear Ramp Blending     |
                      |  - Multi-threaded CPU / CUDA / DML    |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |           Delivery Engine             |
                      |  - High-res Document / Photo output   |
                      |  - Before / After Split-View Collage  |
                      |  - Live Progress Bar & Status Updates |
                      +---------------------------------------+
```

---

## 1. Modular Directory Decomposition

A well-structured production bot separates concerns strictly across six layers:

1. **`bot/config.py`**:
   - Environment variables loaded via `python-dotenv`.
   - Token validation, concurrency limit settings, upload file size limits (e.g. 20MB for images, 50MB for video), WebApp URL configurations.
2. **`bot/core/`**:
   - `queue.py`: `asyncio.Semaphore` based concurrency management. Prevents server thrashing or Out-Of-Memory (OOM) crashes by queuing excess processing requests gracefully.
   - `status.py`: Telegram's native `sendChatAction` keep-alive pulse (`upload_photo`, `upload_video`) running in a background asyncio loop while heavy processing occurs.
3. **`bot/engine/`**:
   - `base.py`: Abstract Base Class `BaseUpscalerEngine` defining standardized `upscale_pil_image` interfaces.
   - `model_manager.py`: Automated discovery and downloading of Real-ESRGAN weights (`RealESRGAN_x4plus.onnx`, `RealESRGAN_x4plus_anime_6B.onnx`, `real_esrgan_general_x4v3.onnx`).
   - `onnx_engine.py`: High-performance server-side ONNX Runtime engine. Manages session pooling, thread allocations, dynamic tiling, and seam elimination.
   - `image_processor.py`: Format detection, alpha channel (RGBA transparency) extraction/re-integration, and Lanczos downsampling (4x to 2x).
   - `video_processor.py`: FFmpeg-based frame demuxing, FPS normalization, streaming upscaling, audio track extraction, and lossless remuxing.
4. **`bot/handlers/`**:
   - `start.py`: Welcoming message, command registration, and interactive help documentation.
   - `photo.py` & `document.py`: Ingestion of photos or uncompressed documents, triggering the Inline Wizard.
   - `video.py`: Video validation, duration/size probing via `ffprobe`, and video wizard initialization.
   - `callbacks.py`: Real-time in-place callback query dispatching (scale toggling, model mode switching, processing triggers, before/after comparisons).
5. **`bot/services/`**:
   - `telegram_service.py`: Encapsulates message editing, media sending with fallback handling for Telegram payload limits (sending as Document if Photo dimensions exceed limits).
6. **`bot/utils/`**:
   - `file_utils.py`: Context manager `temp_workspace(prefix=...)` guaranteeing folder deletion even on unhandled exceptions.
   - `media_info.py`: Wrapper around `ffprobe` to inspect video resolution, frame rate, duration, and audio streams.

---

## 2. Key Lifecycle & Data Flows

### Ingestion & Wizard Flow:
1. User sends photo/video.
2. Handler immediately downloads the file into a temporary staging path.
3. Handler sends a single interactive card with inline buttons (`2x / 4x`, `Photo / Art`, `PNG / JPG`).
4. User clicks inline buttons to toggle options. The bot uses `edit_message_reply_markup` or `edit_message_caption` to update the card in-place with zero notification spam.

### Processing Flow:
1. User clicks `🚀 AI ӨҢДЕУДІ БАСТАУ` (Start AI Processing).
2. The card updates to an animated progress bar: `[■■■■□□□□] 50%`.
3. Background task acquires the `asyncio.Semaphore`.
4. The processing engine executes tiled inference.
5. The result is saved to disk and delivered via `send_photo` or `send_document`.
6. Result caption includes interactive buttons: `[ 🔄 Салыстыру (Дейін/Кейін) ]` and `[ 📤 Бөлісу ]`.
7. `temp_workspace` context manager executes, scrubbing all raw/intermediate files completely.
