import asyncio,logging
from aiogram import Bot,Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from bot.config import settings
from bot.database.engine import engine
from bot.database.models import Base
from bot.handlers.start import router as start_router
from bot.handlers.user import router as user_router
from bot.handlers.admin import router as admin_router
from bot.handlers.settings import router as settings_router
from bot.handlers.premium import router as premium_router
async def init_db():
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
async def main():
    logging.basicConfig(level=logging.INFO); await init_db()
    bot=Bot(token=settings.bot_token,default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.set_my_commands([
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="menu", description="Asosiy menyu"),
    ])
    dp=Dispatcher(); dp.include_router(start_router); dp.include_router(user_router); dp.include_router(admin_router); dp.include_router(settings_router)
    dp.include_router(premium_router)
    try: await dp.start_polling(bot)
    finally: await bot.session.close(); await engine.dispose()
if __name__=="__main__": asyncio.run(main())
