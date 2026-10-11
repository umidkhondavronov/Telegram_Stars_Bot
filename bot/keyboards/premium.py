from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
DEFAULT_PREMIUM={3:160000,6:220000,12:380000}
def premium_keyboard(prices=None):
    prices=prices or DEFAULT_PREMIUM
    labels={3:"3 oy",6:"6 oy",12:"1 yil"}
    rows=[[InlineKeyboardButton(text=f"💎 {labels.get(m,str(m)+' oy')} — {p:,} so'm",callback_data=f"premium:{m}")] for m,p in prices.items()]
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga",callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
def recipient_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 O'zim uchun",callback_data="premium_self")],
        [InlineKeyboardButton(text="👤 Boshqa kishiga",callback_data="premium_other")],
        [InlineKeyboardButton(text="⬅️ Orqaga",callback_data="back")]])
def confirm_keyboard(months):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash",callback_data=f"premium_confirm:{months}")],
        [InlineKeyboardButton(text="❌ Bekor qilish",callback_data="back")]])
