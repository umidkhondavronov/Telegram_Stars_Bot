from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Stars sotib olish", callback_data="stars")],
        [InlineKeyboardButton(text="🎁 Sovg'a sotib olish", callback_data="gifts")],
        [InlineKeyboardButton(text="💎 Telegram Premium", callback_data="premium_buy")],
        [InlineKeyboardButton(text="💳 Balansni to'ldirish", callback_data="deposit")],
        [InlineKeyboardButton(text="💰 Balansim", callback_data="balance"), InlineKeyboardButton(text="👤 Profilim", callback_data="profile")],
        [InlineKeyboardButton(text="📦 Buyurtmalarim", callback_data="orders")],
        [InlineKeyboardButton(text="📜 Operatsiyalar tarixi", callback_data="history")],
        [InlineKeyboardButton(text="🆘 Yordam", callback_data="support")],
    ])
