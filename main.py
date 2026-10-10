import asyncio
import logging
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMINS, WEB_HOST, WEB_PORT, WEBAPP_URL
from database import db
from seen_api import seen_client
from web_server import create_web_app

from handlers.user_handlers import router as user_router
from handlers.smm_handlers import router as smm_router
from handlers.number_handlers import router as number_router
from handlers.admin_handlers import router as admin_router

import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("PixoraSMM")

async def main():
    logger.info("Initializing Pixora SMM Bot & Database...")
    await db.init_db()

    # Pre-sync initial services
    logger.info("Pre-syncing services cache...")
    await seen_client.fetch_services()

    # Start Bot
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Include routers
    dp.include_router(user_router)
    dp.include_router(smm_router)
    dp.include_router(number_router)
    dp.include_router(admin_router)

    # Start Web App (Mini App) HTTP Server
    web_app = create_web_app()
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, WEB_HOST, WEB_PORT)
    await site.start()

    logger.info(f"🌐 Web App Mini App server running at http://{WEB_HOST}:{WEB_PORT}")
    logger.info(f"🚀 Bot polling started! Admin ID: {ADMINS}")

    try:
        # Notify admins that bot is running
        bot_info = await bot.get_me()
        logger.info(f"Bot connected: @{bot_info.username} ({bot_info.first_name})")

        for admin_id in ADMINS:
            try:
                await bot.send_message(
                    admin_id,
                    f"🚀 <b>Pixora SMM Bot ishga tushdi!</b>\n\n"
                    f"🤖 Bot: @{bot_info.username}\n"
                    f"🌐 Web App: <code>http://localhost:{WEB_PORT}</code>\n"
                    f"👑 Siz botsizning bosh administratorisiz!\n"
                    f"Boshqaruv paneli: /admin",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Could not notify admin {admin_id}: {e}")

        # Start long polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        logger.info("Shutting down...")
        await runner.cleanup()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Pixora SMM Bot stopped.")
