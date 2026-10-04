"""
Aiogram 3.x Interactive Inline Wizard Handler Pattern.
Demonstrates single-message card state updates and progress bar animation.
"""

import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)

def make_keyboard(scale: int = 2, mode: str = "photo", fmt: str = "png") -> InlineKeyboardMarkup:
    scale_text = f"📐 Scale: {'2× ⚪' if scale == 2 else '⚫ 4×'}"
    mode_text = f"🎨 Mode: {'Photo 📷' if mode == 'photo' else 'Art 🎨'}"
    fmt_text = f"💾 Format: {fmt.upper()}"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=scale_text, callback_data=f"toggle:scale:{scale}:{mode}:{fmt}")],
        [InlineKeyboardButton(text=mode_text, callback_data=f"toggle:mode:{scale}:{mode}:{fmt}")],
        [InlineKeyboardButton(text=fmt_text, callback_data=f"toggle:fmt:{scale}:{mode}:{fmt}")],
        [InlineKeyboardButton(text="🚀 START AI UPSCALING", callback_data=f"start:{scale}:{mode}:{fmt}")]
    ])

def register_wizard_handlers(dp: Dispatcher):
    
    @dp.message(F.photo)
    async def on_photo(message: Message):
        caption = (
            "<b>✨ AI Upscaler Pro Wizard</b>\n\n"
            "Select your desired parameters below and click <b>Start</b>:"
        )
        await message.reply(caption, reply_markup=make_keyboard(), parse_mode="HTML")

    @dp.callback_query(F.data.startswith("toggle:"))
    async def on_toggle(callback: CallbackQuery):
        parts = callback.data.split(":")
        target, cur_scale, cur_mode, cur_fmt = parts[1], int(parts[2]), parts[3], parts[4]
        
        if target == "scale":
            cur_scale = 4 if cur_scale == 2 else 2
        elif target == "mode":
            cur_mode = "art" if cur_mode == "photo" else "photo"
        elif target == "fmt":
            cur_fmt = "jpg" if cur_fmt == "png" else "png"
            
        await callback.message.edit_reply_markup(
            reply_markup=make_keyboard(cur_scale, cur_mode, cur_fmt)
        )
        await callback.answer()

    @dp.callback_query(F.data.startswith("start:"))
    async def on_start(callback: CallbackQuery, bot: Bot):
        _, scale, mode, fmt = callback.data.split(":")
        scale = int(scale)
        
        # Step 1: Update card to progress state
        await callback.message.edit_caption(
            caption=f"⏳ <b>AI Processing Started...</b>\n\n[■□□□□□□□□□] 10%\nMode: {mode.upper()} | Scale: {scale}×",
            parse_mode="HTML"
        )
        await callback.answer("AI processing initiated!")
        
        # Step 2: Simulate live progress updates
        for pct in [30, 60, 90, 100]:
            await asyncio.sleep(1.0)
            filled = pct // 10
            bar = "■" * filled + "□" * (10 - filled)
            try:
                await callback.message.edit_caption(
                    caption=f"⏳ <b>Upscaling in progress...</b>\n\n[{bar}] {pct}%\nMode: {mode.upper()} | Scale: {scale}×",
                    parse_mode="HTML"
                )
            except Exception:
                pass
                
        # Step 3: Complete and send delivery message
        await callback.message.reply(
            f"✅ <b>Done!</b> Upscaled to {scale}× ({fmt.upper()}).",
            parse_mode="HTML"
        )
