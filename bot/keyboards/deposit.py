from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def deposit_cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Bekor qilish",callback_data="deposit_cancel")]])

def admin_deposit_keyboard(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash",callback_data=f"deposit_approve:{order_id}"),
        InlineKeyboardButton(text="❌ Rad etish",callback_data=f"deposit_reject:{order_id}")]])
