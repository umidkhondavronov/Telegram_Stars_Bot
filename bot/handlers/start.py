from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from bot.database.engine import SessionLocal
from bot.database.repository import get_or_create_user,get_balance
from bot.keyboards.main import main_keyboard
router=Router()
async def show_main_menu(message: Message):
    async with SessionLocal() as session:
        user=await get_or_create_user(session,message.from_user)
        balance=await get_balance(session,user.id)
    name=message.from_user.first_name or "do'st"
    await message.answer(
        f"👋 Salom, <b>{name}</b>!\n\n"
        "<b>Stars Shop</b> ga xush kelibsiz.\n"
        f"💰 Balansingiz: <b>{balance:,.0f} so'm</b>\n\n"
        "Kerakli bo'limni tanlang:", reply_markup=main_keyboard(), parse_mode="HTML")

@router.message(CommandStart())
async def start(message:Message):
    await show_main_menu(message)

@router.message(Command("menu"))
async def menu(message: Message):
    await show_main_menu(message)
