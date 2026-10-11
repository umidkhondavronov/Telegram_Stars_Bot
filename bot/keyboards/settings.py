from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def settings_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Stars narxlari", callback_data="adm:set:stars")],
        [InlineKeyboardButton(text="🎁 Gift narxlari", callback_data="adm:set:gifts")],
        [InlineKeyboardButton(text="💎 Premium narxlari", callback_data="adm:set:premium")],
        [InlineKeyboardButton(text="💳 To'lov rekvizitlari", callback_data="adm:set:payment")],
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:home")],
    ])

def settings_back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Sozlamalar", callback_data="adm:settings")]
    ])
