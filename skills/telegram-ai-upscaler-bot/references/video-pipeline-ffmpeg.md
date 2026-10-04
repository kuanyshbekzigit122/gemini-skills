# Video Upscaling & FFmpeg Pipeline Reference

This document outlines the frame-by-frame streaming super-resolution pipeline for video processing in the Telegram Bot.

---

## 1. High-Level Video Architecture

```
[ Input MP4 / MOV ]
         |
         v
  [ ffprobe ] ---> Check duration (<= 30s for bot), fps, width, height, audio track
         |
    +----+--------------------------------+
    |                                     |
    v                                     v
[ Audio Stream ]                      [ Video Stream ]
ffmpeg -i input.mp4 -vn -c:a aac      ffmpeg -i input.mp4 -r 15.0 frame_%06d.png
    |                                     |
    |                                     v
    |                            [ Frame Streaming Loop ]
    |                            For each frame:
    |                              1. Image.open(frame)
    |                              2. engine.upscale_pil_image()
    |                              3. save upscaled_frame
    |                              4. unlink(raw_frame)  <-- Saves disk space!
    |                              5. update progress callback
    |                                     |
    +------------------+------------------+
                       |
                       v
            [ FFmpeg Final Remux ]
            ffmpeg -framerate 15 -i up_frame_%06d.png
                   -i audio.m4a (if exists)
                   -vf deflicker=mode=pm:size=5
                   -c:v libx264 -preset superfast -crf 18
                   -pix_fmt yuv420p -c:a copy
                       |
                       v
            [ 4K / 2K Output MP4 ]
```

---

## 2. Probing Video Metadata with FFprobe

Always validate video inputs before processing to prevent denial-of-service from massive 10GB or 2-hour video uploads:

```python
import subprocess
import json
from pathlib import Path
from dataclasses import dataclass

@dataclass
class VideoInfo:
    width: int
    height: int
    duration: float
    fps: float
    has_audio: bool

def probe_video(video_path: Path) -> tuple[bool, VideoInfo | str]:
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(video_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return False, "Failed to inspect video metadata."
    
    data = json.loads(res.stdout)
    v_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    a_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    
    if not v_stream:
        return False, "No valid video stream found."
    
    # Calculate FPS from fraction (e.g., '30/1' or '30000/1001')
    r_fps = v_stream.get("r_frame_rate", "30/1")
    num, den = map(int, r_fps.split("/"))
    fps = num / den if den != 0 else 30.0
    
    duration = float(data.get("format", {}).get("duration", 0.0))
    return True, VideoInfo(
        width=int(v_stream.get("width", 0)),
        height=int(v_stream.get("height", 0)),
        duration=duration,
        fps=fps,
        has_audio=a_stream is not None
    )
```

---

## 3. Streaming Frame Processing (Disk-Safety Pattern)

When processing a 30-second 1080p video at 30 FPS, there are **900 frames**.
- 900 raw 1080p PNGs = ~3.5 GB.
- 900 upscaled 4K PNGs = ~14 GB.
- Keeping both on disk simultaneously can easily crash a server with a full disk error!

**The Streaming Unlink Pattern:**
As soon as `frame_000001.png` is upscaled and written to `up_frame_000001.png`, immediately call:
```python
frame_path.unlink(missing_ok=True)
```
This reduces disk overhead by **50%**, enabling long video processing on lean VPS storage.

---

## 4. Deflickering & Temporal Stabilization

Frame-by-frame super-resolution on real-world video often exhibits subtle high-frequency brightness variance between consecutive frames (flickering).
To stabilize the video during remuxing without sacrificing sharpness, apply FFmpeg's `deflicker` filter:

```bash
-vf "deflicker=mode=pm:size=5"
```
- `mode=pm`: Predictive moving average luminance smoothing.
- `size=5`: Temporal window of 5 frames. Eliminates flickering while preserving crisp edge details.

---

## 5. Audio Lossless Preservation

Always copy audio streams bit-for-bit without lossy re-encoding whenever possible:
```bash
-c:a copy
```
If re-encoding is required (e.g. from Opus/Vorbis to MP4-compatible AAC):
```bash
-c:a aac -b:a 192k
```
