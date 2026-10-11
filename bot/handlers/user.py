from decimal import Decimal, InvalidOperation
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from bot.config import settings, admin_ids
from bot.database.engine import SessionLocal
from bot.database.repository import (
    attach_deposit_screenshot, create_deposit_order, create_shop_order,
    get_balance, get_recent_orders, get_recent_transactions, get_setting,
)
from bot.keyboards.main import main_keyboard
from bot.keyboards.stars import GIFTS, PACKAGES, confirm_keyboard, gifts_keyboard, recipient_keyboard, stars_keyboard
from bot.keyboards.deposit import deposit_cancel_keyboard

router = Router()

class DepositState(StatesGroup):
    amount = State()
    screenshot = State()

class PurchaseState(StatesGroup):
    stars_recipient = State()
    gift_recipient = State()

def _recipient_text(username: str | None, user_id: int | None = None) -> str:
    if username:
        return f"👤 {username}"
    return "👤 O'zim uchun"

def _money(value):
    return f"{value:,.0f} so'm"

def _parse_stars_prices(raw):
    from bot.keyboards.stars import PACKAGES
    if not raw:
        return PACKAGES
    try:
        result = {}
        for part in raw.split(","):
            k, v = part.split("=", 1)
            result[int(k.strip())] = int(v.strip())
        return result or PACKAGES
    except Exception:
        return PACKAGES

def _parse_gift_prices(raw):
    from bot.keyboards.stars import GIFTS
    if not raw:
        return GIFTS
    try:
        result = dict(GIFTS)
        for part in raw.split(","):
            k, v = part.split("=", 1)
            if k.strip() in result:
                e, n, _ = result[k.strip()]
                result[k.strip()] = (e, n, int(v.strip()))
        return result
    except Exception:
        return GIFTS

async def _stars_prices():
    async with SessionLocal() as s:
        raw = await get_setting(s, "stars_prices")
    return _parse_stars_prices(raw)

async def _gift_prices():
    async with SessionLocal() as s:
        raw = await get_setting(s, "gift_prices")
    return _parse_gift_prices(raw)

async def _payment_details():
    async with SessionLocal() as s:
        card = await get_setting(s, "payment_card", settings.payment_card)
        name = await get_setting(s, "payment_name", settings.payment_name)
    return card, name

@router.callback_query(F.data == "back")
async def back(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("🏠 <b>Asosiy menyu</b>\n\nKerakli bo'limni tanlang:", reply_markup=main_keyboard(), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "balance")
async def balance(call: CallbackQuery):
    async with SessionLocal() as s:
        b = await get_balance(s, call.from_user.id)
    await call.message.edit_text(f"💰 Balansingiz: <b>{_money(b)}</b>", reply_markup=main_keyboard(), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "profile")
async def profile(call: CallbackQuery):
    await call.message.edit_text(
        f"👤 <b>Profilim</b>\n\n"
        f"🆔 ID: <code>{call.from_user.id}</code>\n"
        f"🔗 Username: @{call.from_user.username or 'yo\'q'}\n"
        f"👤 Ism: {call.from_user.first_name or 'yo\'q'}",
        reply_markup=main_keyboard(), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "history")
async def history(call: CallbackQuery):
    async with SessionLocal() as s:
        rows = await get_recent_transactions(s, call.from_user.id)
    if not rows:
        text = "📜 <b>Operatsiyalar tarixi</b>\n\nHozircha operatsiyalar yo'q."
    else:
        lines = []
        for r in rows:
            sign = "+" if r.type == "credit" else "-"
            lines.append(f"{sign}{_money(r.amount)} — {r.description}")
        text = "📜 <b>Operatsiyalar tarixi</b>\n\n" + "\n".join(lines)
    await call.message.edit_text(text, reply_markup=main_keyboard(), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "orders")
async def orders(call: CallbackQuery):
    async with SessionLocal() as s:
        rows = await get_recent_orders(s, call.from_user.id)
    if not rows:
        text = "📦 <b>Buyurtmalarim</b>\n\nHozircha buyurtmalar yo'q."
    else:
        lines = []
        status_map = {"pending": "⏳ Kutilmoqda", "completed": "✅ Bajarildi", "cancelled": "❌ Bekor qilindi"}
        for _, label, price, status, recipient in rows:
            target = recipient or "O'zim uchun"
            lines.append(f"• {label} → {target}\n  {_money(price)} — {status_map.get(status, status)}")
        text = "📦 <b>Buyurtmalarim</b>\n\n" + "\n".join(lines)
    await call.message.edit_text(text, reply_markup=main_keyboard(), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "support")
async def support(call: CallbackQuery):
    await call.message.edit_text(
        "🆘 <b>Yordam markazi</b>\n\n"
        "💳 <b>To'lov bo'yicha muammo</b>\n"
        "To'lov qilgan bo'lsangiz, chek yoki skrinshotni yuboring. "
        "Administrator to'lovni tekshiradi va tasdiqlagandan so'ng balansingiz to'ldiriladi.\n\n"
        "📦 <b>Buyurtma bo'yicha muammo</b>\n"
        "Buyurtma holati yoki yetkazib berish bo'yicha savol bo'lsa, "
        "buyurtma kodini yuboring.\n\n"
        "👨‍💼 <b>Administrator</b>\n"
        "🔹 @frrej — asosiy yordam va buyurtmalar\n\n"
        "⚠️ Murojaatda imkon qadar <b>buyurtma kodini</b> va kerakli skrinshotni yuboring.",
        reply_markup=main_keyboard(), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "deposit")
async def deposit(call: CallbackQuery, state: FSMContext):
    await state.clear(); await state.set_state(DepositState.amount)
    await call.message.edit_text(
        "💳 <b>Balansni to'ldirish</b>\n\n"
        "Qancha summa kiritmoqchi ekaningizni yozing.\n"
        "🔽 Eng kam: <b>1 000 so'm</b>\n"
        "🔼 Eng ko'p: <b>2 500 000 so'm</b>\n\n"
        "Buyurtma yaratilgach, to'lov rekvizitlari chiqadi. To'lovdan keyin skrinshotni shu yerga yuborasiz.",
        reply_markup=deposit_cancel_keyboard(), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "deposit_cancel")
async def deposit_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("🏠 <b>Asosiy menyu</b>\n\nKerakli bo'limni tanlang:", reply_markup=main_keyboard(), parse_mode="HTML")
    await call.answer()

@router.message(DepositState.amount)
async def deposit_amount(message: Message, state: FSMContext):
    try:
        amount = Decimal((message.text or "").replace(" ", "").replace(",", "."))
        if amount != amount.to_integral_value() or amount < Decimal("1000") or amount > Decimal("2500000"):
            raise ValueError
    except (InvalidOperation, ValueError, AttributeError):
        await message.answer("❌ <b>1 000</b> dan <b>2 500 000 so'mgacha</b> bo'lgan butun summani kiriting.", parse_mode="HTML")
        return
    async with SessionLocal() as s:
        order = await create_deposit_order(s, message.from_user.id, amount)
    await state.update_data(deposit_order_id=order.id); await state.set_state(DepositState.screenshot)
    await message.answer(
        f"✅ <b>Balansni to'ldirish buyurtmasi yaratildi</b>\n\n"
        f"🧾 Buyurtma kodi: <code>{order.code}</code>\n"
        f"💰 Summa: <b>{_money(amount)}</b>\n\n"
        f"💳 Quyidagi karta raqamiga <b>{_money(amount)}</b> o'tkazing:\n"
        f"<code>{(await _payment_details())[0]}</code>\n"
        f"👤 Qabul qiluvchi: <b>{(await _payment_details())[1]}</b>\n\n"
        "⚠️ To'lovdan keyin <b>skrinshotni shu yerga yuboring</b>.\n"
        "Administrator to'lovni qo'lda tekshiradi va tasdiqlagandan keyin pul balansingizga tushadi.",
        reply_markup=deposit_cancel_keyboard(), parse_mode="HTML")

@router.message(DepositState.screenshot, F.photo)
async def deposit_screenshot(message: Message, state: FSMContext):
    data = await state.get_data(); order_id = data.get("deposit_order_id")
    if not order_id:
        await state.clear(); await message.answer("❌ Buyurtma topilmadi. Balansni to'ldirishni qaytadan boshlang.", reply_markup=main_keyboard()); return
    file_id = message.photo[-1].file_id
    async with SessionLocal() as s:
        try: order = await attach_deposit_screenshot(s, int(order_id), file_id)
        except ValueError:
            await state.clear(); await message.answer("❌ Bu buyurtma allaqachon ko'rib chiqilgan.", reply_markup=main_keyboard()); return
    await state.clear()
    await message.answer(
        f"📨 <b>Skrinshot qabul qilindi</b>\n\n"
        f"🧾 Kod: <code>{order.code}</code>\n"
        f"💰 Summa: <b>{_money(order.amount)}</b>\n\n"
        "⏳ Administrator tekshiruvini kuting. Tasdiqlangandan so'ng balansingiz to'ldiriladi.",
        reply_markup=main_keyboard(), parse_mode="HTML")
    username = f"@{message.from_user.username}" if message.from_user.username else "username yo'q"
    caption = (
        "💳 <b>YANGI BALANS TO'LDIRISH</b>\n\n"
        f"🧾 Kod: <code>{order.code}</code>\n"
        f"👤 Foydalanuvchi: {message.from_user.full_name}\n"
        f"🔗 Username: {username}\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"💰 Summa: <b>{_money(order.amount)}</b>\n\n"
        "Skrinshotni tekshirib, kerakli amalni tanlang:")
    from bot.keyboards.deposit import admin_deposit_keyboard
    for admin_id in admin_ids():
        await message.bot.send_photo(admin_id, file_id, caption=caption, reply_markup=admin_deposit_keyboard(order.id), parse_mode="HTML")

@router.message(DepositState.screenshot)
async def deposit_screenshot_wrong_type(message: Message):
    await message.answer("📸 Iltimos, <b>to'lov skrinshotini rasm sifatida</b> yuboring.", parse_mode="HTML")

# Stars
@router.callback_query(F.data == "stars")
async def stars(call, state):
    await state.clear(); await call.message.edit_text("⭐ <b>Stars kimga yuboriladi?</b>", reply_markup=recipient_keyboard("stars_to"), parse_mode="HTML"); await call.answer()

@router.callback_query(F.data == "stars_to:self")
async def stars_self(call, state):
    await state.clear(); await state.update_data(recipient_username=None, recipient_user_id=call.from_user.id)
    await call.message.edit_text("⭐ <b>Stars paketini tanlang:</b>", reply_markup=stars_keyboard(await _stars_prices()), parse_mode="HTML"); await call.answer()

@router.callback_query(F.data == "stars_to:other")
async def stars_other(call, state):
    await state.clear(); await state.set_state(PurchaseState.stars_recipient)
    await call.message.edit_text("⭐ <b>Qabul qiluvchining username'ini kiriting</b>\n\nMasalan: <code>@username</code>", parse_mode="HTML"); await call.answer()

@router.message(PurchaseState.stars_recipient)
async def stars_recipient(message, state):
    username = (message.text or "").strip(); username = username if username.startswith("@") else "@" + username
    if len(username) < 2 or " " in username or len(username) > 33:
        await message.answer("❌ To'g'ri username kiriting, masalan <code>@username</code>.", parse_mode="HTML"); return
    await state.update_data(recipient_username=username, recipient_user_id=None); await state.set_state(None)
    await message.answer("⭐ <b>Stars paketini tanlang:</b>", reply_markup=stars_keyboard(await _stars_prices()), parse_mode="HTML")

@router.callback_query(F.data.startswith("starbuy:"))
async def star_preview(call, state):
    stars_count = int(call.data.split(":")[1]); packages = await _stars_prices(); price = Decimal(packages[stars_count]); data = await state.get_data()
    if "recipient_username" not in data: data = {"recipient_username": None, "recipient_user_id": call.from_user.id}
    async with SessionLocal() as s: b = await get_balance(s, call.from_user.id)
    if b < price:
        await call.answer(f"Mablag' yetarli emas. Balans: {_money(b)}", show_alert=True); return
    recipient = _recipient_text(data.get("recipient_username"))
    await state.update_data(kind="stars", item_key=str(stars_count), item_name=f"⭐ {stars_count:,} Stars", stars=stars_count, price=str(price), recipient_username=data.get("recipient_username"), recipient_user_id=data.get("recipient_user_id"))
    await call.message.edit_text(f"⭐ <b>{stars_count:,} Stars</b>\n{recipient}\n\n💵 Narx: <b>{_money(price)}</b>\n💰 Balans: <b>{_money(b)}</b>\n\nBuyurtmani tasdiqlaysizmi?", reply_markup=confirm_keyboard("stars", str(stars_count)), parse_mode="HTML"); await call.answer()

# Gifts
@router.callback_query(F.data == "gifts")
async def gifts(call, state):
    await state.clear(); await call.message.edit_text("🎁 <b>Sovg'a kimga yuboriladi?</b>", reply_markup=recipient_keyboard("gift_to"), parse_mode="HTML"); await call.answer()

@router.callback_query(F.data == "gift_to:self")
async def gift_self(call, state):
    await state.clear(); await state.update_data(recipient_username=None, recipient_user_id=call.from_user.id)
    await call.message.edit_text("🎁 <b>Sovg'ani tanlang:</b>", reply_markup=gifts_keyboard(await _gift_prices()), parse_mode="HTML"); await call.answer()

@router.callback_query(F.data == "gift_to:other")
async def gift_other(call, state):
    await state.clear(); await state.set_state(PurchaseState.gift_recipient)
    await call.message.edit_text("🎁 <b>Qabul qiluvchining username'ini kiriting</b>\n\nMasalan: <code>@username</code>", parse_mode="HTML"); await call.answer()

@router.message(PurchaseState.gift_recipient)
async def gift_recipient(message, state):
    username = (message.text or "").strip(); username = username if username.startswith("@") else "@" + username
    if len(username) < 2 or " " in username or len(username) > 33:
        await message.answer("❌ To'g'ri username kiriting, masalan <code>@username</code>.", parse_mode="HTML"); return
    await state.update_data(recipient_username=username, recipient_user_id=None); await state.set_state(None)
    await message.answer("🎁 <b>Sovg'ani tanlang:</b>", reply_markup=gifts_keyboard(await _gift_prices()), parse_mode="HTML")

@router.callback_query(F.data.startswith("giftbuy:"))
async def gift_preview(call, state):
    key = call.data.split(":", 1)[1]; gifts = await _gift_prices(); emoji, name, price_int = gifts[key]; price = Decimal(price_int); data = await state.get_data()
    if "recipient_username" not in data: data = {"recipient_username": None, "recipient_user_id": call.from_user.id}
    async with SessionLocal() as s: b = await get_balance(s, call.from_user.id)
    if b < price:
        await call.answer(f"Mablag' yetarli emas. Balans: {_money(b)}", show_alert=True); return
    await state.update_data(kind="gift", item_key=key, item_name=f"{emoji} {name}", stars=None, price=str(price), recipient_username=data.get("recipient_username"), recipient_user_id=data.get("recipient_user_id"))
    await call.message.edit_text(f"🎁 <b>{emoji} {name}</b>\n{_recipient_text(data.get('recipient_username'))}\n\n💵 Narx: <b>{_money(price)}</b>\n💰 Balans: <b>{_money(b)}</b>\n\nBuyurtmani tasdiqlaysizmi?", reply_markup=confirm_keyboard("gift", key), parse_mode="HTML"); await call.answer()

@router.callback_query(F.data.startswith("confirm:"))
async def confirm_purchase(call, state):
    _, kind, key = call.data.split(":", 2); data = await state.get_data()
    if data.get("kind") != kind or data.get("item_key") != key:
        await call.answer("Buyurtma eskirgan. Qaytadan boshlang.", show_alert=True); return
    price = Decimal(data["price"])
    try:
        async with SessionLocal() as s:
            order, new_balance = await create_shop_order(s, call.from_user.id, kind, key, data["item_name"], data.get("stars"), price, data.get("recipient_user_id"), data.get("recipient_username"))
    except ValueError:
        await call.answer("Mablag' yetarli emas.", show_alert=True); return
    recipient = _recipient_text(data.get("recipient_username"), data.get("recipient_user_id")); await state.clear()
    await call.message.edit_text(
        f"✅ <b>Buyurtma #{order.id} yaratildi!</b>\n\n{data['item_name']}\n{recipient}\n💰 Sarflandi: <b>{_money(price)}</b>\n💳 Yangi balans: <b>{_money(new_balance)}</b>\n\n⏳ Holat: <b>Kutilmoqda</b>. Administrator buyurtmani qo'lda bajaradi.",
        reply_markup=main_keyboard(), parse_mode="HTML")
    await call.answer("Buyurtma yaratildi")
    from bot.keyboards.admin import admin_order_keyboard
    username = f"@{call.from_user.username}" if call.from_user.username else "username yo'q"
    target_username = data.get("recipient_username") or username
    target_id = data.get("recipient_user_id") or call.from_user.id
    admin_text = (
        "🛒 <b>YANGI BUYURTMA</b>\n\n"
        f"🧾 Buyurtma: <code>#{order.id}</code>\n"
        f"👤 Xaridor: {call.from_user.full_name}\n"
        f"🔗 Xaridor username: {username}\n"
        f"🆔 Xaridor ID: <code>{call.from_user.id}</code>\n"
        f"📦 Mahsulot: <b>{data['item_name']}</b>\n"
        f"🎯 Qabul qiluvchi: <b>{target_username}</b>\n"
        f"🆔 Qabul qiluvchi ID: <code>{target_id}</code>\n"
        f"💰 Summa: <b>{_money(price)}</b>\n\n"
        "Mahsulotni qo'lda yuboring. So'ng buyurtmani bajaring yoki bekor qiling.")
    for admin_id in admin_ids():
        await call.bot.send_message(admin_id, admin_text, reply_markup=admin_order_keyboard(order.id), parse_mode="HTML")

@router.callback_query(F.data.startswith("cancel:"))
async def cancel_purchase(call, state):
    kind = call.data.split(":", 1)[1]; await state.clear()
    if kind == "stars":
        await call.message.edit_text("⭐ <b>Stars kimga yuboriladi?</b>", reply_markup=recipient_keyboard("stars_to"), parse_mode="HTML")
    else:
        await call.message.edit_text("🎁 <b>Sovg'a kimga yuboriladi?</b>", reply_markup=recipient_keyboard("gift_to"), parse_mode="HTML")
    await call.answer()
