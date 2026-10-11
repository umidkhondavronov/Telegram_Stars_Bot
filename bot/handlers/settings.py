from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from bot.config import settings, admin_ids
from bot.database.engine import SessionLocal
from bot.database.repository import get_setting, set_setting
from bot.keyboards.settings import settings_keyboard, settings_back_keyboard

router = Router()

DEFAULT_STARS = "50=11000,100=22000,200=43000,300=65000,500=115000,1000=225000,2000=560000"
DEFAULT_GIFTS = "teddy=2600,heart=2600,gift=4325,rose=4325,cake=8650,bouquet=8650,rocket=8650,trophy=17300,ring=17300,diamond=17300"
DEFAULT_PREMIUM = "3=160000,6=220000,12=380000"

class SettingsState(StatesGroup):
    section = State()

def is_admin(uid: int) -> bool:
    return uid in admin_ids()

def _parse_stars(raw):
    result = {}
    for part in raw.split(","):
        if "=" not in part: raise ValueError
        k,v = part.split("=",1)
        stars, price = int(k.strip()), int(v.strip())
        if stars <= 0 or price <= 0: raise ValueError
        result[stars] = price
    if not result: raise ValueError
    return result

def _parse_gifts(raw):
    result = {}
    for part in raw.split(","):
        if "=" not in part: raise ValueError
        k,v = part.split("=",1)
        key, price = k.strip(), int(v.strip())
        if not key or price <= 0: raise ValueError
        result[key] = price
    if not result: raise ValueError
    return result

@router.callback_query(F.data == "adm:settings")
async def settings_home(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("Ruxsat yo'q", show_alert=True); return
    await state.clear()
    await call.message.edit_text("⚙️ <b>Sozlamalar</b>\n\nO'zgartirmoqchi bo'lgan bo'limni tanlang:",
                                  reply_markup=settings_keyboard(), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("adm:set:" ) | F.data.startswith("settings_"))
async def settings_section(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("Ruxsat yo'q", show_alert=True); return
    section = call.data.split(":")[-1] if call.data.startswith("adm:set:") else call.data.replace("settings_", "")
    await state.set_state(SettingsState.section)
    await state.update_data(section=section)

    async with SessionLocal() as s:
        if section == "stars":
            raw = await get_setting(s, "stars_prices", DEFAULT_STARS)
            text = (
                "⭐ <b>Stars narxlari</b>\n\n"
                "Format: <code>Stars=Narx</code>, vergul bilan ajrating.\n\n"
                f"Joriy: <code>{raw}</code>\n\n"
                "Masalan: <code>50=12000,100=23000</code>"
            )
        elif section == "gifts":
            raw = await get_setting(s, "gift_prices", DEFAULT_GIFTS)
            text = (
                "🎁 <b>Gift narxlari</b>\n\n"
                "Gift kalitlari o'zgarmaydi; faqat narxlarni kiriting.\n"
                f"Joriy: <code>{raw}</code>\n\n"
                "Masalan: <code>teddy=3000,heart=3000</code>"
            )
        elif section == "premium":
            raw = await get_setting(s, "premium_prices", DEFAULT_PREMIUM)
            text = (
                "💎 <b>Premium narxlari</b>\n\n"
                "Format: <code>3=160000,6=220000,12=380000</code>\n\n"
                f"Joriy: <code>{raw}</code>\n\n"
                "3 oy, 6 oy va 1 yil narxlarini so'mda kiriting."
            )
        else:
            card = await get_setting(s, "payment_card", settings.payment_card)
            name = await get_setting(s, "payment_name", settings.payment_name)
            text = (
                "💳 <b>To'lov rekvizitlari</b>\n\n"
                f"Joriy karta: <code>{card}</code>\n"
                f"Joriy qabul qiluvchi: <b>{name}</b>\n\n"
                "Yangi ma'lumotni quyidagicha yuboring:\n"
                "<code>karta|qabul qiluvchi</code>"
            )
    await call.message.answer(text, reply_markup=settings_back_keyboard(), parse_mode="HTML")
    await call.answer()

@router.message(SettingsState.section)
async def save_settings(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear(); return
    data = await state.get_data()
    section = data.get("section")
    raw = (message.text or "").strip()
    try:
        async with SessionLocal() as s:
            if section == "stars":
                _parse_stars(raw)
                await set_setting(s, "stars_prices", raw)
                reply = "✅ Stars narxlari saqlandi."
            elif section == "gifts":
                _parse_gifts(raw)
                await set_setting(s, "gift_prices", raw)
                reply = "✅ Gift narxlari saqlandi."
            elif section == "premium":
                parts = {}
                for part in raw.split(","):
                    k, v = part.split("=", 1)
                    k, v = int(k.strip()), int(v.strip())
                    if k not in (3, 6, 12) or v <= 0:
                        raise ValueError
                    parts[k] = v
                if set(parts) != {3, 6, 12}:
                    raise ValueError
                await set_setting(s, "premium_prices", raw)
                reply = "✅ Premium narxlari saqlandi."
            elif section == "payment":
                parts = [x.strip() for x in raw.split("|", 1)]
                if len(parts) != 2 or not all(parts):
                    raise ValueError
                await set_setting(s, "payment_card", parts[0])
                await set_setting(s, "payment_name", parts[1])
                reply = "✅ To'lov rekvizitlari saqlandi."
            else:
                raise ValueError
    except (ValueError, TypeError):
        await message.answer("❌ Format noto'g'ri. Qaytadan kiriting.")
        return
    await state.clear()
    await message.answer(reply, reply_markup=settings_keyboard())

