import os
import asyncio
import logging
import sys
import io
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import BOT_TOKEN, ADMINS, WEB_HOST, WEB_PORT, WEBAPP_URL
from database import db
from seen_api import seen_client
from web_server import create_web_app

from handlers.free_handlers import router as free_router
from handlers.user_handlers import router as user_router
from handlers.smm_handlers import router as smm_router
from handlers.number_handlers import router as number_router
from handlers.admin_handlers import router as admin_router

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("PixoraSMM")

async def keep_alive_ping(url: str):
    """Pings the health check endpoint every 3 minutes to keep Render alive 24/7."""
    if not url or "localhost" in url or "127.0.0.1" in url:
        return
    await asyncio.sleep(30)
    health_url = f"{url.rstrip('/')}/health"
    while True:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(health_url, timeout=15) as resp:
                    logger.info(f"💓 Keep-alive ping to {health_url}: status={resp.status}")
        except Exception as ex:
            logger.debug(f"Keep-alive ping error: {ex}")
        await asyncio.sleep(180)  # Ping every 3 minutes

async def main():
    logger.info("Initializing Pixora SMM Bot & Database...")
    await db.init_db()

    # Pre-sync initial services in background (doesn't block port binding)
    asyncio.create_task(seen_client.fetch_services())

    # Start Bot
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Include routers
    dp.include_router(free_router)
    dp.include_router(user_router)
    dp.include_router(smm_router)
    dp.include_router(number_router)
    dp.include_router(admin_router)

    # Web App instance
    web_app = create_web_app()

    # Detect Render environment
    render_url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
    if render_url:
        await db.set_setting("webapp_url", render_url)
        logger.info(f"🌐 Render external URL detected and saved: {render_url}")

    current_webapp_url = await db.get_setting("webapp_url", WEBAPP_URL)
    is_render = bool(os.getenv("RENDER") or os.getenv("RENDER_EXTERNAL_URL") or os.getenv("PORT"))

    bot_info = await bot.get_me()
    logger.info(f"Bot connected: @{bot_info.username} ({bot_info.first_name})")

    if is_render and current_webapp_url and current_webapp_url.startswith("https://"):
        # ==========================================
        # RENDER WEBHOOK MODE (24/7 Active)
        # ==========================================
        webhook_path = "/webhook"
        webhook_url = f"{current_webapp_url.rstrip('/')}{webhook_path}"
        logger.info(f"🚀 Render environment detected! Activating Webhook at: {webhook_url}")

        SimpleRequestHandler(
            dispatcher=dp,
            bot=bot
        ).register(web_app, path=webhook_path)

        setup_application(web_app, dp, bot=bot)

        # Start Web server first so /webhook and /health are already listening
        runner = web.AppRunner(web_app)
        await runner.setup()
        site = web.TCPSite(runner, WEB_HOST, WEB_PORT)
        await site.start()
        logger.info(f"🌐 Web App & Webhook server running at http://{WEB_HOST}:{WEB_PORT}")

        # Set Telegram webhook (server is ready to receive requests)
        try:
            await bot.set_webhook(
                url=webhook_url,
                allowed_updates=dp.resolve_used_update_types(),
                drop_pending_updates=False
            )
            logger.info(f"✅ Webhook successfully set to: {webhook_url}")
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")

        # Start self keep-alive loop
        asyncio.create_task(keep_alive_ping(current_webapp_url))

        # Notify admins
        for admin_id in ADMINS:
            try:
                await bot.send_message(
                    admin_id,
                    f"🚀 <b>Pixora SMM Bot ishga tushdi (Render Webhook 24/7)!</b>\n\n"
                    f"🤖 Bot: @{bot_info.username}\n"
                    f"🌐 Webhook: <code>{webhook_url}</code>\n"
                    f"📱 Mini App: <code>{current_webapp_url}</code>\n"
                    f"👑 Admin ID: <code>{admin_id}</code>\n\n"
                    f"⚡ Bot va Mini App 24/7 uzluksiz ishga tushirildi!",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Could not notify admin {admin_id}: {e}")

        # Keep server running indefinitely
        try:
            await asyncio.Event().wait()
        finally:
            logger.info("Shutting down webhook server...")
            await runner.cleanup()
            await bot.session.close()

    else:
        # ==========================================
        # LOCAL DEVELOPMENT POLLING MODE
        # ==========================================
        logger.info("💻 Local environment detected! Activating Long Polling mode...")

        # Remove any existing webhook so polling works without conflict
        await bot.delete_webhook(drop_pending_updates=False)

        # Start local Web server
        runner = web.AppRunner(web_app)
        await runner.setup()
        site = web.TCPSite(runner, WEB_HOST, WEB_PORT)
        await site.start()
        logger.info(f"🌐 Local Web App server running at http://{WEB_HOST}:{WEB_PORT}")

        # Notify admins
        for admin_id in ADMINS:
            try:
                await bot.send_message(
                    admin_id,
                    f"🚀 <b>Pixora SMM Bot ishga tushdi (Local Polling)!</b>\n\n"
                    f"🤖 Bot: @{bot_info.username}\n"
                    f"💻 Rejim: Lokal kompyuter",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Could not notify admin {admin_id}: {e}")

        try:
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        finally:
            logger.info("Shutting down local bot...")
            await runner.cleanup()
            await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Pixora SMM Bot stopped.")
