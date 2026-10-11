from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="adm:stats")],
        [InlineKeyboardButton(text="📦 Buyurtmalar", callback_data="adm:orders")],
        [InlineKeyboardButton(text="💎 Premium buyurtmalar", callback_data="adm:premium_orders")],
        [InlineKeyboardButton(text="💳 To'lovlar", callback_data="adm:deposits")],
        [InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="adm:users")],
        [InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="adm:settings")],
        [InlineKeyboardButton(text="➕ Balansga qo'shish", callback_data="admin_credit")],
        [InlineKeyboardButton(text="➖ Balansdan ayirish", callback_data="admin_debit")],
        [InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="back")],
    ])


def admin_order_keyboard(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Bajarildi", callback_data=f"order_complete:{order_id}")],
        [InlineKeyboardButton(text="❌ Bekor qilish va qaytarish", callback_data=f"order_cancel:{order_id}")],
    ])


def admin_orders_list_keyboard(order_ids):
    rows = [[InlineKeyboardButton(text=f"📦 #{oid}", callback_data=f"adm:order:{oid}")] for oid in order_ids]
    rows.append([InlineKeyboardButton(text="🔄 Yangilash", callback_data="adm:orders")])
    rows.append([InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_premium_detail_keyboard(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Bajarildi", callback_data=f"premium_complete:{order_id}")],
        [InlineKeyboardButton(text="❌ Bekor qilish va qaytarish", callback_data=f"premium_cancel:{order_id}")],
        [InlineKeyboardButton(text="⬅️ Premium buyurtmalar", callback_data="adm:premium_orders")],
    ])


def admin_order_detail_keyboard(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Bajarildi", callback_data=f"order_complete:{order_id}")],
        [InlineKeyboardButton(text="❌ Bekor qilish va qaytarish", callback_data=f"order_cancel:{order_id}")],
        [InlineKeyboardButton(text="⬅️ Buyurtmalar", callback_data="adm:orders")],
    ])


def admin_deposit_list_keyboard(order_ids):
    rows = [[InlineKeyboardButton(text=f"💳 #{oid}", callback_data=f"adm:deposit:{oid}")] for oid in order_ids]
    rows.append([InlineKeyboardButton(text="🔄 Yangilash", callback_data="adm:deposits")])
    rows.append([InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_deposit_detail_keyboard(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Skrinshotni ko'rish", callback_data=f"adm:deposit_photo:{order_id}")],
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"deposit_approve:{order_id}")],
        [InlineKeyboardButton(text="❌ Rad etish", callback_data=f"deposit_reject:{order_id}")],
        [InlineKeyboardButton(text="⬅️ To'lovlar", callback_data="adm:deposits")],
    ])


def admin_user_detail_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 Boshqa foydalanuvchi", callback_data="adm:user_search")],
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:home")],
    ])
