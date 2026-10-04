"""
Download Real-ESRGAN ONNX models required for the AI Upscaler Bot.
Usage:
    python download_models.py [--output-dir ./models]
"""

import sys
import argparse
from pathlib import Path

# Safe UTF-8 console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import urllib.request
import urllib.error

MODELS = {
    "RealESRGAN_x4plus.onnx": {
        "hf_url": "https://huggingface.co/ai-forever/Real-ESRGAN/resolve/main/RealESRGAN_x4.onnx",
        "description": "General Photo 4x flagship model"
    },
    "RealESRGAN_x4plus_anime_6B.onnx": {
        "hf_url": "https://huggingface.co/akashhh/RealESRGAN_x4plus_anime_6B_onnx/resolve/main/RealESRGAN_x4plus_anime_6B.onnx",
        "description": "Anime / Digital Art 4x model"
    },
    "real_esrgan_general_x4v3.onnx": {
        "hf_url": "https://huggingface.co/qualcomm/Real-ESRGAN-General-x4v3/resolve/main/real_esrgan_general_x4v3.onnx",
        "description": "Fast compact Web/General model"
    }
}

def download_file(url: str, dest: Path) -> bool:
    print(f"Downloading from {url}...")
    try:
        def reporthook(blocknum, blocksize, totalsize):
            read = blocknum * blocksize
            if totalsize > 0:
                pct = min(100, read * 100 // totalsize)
                mb_read = read / (1024 * 1024)
                mb_total = totalsize / (1024 * 1024)
                sys.stdout.write(f"\r  Progress: {pct}% ({mb_read:.1f} MB / {mb_total:.1f} MB)")
                sys.stdout.flush()
        
        urllib.request.urlretrieve(url, dest, reporthook)
        print("\nDownload complete!")
        return True
    except urllib.error.URLError as e:
        print(f"\nFailed to download: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Download Real-ESRGAN ONNX models")
    parser.add_argument("--output-dir", type=Path, default=Path("./models"), help="Target directory for models")
    args = parser.parse_args()
    
    args.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Target model directory: {args.output_dir.resolve()}")
    
    for filename, info in MODELS.items():
        target_path = args.output_dir / filename
        if target_path.exists() and target_path.stat().st_size > 1024 * 1024:
            print(f"[EXISTS] {filename} already exists ({target_path.stat().st_size / (1024*1024):.1f} MB). Skipping.")
            continue
            
        print(f"\n[DOWNLOAD] Fetching {filename} ({info['description']})...")
        download_file(info["hf_url"], target_path)

if __name__ == "__main__":
    main()
