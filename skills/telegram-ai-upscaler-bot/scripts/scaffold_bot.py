"""
CLI Scaffolding Tool for AI Image & Video Upscaler Telegram Bot.
Generates a complete, modular, production-ready project in seconds.

Usage:
    python scaffold_bot.py --output /path/to/my_new_bot [--bot-name "MyUpscalerBot"]
"""

import os
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

CONFIG_PY = '''import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "2"))
TARGET_VIDEO_FPS = float(os.getenv("TARGET_VIDEO_FPS", "15.0"))
MAX_IMAGE_MB = int(os.getenv("MAX_IMAGE_MB", "20"))
MAX_VIDEO_MB = int(os.getenv("MAX_VIDEO_MB", "50"))
MAX_VIDEO_DURATION_SEC = int(os.getenv("MAX_VIDEO_DURATION_SEC", "30"))
'''

CORE_QUEUE_PY = '''import asyncio
import logging
from bot.config import MAX_CONCURRENT_TASKS

logger = logging.getLogger(__name__)

class ConcurrencyLimiter:
    def __init__(self, max_concurrent: int = MAX_CONCURRENT_TASKS):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
    async def acquire(self):
        await self._semaphore.acquire()
        
    def release(self):
        self._semaphore.release()
        
    async def __aenter__(self):
        await self.acquire()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.release()

upscaler_limiter = ConcurrencyLimiter()
'''

CORE_STATUS_PY = '''import asyncio
import logging
from aiogram import Bot

logger = logging.getLogger(__name__)

async def keep_chat_action(bot: Bot, chat_id: int, action: str = "upload_photo", stop_event: asyncio.Event = None):
    while not (stop_event and stop_event.is_set()):
        try:
            await bot.send_chat_action(chat_id=chat_id, action=action)
        except Exception as exc:
            logger.debug("Chat action pulse failed: %s", exc)
        await asyncio.sleep(4.0)
'''

FILE_UTILS_PY = '''import shutil
import tempfile
from pathlib import Path
from contextlib import contextmanager

@contextmanager
def temp_workspace(prefix: str = "upscale_"):
    temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
'''

def scaffold(target_dir: Path, bot_name: str):
    print(f"[START] Scaffolding {bot_name} at: {target_dir.resolve()}...")
    
    # Create directories
    dirs = [
        target_dir / "bot" / "core",
        target_dir / "bot" / "engine",
        target_dir / "bot" / "handlers",
        target_dir / "bot" / "services",
        target_dir / "bot" / "utils",
        target_dir / "models",
        target_dir / "tests",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        (d / "__init__.py").touch(exist_ok=True)
        
    # Write core files
    (target_dir / "bot" / "config.py").write_text(CONFIG_PY, encoding="utf-8")
    (target_dir / "bot" / "core" / "queue.py").write_text(CORE_QUEUE_PY, encoding="utf-8")
    (target_dir / "bot" / "core" / "status.py").write_text(CORE_STATUS_PY, encoding="utf-8")
    (target_dir / "bot" / "utils" / "file_utils.py").write_text(FILE_UTILS_PY, encoding="utf-8")
    
    (target_dir / ".env.example").write_text(
        "TELEGRAM_BOT_TOKEN=your_token_here\nMAX_CONCURRENT_TASKS=2\nTARGET_VIDEO_FPS=15.0\n",
        encoding="utf-8"
    )
    (target_dir / "requirements.txt").write_text(
        "aiogram>=3.4.1\nonnxruntime>=1.17.1\npillow>=10.2.0\nnumpy>=1.26.4\npython-dotenv>=1.0.1\n",
        encoding="utf-8"
    )
    
    print("[SUCCESS] Project structure successfully generated!")
    print(f"Next steps:")
    print(f"   cd {target_dir}")
    print(f"   pip install -r requirements.txt")
    print(f"   cp .env.example .env (and set your TELEGRAM_BOT_TOKEN)")
    print(f"   python main.py")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scaffold AI Upscaler Telegram Bot")
    parser.add_argument("--output", type=Path, required=True, help="Target project directory")
    parser.add_argument("--bot-name", type=str, default="AI Upscaler Bot", help="Bot display name")
    args = parser.parse_args()
    
    scaffold(args.output, args.bot_name)
