from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

PACKAGES = {
    50: 11000, 100: 22000, 200: 43000, 300: 65000,
    500: 115000, 1000: 225000, 2000: 560000,
}
GIFTS = {
    "teddy": ("🧸", "Ayiqcha", 2600), "heart": ("💖", "Yurak", 2600),
    "gift": ("🎁", "Sovg'a", 4325), "rose": ("🌹", "Atirgul", 4325),
    "cake": ("🎂", "Tort", 8650), "bouquet": ("💐", "Guldasta", 8650),
    "rocket": ("🚀", "Raketa", 8650), "trophy": ("🏆", "Kubok", 17300),
    "ring": ("💍", "Uzuk", 17300), "diamond": ("💎", "Olmos", 17300),
}

def recipient_keyboard(prefix):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 O'zim uchun", callback_data=f"{prefix}:self")],
        [InlineKeyboardButton(text="🔎 Boshqa foydalanuvchiga", callback_data=f"{prefix}:other")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back")],
    ])

def stars_keyboard(packages=None):
    packages = packages or PACKAGES
    rows = [[InlineKeyboardButton(text=f"⭐ {s:,} — {p:,} so'm", callback_data=f"starbuy:{s}")]
            for s, p in packages.items()]
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="stars")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def gifts_keyboard(gifts=None):
    gifts = gifts or GIFTS
    rows = []
    items = list(gifts.items())
    for i in range(0, len(items), 2):
        rows.append([
            InlineKeyboardButton(text=f"{e} {n} — {p:,} so'm", callback_data=f"giftbuy:{k}")
            for k, (e, n, p) in items[i:i+2]
        ])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="gifts")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def confirm_keyboard(kind, key):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"confirm:{kind}:{key}")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel:{kind}")],
    ])
