import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import settings
import database as db
from handlers import start_router, ocr_router, ig_router, ref_router, admin_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("persian_ocr_bot")

async def main():
    if not settings.BOT_TOKEN or settings.BOT_TOKEN == "123456789:ABCDefGhIjKlMnOpQrStUvWxYz":
        logger.warning(
            "⚠️ هشدار: توکن ربات (BOT_TOKEN) در فایل .env یا متغیرهای محیطی تنظیم نشده است!\n"
            "لطفاً توکن ربات دریافتی از @BotFather را در فایل .env قرار دهید."
        )
        return

    logger.info("🔧 در حال راه‌اندازی دیتابیس...")
    await db.init_db()

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Include Handlers
    dp.include_router(admin_router)
    dp.include_router(ig_router)
    dp.include_router(ref_router)
    dp.include_router(start_router)
    dp.include_router(ocr_router)

    bot_info = await bot.get_me()
    logger.info(f"🚀 ربات با موفقیت راه‌اندازی شد: @{bot_info.username} ({bot_info.id})")
    
    # Start Polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 ربات متوقف شد.")
