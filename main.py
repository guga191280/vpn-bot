import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PATH, PORT
from database import init_db
from handlers import router
from admin import admin_router
from scheduler import setup_scheduler

logging.basicConfig(level=logging.INFO)

async def on_startup(bot: Bot):
    await init_db()
    await bot.set_webhook(WEBHOOK_URL)
    setup_scheduler(bot)

async def on_shutdown(bot: Bot):
    await bot.delete_webhook()

def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(admin_router)
    dp.include_router(router)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()
    handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
