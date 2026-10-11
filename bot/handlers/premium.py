from decimal import Decimal
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from bot.config import settings, admin_ids
from bot.database.engine import SessionLocal
from bot.database.models import PremiumOrder, Transaction, Wallet, TransactionType
from bot.database.repository import get_balance, get_setting
from bot.keyboards.main import main_keyboard
from bot.keyboards.premium import DEFAULT_PREMIUM, premium_keyboard, recipient_keyboard, confirm_keyboard
from bot.keyboards.admin import admin_premium_detail_keyboard

router = Router()

class PremiumState(StatesGroup):
    recipient = State()

PREMIUM_LABELS = {3: "3 oy", 6: "6 oy", 12: "1 yil"}

def _parse_prices(raw):
    if not raw:
        return DEFAULT_PREMIUM
    try:
        result = {}
        for part in raw.split(","):
            k, v = part.split("=", 1)
            result[int(k.strip())] = int(v.strip())
        return result or DEFAULT_PREMIUM
    except Exception:
        return DEFAULT_PREMIUM

async def _prices():
    async with SessionLocal() as s:
        raw = await get_setting(s, "premium_prices")
    return _parse_prices(raw)

def _money(value):
    return f"{value:,.0f} so'm"

@router.callback_query(F.data == "premium_buy")
async def premium_buy(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(
        "💎 <b>Telegram Premium</b>\n\nKim uchun Premium olmoqchisiz?",
        reply_markup=recipient_keyboard(), parse_mode="HTML"
    )
    await call.answer()

@router.callback_query(F.data == "premium_self")
async def premium_self(call: CallbackQuery, state: FSMContext):
    await state.clear()
    recipient = f"@{call.from_user.username}" if call.from_user.username else str(call.from_user.id)
    await state.update_data(recipient=recipient, recipient_id=call.from_user.id)
    await state.set_state(PremiumState.recipient)
    await call.message.edit_text(
        "💎 <b>Premium muddatini tanlang:</b>",
        reply_markup=premium_keyboard(await _prices()), parse_mode="HTML"
    )
    await call.answer()

@router.callback_query(F.data == "premium_other")
async def premium_other(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(PremiumState.recipient)
    await state.update_data(recipient_id=None)
    await call.message.edit_text(
        "👤 <b>Premium kimga yuboriladi?</b>\n\nUsername yuboring, masalan: <code>@username</code>",
        parse_mode="HTML"
    )
    await call.answer()

@router.message(PremiumState.recipient)
async def premium_recipient(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("recipient"):
        username = (message.text or "").strip()
        if not username.startswith("@"):
            username = "@" + username
        if len(username) < 2 or len(username) > 33 or " " in username or "@" in username[1:]:
            await message.answer("❌ To'g'ri username kiriting, masalan <code>@username</code>.", parse_mode="HTML")
            return
        await state.update_data(recipient=username, recipient_id=None)
    await message.answer(
        "💎 <b>Premium muddatini tanlang:</b>",
        reply_markup=premium_keyboard(await _prices()), parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("premium:"))
async def premium_preview(call: CallbackQuery, state: FSMContext):
    try:
        months = int(call.data.split(":", 1)[1])
    except ValueError:
        await call.answer("Noto'g'ri muddat.", show_alert=True)
        return
    prices = await _prices()
    if months not in prices:
        await call.answer("Bu Premium muddati mavjud emas.", show_alert=True)
        return
    price = Decimal(prices[months])
    data = await state.get_data()
    recipient = data.get("recipient")
    if not recipient:
        recipient = f"@{call.from_user.username}" if call.from_user.username else str(call.from_user.id)
        await state.update_data(recipient=recipient, recipient_id=call.from_user.id)
        data = await state.get_data()
    async with SessionLocal() as s:
        balance = await get_balance(s, call.from_user.id)
    if balance < price:
        await call.answer(f"Balansingiz yetarli emas: {_money(balance)}", show_alert=True)
        return
    await state.update_data(months=months, price=int(price))
    await call.message.edit_text(
        f"💎 <b>Premium buyurtmasi</b>\n\n"
        f"💎 Muddat: <b>{PREMIUM_LABELS.get(months, str(months) + ' oy')}</b>\n"
        f"🎯 Qabul qiluvchi: <b>{recipient}</b>\n"
        f"💰 Narxi: <b>{_money(price)}</b>\n"
        f"💳 Balansingiz: <b>{_money(balance)}</b>\n\n"
        "Tasdiqlaysizmi?",
        reply_markup=confirm_keyboard(months), parse_mode="HTML"
    )
    await call.answer()

@router.callback_query(F.data.startswith("premium_confirm:"))
async def premium_confirm(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    try:
        months = int(call.data.split(":", 1)[1])
        price = Decimal(data["price"])
    except (ValueError, KeyError):
        await call.answer("Buyurtma eskirgan. Qaytadan boshlang.", show_alert=True)
        return
    recipient = data.get("recipient")
    recipient_id = data.get("recipient_id")
    if not recipient:
        await call.answer("Qabul qiluvchini tanlang.", show_alert=True)
        return
    async with SessionLocal() as s:
        wallet = await s.get(Wallet, call.from_user.id, with_for_update=True)
        if not wallet or wallet.balance < price:
            await call.answer("Balansingiz yetarli emas.", show_alert=True)
            return
        wallet.balance -= price
        order = PremiumOrder(
            user_id=call.from_user.id, months=months, price=price,
            recipient=recipient, recipient_id=recipient_id, status="pending"
        )
        s.add(order)
        await s.flush()
        s.add(Transaction(
            user_id=call.from_user.id, amount=price,
            type=TransactionType.DEBIT.value,
            description=f"Telegram Premium {months} oy"
        ))
        new_balance = wallet.balance
        await s.commit()
        order_id = order.id
    await state.clear()
    label = PREMIUM_LABELS.get(months, f"{months} oy")
    await call.message.edit_text(
        f"✅ <b>Premium buyurtmasi #{order_id} yaratildi!</b>\n\n"
        f"💎 Muddat: <b>{label}</b>\n"
        f"🎯 Qabul qiluvchi: <b>{recipient}</b>\n"
        f"💰 Sarflandi: <b>{_money(price)}</b>\n"
        f"💳 Yangi balans: <b>{_money(new_balance)}</b>\n\n"
        "⏳ Administrator Premiumni qo'lda yuboradi. Buyurtma bajarilgach sizga xabar beriladi.",
        reply_markup=main_keyboard(), parse_mode="HTML"
    )
    try:
        username = f"@{call.from_user.username}" if call.from_user.username else "username yo'q"
        for admin_id in admin_ids():
            await call.bot.send_message(
                admin_id,
                f"💎 <b>YANGI PREMIUM BUYURTMA</b>\n\n"
                f"🧾 Buyurtma: <code>PR-{order_id}</code>\n"
                f"👤 Xaridor: {call.from_user.full_name}\n"
                f"🔗 Xaridor username: {username}\n"
                f"🆔 Xaridor ID: <code>{call.from_user.id}</code>\n"
                f"💎 Premium: <b>{label}</b>\n"
                f"🎯 Qabul qiluvchi: <b>{recipient}</b>\n"
                f"💰 Summa: <b>{_money(price)}</b>\n\n"
                "📌 Premiumni qo'lda yuboring, so'ng buyurtmani bajaring.",
                reply_markup=admin_premium_detail_keyboard(order_id),
                parse_mode="HTML"
            )
    except Exception:
        pass
    await call.answer("Buyurtma yaratildi")
