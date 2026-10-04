# Telegram Inline Wizard UX & Split-View Collage Guide

This guide details the modern UI/UX patterns used to create a polished, mobile-app-like experience inside Telegram.

---

## 1. The Single-Message Interactive Card Pattern

Traditional bots send multiple consecutive messages when asking users for options:
- "Choose scale:" -> [2x] [4x]
- "Choose format:" -> [PNG] [JPG]
- "Processing..."
This creates annoying chat clutter.

**The Solution: In-Place Editing**
Maintain a single dynamic message card. Whenever the user clicks an option, update the keyboard and caption in-place using:
- `callback_query.message.edit_reply_markup(...)`
- `callback_query.message.edit_caption(...)`

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def build_wizard_keyboard(scale: int = 2, mode: str = "photo", fmt: str = "png") -> InlineKeyboardMarkup:
    scale_label = f"📐 Масштаб: {'2× ⚪' if scale == 2 else '⚫ 4×'}"
    mode_label = f"🎨 Режим: {'Фото 📷' if mode == 'photo' else 'Арт 🎨'}"
    fmt_label = f"💾 Формат: {fmt.upper()}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=scale_label, callback_data=f"toggle_scale:{scale}:{mode}:{fmt}")],
        [InlineKeyboardButton(text=mode_label, callback_data=f"toggle_mode:{scale}:{mode}:{fmt}")],
        [InlineKeyboardButton(text=fmt_label, callback_data=f"toggle_fmt:{scale}:{mode}:{fmt}")],
        [InlineKeyboardButton(text="🚀 AI ӨҢДЕУДІ БАСТАУ", callback_data=f"start_upscale:{scale}:{mode}:{fmt}")]
    ])
    return keyboard
```

---

## 2. Animated Progress Bar & ChatAction Pulse

During heavy CPU/GPU processing (which may take 5–30 seconds), users need visual reassurance that the bot hasn't frozen.

### Dynamic Progress Bar Generator:
```python
def generate_progress_bar(percentage: float, length: int = 10) -> str:
    filled = int(round(length * percentage))
    bar = "■" * filled + "□" * (length - filled)
    return f"[{bar}] {int(percentage * 100)}%"
```

### Native `sendChatAction` Keep-Alive Loop:
Telegram requires chat actions (e.g. `upload_photo`, `upload_video`) to be refreshed every 4.5 seconds:
```python
import asyncio
from aiogram import Bot

async def keep_chat_action_alive(bot: Bot, chat_id: int, action: str = "upload_photo", stop_event: asyncio.Event = None):
    while not (stop_event and stop_event.is_set()):
        try:
            await bot.send_chat_action(chat_id=chat_id, action=action)
        except Exception:
            pass
        await asyncio.sleep(4.0)
```

---

## 3. Before / After Split-View Collage Generator

A visual comparison image allows users to immediately appreciate the quality improvement.

```python
from PIL import Image, ImageDraw, ImageFont

def create_before_after_split(
    original_img: Image.Image,
    upscaled_img: Image.Image,
    split_ratio: float = 0.5
) -> Image.Image:
    # Resize original to match upscaled dimensions for aligned comparison
    target_w, target_h = upscaled_img.size
    orig_resized = original_img.resize((target_w, target_h), Image.Resampling.BILINEAR)
    
    split_x = int(target_w * split_ratio)
    
    # Create canvas
    canvas = Image.new("RGB", (target_w, target_h))
    
    # Paste Left: Original ("BEFORE")
    canvas.paste(orig_resized.crop((0, 0, split_x, target_h)), (0, 0))
    # Paste Right: Upscaled ("AFTER")
    canvas.paste(upscaled_img.crop((split_x, 0, target_w, target_h)), (split_x, 0))
    
    draw = ImageDraw.Draw(canvas)
    
    # Draw vertical divider line (with subtle drop shadow)
    line_w = max(4, target_w // 400)
    draw.line([(split_x, 0), (split_x, target_h)], fill=(255, 255, 255), width=line_w)
    
    # Draw badges
    # Left Badge: "◀️ ДЕЙІН"
    draw.rectangle([20, 20, 220, 80], fill=(0, 0, 0, 180))
    draw.text((40, 35), "◀️ ДЕЙІН", fill=(255, 255, 255))
    
    # Right Badge: "КЕЙІН (AI) ▶️"
    draw.rectangle([target_w - 240, 20, target_w - 20, 80], fill=(0, 180, 80, 200))
    draw.text((target_w - 220, 35), "КЕЙІН (AI) ▶️", fill=(255, 255, 255))
    
    return canvas
```
