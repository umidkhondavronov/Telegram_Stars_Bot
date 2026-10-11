from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from sqlalchemy import desc, func, or_, select

from bot.config import settings, admin_ids
from bot.database.engine import SessionLocal
from bot.database.models import (
    DepositOrder, DepositStatus, ShopOrder, ShopOrderStatus, PremiumOrder,
    Transaction, TransactionType, User, Wallet,
)
from bot.database.repository import (
    approve_deposit, change_balance, reject_deposit,
    complete_shop_order, cancel_shop_order, complete_premium_order, cancel_premium_order, get_balance,
)
from bot.keyboards.admin import (
    admin_keyboard, admin_order_keyboard, admin_order_detail_keyboard,
    admin_orders_list_keyboard, admin_deposit_list_keyboard,
    admin_deposit_detail_keyboard, admin_user_detail_keyboard, admin_premium_detail_keyboard,
)

router = Router()

class AdminBalanceState(StatesGroup):
    user_id = State()
    amount = State()

class AdminUserSearchState(StatesGroup):
    query = State()


def is_admin(uid: int) -> bool:
    return uid in admin_ids()


def money(value) -> str:
    return f"{value:,.0f} so'm"


def status_uz(status: str) -> str:
    return {
        ShopOrderStatus.PENDING.value: "🟡 Kutilmoqda",
        ShopOrderStatus.COMPLETED.value: "🟢 Bajarildi",
        ShopOrderStatus.CANCELLED.value: "🔴 Bekor qilindi",
    }.get(status, status)


@router.message(Command("admin"))
async def admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "🛠 <b>Administrator paneli</b>\n\nKerakli bo'limni tanlang:",
        reply_markup=admin_keyboard(), parse_mode="HTML"
    )


@router.callback_query(F.data == "adm:home")
async def admin_home(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("Ruxsat yo'q", show_alert=True); return
    await state.clear()
    await call.message.edit_text(
        "🛠 <b>Administrator paneli</b>\n\nKerakli bo'limni tanlang:",
        reply_markup=admin_keyboard(), parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data == "adm:stats")
async def admin_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Ruxsat yo'q", show_alert=True); return
    async with SessionLocal() as s:
        users = await s.scalar(select(func.count(User.id))) or 0
        shop_total = await s.scalar(select(func.count(ShopOrder.id))) or 0
        pending_orders = await s.scalar(select(func.count(ShopOrder.id)).where(ShopOrder.status == ShopOrderStatus.PENDING.value)) or 0
        completed_orders = await s.scalar(select(func.count(ShopOrder.id)).where(ShopOrder.status == ShopOrderStatus.COMPLETED.value)) or 0
        deposits_total = await s.scalar(select(func.count(DepositOrder.id))) or 0
        pending_deposits = await s.scalar(select(func.count(DepositOrder.id)).where(DepositOrder.status == DepositStatus.PENDING.value)) or 0
        approved_sum = await s.scalar(select(func.coalesce(func.sum(DepositOrder.amount), 0)).where(DepositOrder.status == DepositStatus.APPROVED.value)) or 0
        stars_sum = await s.scalar(select(func.coalesce(func.sum(ShopOrder.stars), 0)).where(ShopOrder.kind == "stars", ShopOrder.status == ShopOrderStatus.COMPLETED.value)) or 0
        gift_count = await s.scalar(select(func.count(ShopOrder.id)).where(ShopOrder.kind == "gift", ShopOrder.status == ShopOrderStatus.COMPLETED.value)) or 0
        premium_count = await s.scalar(select(func.count(PremiumOrder.id)).where(PremiumOrder.status == "completed")) or 0
        sales_sum = (await s.scalar(select(func.coalesce(func.sum(ShopOrder.price), 0)).where(ShopOrder.status == ShopOrderStatus.COMPLETED.value)) or 0) + (await s.scalar(select(func.coalesce(func.sum(PremiumOrder.price), 0)).where(PremiumOrder.status == "completed")) or 0)

    text = (
        "📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{users}</b>\n"
        f"📦 Jami buyurtmalar: <b>{shop_total}</b>\n"
        f"🟡 Kutilayotgan buyurtmalar: <b>{pending_orders}</b>\n"
        f"🟢 Bajarilgan buyurtmalar: <b>{completed_orders}</b>\n\n"
        f"💳 Jami to'lovlar: <b>{deposits_total}</b>\n"
        f"⏳ Kutilayotgan to'lovlar: <b>{pending_deposits}</b>\n"
        f"💰 Tasdiqlangan to'lovlar: <b>{money(approved_sum)}</b>\n\n"
        f"⭐ Sotilgan Stars: <b>{stars_sum:,}</b>\n"
        f"🎁 Bajarilgan Giftlar: <b>{gift_count}</b>\n"
        f"💎 Bajarilgan Premium: <b>{premium_count}</b>\n"
        f"💵 Bajarilgan savdo: <b>{money(sales_sum)}</b>"
    )
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:home")]])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "adm:orders")
async def admin_orders(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Ruxsat yo'q", show_alert=True); return
    async with SessionLocal() as s:
        rows = (await s.execute(
            select(ShopOrder).where(ShopOrder.status == ShopOrderStatus.PENDING.value)
            .order_by(desc(ShopOrder.created_at)).limit(20)
        )).scalars().all()
    if not rows:
        text = "📦 <b>Buyurtmalar</b>\n\n🟢 Hozircha kutilayotgan buyurtmalar yo'q."
        kb = admin_orders_list_keyboard([])
    else:
        text = "📦 <b>Kutilayotgan buyurtmalar</b>\n\nBuyurtmani tanlang:"
        kb = admin_orders_list_keyboard([r.id for r in rows])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "adm:premium_orders")
async def admin_premium_orders(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Ruxsat yo'q", show_alert=True); return
    async with SessionLocal() as s:
        rows = (await s.execute(
            select(PremiumOrder).where(PremiumOrder.status == "pending")
            .order_by(desc(PremiumOrder.created_at)).limit(20)
        )).scalars().all()
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = [[InlineKeyboardButton(text=f"💎 PR-{r.id} — {r.months} oy", callback_data=f"adm:premium:{r.id}")] for r in rows]
    buttons.append([InlineKeyboardButton(text="🔄 Yangilash", callback_data="adm:premium_orders")])
    buttons.append([InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:home")])
    text = "💎 <b>Kutilayotgan Premium buyurtmalar</b>\n\n" + ("Hozircha buyurtmalar yo'q." if not rows else "Buyurtmani tanlang:")
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("adm:premium:"))
async def admin_premium_detail(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Ruxsat yo'q", show_alert=True); return
    oid = int(call.data.rsplit(":", 1)[1])
    async with SessionLocal() as s:
        order = await s.get(PremiumOrder, oid)
        buyer = await s.get(User, order.user_id) if order else None
    if not order:
        await call.answer("Buyurtma topilmadi", show_alert=True); return
    username = f"@{buyer.username}" if buyer and buyer.username else "username yo'q"
    label = {3:"3 oy",6:"6 oy",12:"1 yil"}.get(order.months, f"{order.months} oy")
    text = (
        f"💎 <b>Premium buyurtma PR-{order.id}</b>\n\n"
        f"👤 Xaridor: <b>{buyer.first_name if buyer else 'Noma' + chr(39) + 'lum'}</b>\n"
        f"🔗 Username: <b>{username}</b>\n"
        f"🆔 Xaridor ID: <code>{order.user_id}</code>\n"
        f"💎 Premium: <b>{label}</b>\n"
        f"🎯 Qabul qiluvchi: <b>{order.recipient}</b>\n"
        f"💰 Narxi: <b>{money(order.price)}</b>\n"
        f"📌 Holat: <b>{status_uz(order.status)}</b>\n\n"
        "Premiumni qo'lda yuboring, so'ng tugmani bosing.")
    await call.message.edit_text(text, reply_markup=admin_premium_detail_keyboard(order.id), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("adm:order:"))
async def admin_order_detail(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Ruxsat yo'q", show_alert=True); return
    oid = int(call.data.rsplit(":", 1)[1])
    async with SessionLocal() as s:
        order = await s.get(ShopOrder, oid)
        buyer = await s.get(User, order.user_id) if order else None
    if not order:
        await call.answer("Buyurtma topilmadi", show_alert=True); return
    buyer_name = buyer.first_name if buyer else "Noma'lum"
    buyer_username = f"@{buyer.username}" if buyer and buyer.username else "username yo'q"
    recipient = order.recipient_username or "O'zim uchun"
    recipient_id = order.recipient_user_id or order.user_id
    text = (
        f"📦 <b>Buyurtma #{order.id}</b>\n\n"
        f"👤 Xaridor: <b>{buyer_name}</b>\n"
        f"🔗 Username: <b>{buyer_username}</b>\n"
        f"🆔 Xaridor ID: <code>{order.user_id}</code>\n\n"
        f"📦 Mahsulot: <b>{order.item_name}</b>\n"
        f"🎯 Qabul qiluvchi: <b>{recipient}</b>\n"
        f"🆔 Qabul qiluvchi ID: <code>{recipient_id}</code>\n"
        f"💰 Narxi: <b>{money(order.price)}</b>\n"
        f"📌 Holat: <b>{status_uz(order.status)}</b>"
    )
    await call.message.edit_text(text, reply_markup=admin_order_detail_keyboard(order.id), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "adm:deposits")
async def admin_deposits(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Ruxsat yo'q", show_alert=True); return
    async with SessionLocal() as s:
        rows = (await s.execute(
            select(DepositOrder).where(DepositOrder.status == DepositStatus.PENDING.value)
            .order_by(desc(DepositOrder.created_at)).limit(20)
        )).scalars().all()
    text = "💳 <b>Kutilayotgan to'lovlar</b>\n\n" + ("Hozircha to'lovlar yo'q." if not rows else "To'lovni tanlang:")
    await call.message.edit_text(text, reply_markup=admin_deposit_list_keyboard([r.id for r in rows]), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("adm:deposit:"))
async def admin_deposit_detail(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Ruxsat yo'q", show_alert=True); return
    oid = int(call.data.rsplit(":", 1)[1])
    async with SessionLocal() as s:
        order = await s.get(DepositOrder, oid)
        user = await s.get(User, order.user_id) if order else None
    if not order:
        await call.answer("To'lov topilmadi", show_alert=True); return
    username = f"@{user.username}" if user and user.username else "username yo'q"
    screenshot = "📸 Skrinshot yuborilgan" if order.screenshot_file_id else "⚠️ Skrinshot hali yo'q"
    text = (
        f"💳 <b>To'lov #{order.id}</b>\n\n"
        f"🧾 Kod: <code>{order.code}</code>\n"
        f"👤 Foydalanuvchi: <b>{user.first_name if user else 'Noma\'lum'}</b>\n"
        f"🔗 Username: <b>{username}</b>\n"
        f"🆔 ID: <code>{order.user_id}</code>\n"
        f"💰 Summa: <b>{money(order.amount)}</b>\n"
        f"📌 Holat: <b>{order.status}</b>\n"
        f"{screenshot}"
    )
    await call.message.edit_text(text, reply_markup=admin_deposit_detail_keyboard(order.id), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("adm:deposit_photo:"))
async def admin_deposit_photo(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Ruxsat yo'q", show_alert=True); return
    oid = int(call.data.rsplit(":", 1)[1])
    async with SessionLocal() as s:
        order = await s.get(DepositOrder, oid)
    if not order or not order.screenshot_file_id:
        await call.answer("Skrinshot topilmadi", show_alert=True); return
    await call.bot.send_photo(call.from_user.id, order.screenshot_file_id, caption=f"📸 To'lov #{order.id}\n🧾 Kod: {order.code}\n💰 Summa: {money(order.amount)}")
    await call.answer("Skrinshot yuborildi")


@router.callback_query(F.data == "adm:users")
async def admin_users(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("Ruxsat yo'q", show_alert=True); return
    await state.set_state(AdminUserSearchState.query)
    await call.message.edit_text("👥 <b>Foydalanuvchilar</b>\n\nTelegram ID yoki username kiriting:", parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "adm:user_search")
async def admin_user_search_again(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("Ruxsat yo'q", show_alert=True); return
    await state.set_state(AdminUserSearchState.query)
    await call.message.answer("🔎 Telegram ID yoki username kiriting:")
    await call.answer()


@router.message(AdminUserSearchState.query)
async def admin_user_search(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    q = (message.text or "").strip().lstrip("@")
    async with SessionLocal() as s:
        user = None
        if q.isdigit():
            user = await s.get(User, int(q))
        else:
            user = await s.scalar(select(User).where(User.username.ilike(q)).limit(1))
        if not user:
            await message.answer("❌ Foydalanuvchi topilmadi. ID yoki username'ni tekshiring.")
            return
        balance = await get_balance(s, user.id)
        orders = await s.scalar(select(func.count(ShopOrder.id)).where(ShopOrder.user_id == user.id)) or 0
        deposits = await s.scalar(select(func.count(DepositOrder.id)).where(DepositOrder.user_id == user.id)) or 0
    await state.clear()
    text = (
        "👤 <b>Foydalanuvchi</b>\n\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"🔗 Username: <b>@{user.username if user.username else 'yo\'q'}</b>\n"
        f"👤 Ism: <b>{user.first_name or 'yo\'q'}</b>\n"
        f"💰 Balans: <b>{money(balance)}</b>\n"
        f"📦 Buyurtmalar: <b>{orders}</b>\n"
        f"💳 To'lovlar: <b>{deposits}</b>"
    )
    await message.answer(text, reply_markup=admin_user_detail_keyboard(), parse_mode="HTML")


@router.callback_query(F.data.in_({"admin_credit", "admin_debit"}))
async def start_change(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("Ruxsat yo'q", show_alert=True); return
    await state.update_data(action="credit" if call.data == "admin_credit" else "debit")
    await state.set_state(AdminBalanceState.user_id)
    await call.message.answer("Foydalanuvchining Telegram ID raqamini kiriting:")
    await call.answer()


@router.message(AdminBalanceState.user_id)
async def get_uid(message: Message, state: FSMContext):
    try:
        uid = int((message.text or "").strip())
    except ValueError:
        await message.answer("❌ Telegram ID noto'g'ri."); return
    await state.update_data(user_id=uid); await state.set_state(AdminBalanceState.amount)
    await message.answer("Summani so'mda kiriting:")


@router.message(AdminBalanceState.amount)
async def get_amount(message: Message, state: FSMContext):
    d = await state.get_data()
    try:
        amount = Decimal((message.text or "").replace(" ", "").replace(",", "."))
        if amount <= 0: raise ValueError
    except (InvalidOperation, ValueError, AttributeError):
        await message.answer("❌ Musbat summani kiriting, masalan: 225000"); return
    try:
        async with SessionLocal() as s:
            b = await change_balance(
                s, d["user_id"], amount,
                TransactionType.CREDIT if d["action"] == "credit" else TransactionType.DEBIT,
                "Administrator tomonidan balans o'zgartirildi"
            )
    except ValueError as e:
        await message.answer(str(e)); return
    await state.clear()
    await message.answer(f"✅ Tayyor. Yangi balans: <b>{money(b)}</b>", parse_mode="HTML")


@router.callback_query(F.data.startswith("deposit_approve:"))
async def deposit_approve_handler(call: CallbackQuery):
    if not is_admin(call.from_user.id): await call.answer("Ruxsat yo'q", show_alert=True); return
    order_id = int(call.data.split(":")[1])
    try:
        async with SessionLocal() as s: order, new_balance = await approve_deposit(s, order_id)
    except ValueError as e: await call.answer(str(e), show_alert=True); return
    caption = (call.message.caption or "") + f"\n\n✅ <b>TASDIQLANDI</b>\nFoydalanuvchi balansi: <b>{money(new_balance)}</b>"
    if call.message.photo:
        await call.message.edit_caption(caption=caption, reply_markup=None, parse_mode="HTML")
    else:
        await call.message.edit_text(caption, reply_markup=None, parse_mode="HTML")
    try:
        await call.bot.send_message(order.user_id, f"✅ <b>Balans to'ldirildi!</b>\n\n🧾 Kod: <code>{order.code}</code>\n💰 Qo'shildi: <b>{money(order.amount)}</b>\n💳 Yangi balans: <b>{money(new_balance)}</b>", parse_mode="HTML")
    except Exception: pass
    await call.answer("To'lov tasdiqlandi")


@router.callback_query(F.data.startswith("deposit_reject:"))
async def deposit_reject_handler(call: CallbackQuery):
    if not is_admin(call.from_user.id): await call.answer("Ruxsat yo'q", show_alert=True); return
    order_id = int(call.data.split(":")[1])
    try:
        async with SessionLocal() as s: order = await reject_deposit(s, order_id)
    except ValueError as e: await call.answer(str(e), show_alert=True); return
    caption = (call.message.caption or "") + "\n\n❌ <b>RAD ETILDI</b>"
    if call.message.photo:
        await call.message.edit_caption(caption=caption, reply_markup=None, parse_mode="HTML")
    else:
        await call.message.edit_text(caption, reply_markup=None, parse_mode="HTML")
    try:
        await call.bot.send_message(order.user_id, f"❌ <b>Balansni to'ldirish rad etildi</b>\n\n🧾 Kod: <code>{order.code}</code>\n💰 Summa: <b>{money(order.amount)}</b>", parse_mode="HTML")
    except Exception: pass
    await call.answer("To'lov rad etildi")


@router.callback_query(F.data.startswith("order_complete:"))
async def order_complete(call: CallbackQuery):
    if not is_admin(call.from_user.id): await call.answer("Ruxsat yo'q", show_alert=True); return
    order_id = int(call.data.split(":")[1])
    try:
        async with SessionLocal() as s: order = await complete_shop_order(s, order_id)
    except ValueError as e: await call.answer(str(e), show_alert=True); return
    await call.message.edit_text((call.message.text or "") + "\n\n✅ <b>BAJARILDI</b>", reply_markup=None, parse_mode="HTML")
    try:
        recipient = order.recipient_username or "O'zim uchun"
        await call.bot.send_message(order.user_id, f"✅ <b>Buyurtma #{order.id} bajarildi!</b>\n\n📦 {order.item_name}\n🎯 Qabul qiluvchi: <b>{recipient}</b>", parse_mode="HTML")
    except Exception: pass
    await call.answer("Buyurtma bajarildi")


@router.callback_query(F.data.startswith("order_cancel:"))
async def order_cancel(call: CallbackQuery):
    if not is_admin(call.from_user.id): await call.answer("Ruxsat yo'q", show_alert=True); return
    order_id = int(call.data.split(":")[1])
    try:
        async with SessionLocal() as s: order, new_balance = await cancel_shop_order(s, order_id)
    except ValueError as e: await call.answer(str(e), show_alert=True); return
    await call.message.edit_text((call.message.text or "") + f"\n\n❌ <b>BEKOR QILINDI</b>\n💰 Qaytarildi: <b>{money(order.price)}</b>", reply_markup=None, parse_mode="HTML")
    try:
        await call.bot.send_message(order.user_id, f"❌ <b>Buyurtma #{order.id} bekor qilindi</b>\n\n📦 {order.item_name}\n💰 Qaytarildi: <b>{money(order.price)}</b>\n💳 Yangi balans: <b>{money(new_balance)}</b>", parse_mode="HTML")
    except Exception: pass
    await call.answer("Buyurtma bekor qilindi, pul qaytarildi")


@router.callback_query(F.data.startswith("premium_complete:"))
async def premium_complete(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Ruxsat yo'q", show_alert=True); return
    order_id = int(call.data.split(":")[1])
    try:
        async with SessionLocal() as s:
            order = await complete_premium_order(s, order_id)
    except ValueError as e:
        await call.answer(str(e), show_alert=True); return
    await call.message.edit_text((call.message.text or "") + "\n\n✅ <b>PREMIUM YUBORILDI VA BUYURTMA BAJARILDI</b>", reply_markup=None, parse_mode="HTML")
    try:
        label = {3:"3 oy",6:"6 oy",12:"1 yil"}.get(order.months, f"{order.months} oy")
        await call.bot.send_message(order.user_id, f"✅ <b>Premium buyurtmangiz bajarildi!</b>\n\n💎 Premium: <b>{label}</b>\n🎯 Qabul qiluvchi: <b>{order.recipient}</b>\n🧾 Buyurtma: <code>PR-{order.id}</code>", parse_mode="HTML")
    except Exception:
        pass
    await call.answer("Premium buyurtmasi bajarildi")

@router.callback_query(F.data.startswith("premium_cancel:"))
async def premium_cancel(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Ruxsat yo'q", show_alert=True); return
    order_id = int(call.data.split(":")[1])
    try:
        async with SessionLocal() as s:
            order, new_balance = await cancel_premium_order(s, order_id)
    except ValueError as e:
        await call.answer(str(e), show_alert=True); return
    await call.message.edit_text((call.message.text or "") + f"\n\n❌ <b>BEKOR QILINDI</b>\n💰 Qaytarildi: <b>{money(order.price)}</b>", reply_markup=None, parse_mode="HTML")
    try:
        await call.bot.send_message(order.user_id, f"❌ <b>Premium buyurtmangiz bekor qilindi</b>\n\n🧾 Buyurtma: <code>PR-{order.id}</code>\n💰 Qaytarildi: <b>{money(order.price)}</b>\n💳 Yangi balans: <b>{money(new_balance)}</b>", parse_mode="HTML")
    except Exception:
        pass
    await call.answer("Premium bekor qilindi, pul qaytarildi")
