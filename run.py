import asyncio
import uvicorn
import logging
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("runner")

async def start_web():
    config = uvicorn.Config(
        "web.app:app",
        host=settings.WEB_HOST,
        port=settings.WEB_PORT,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

async def start_bot():
    from bot import main as bot_main
    await bot_main()

async def main():
    logger.info("🚀 در حال راه‌اندازی همزمان وب‌اپلیکیشن و ربات تلگرام...")
    # Run both web server and bot concurrently
    await asyncio.gather(
        start_web(),
        start_bot(),
        return_exceptions=True
    )

if __name__ == "__main__":
    asyncio.run(main())
