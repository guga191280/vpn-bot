import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PATH, PORT
from database import init_db
from handlers import router
from admin import admin_router
from scheduler import setup_scheduler

logging.basicConfig(level=logging.ERROR)
logging.getLogger("apscheduler").setLevel(logging.ERROR)
logging.getLogger("aiogram").setLevel(logging.ERROR)
logging.getLogger("aiohttp").setLevel(logging.ERROR)

async def health(request):
    return web.Response(text="ok")

async def on_startup(bot: Bot):
    try:
        await init_db()
    except Exception as e:
        logging.error(f"DB: {e}")
    try:
        await bot.set_webhook(WEBHOOK_URL)
    except Exception as e:
        logging.error(f"Webhook: {e}")
    try:
        setup_scheduler(bot)
    except Exception as e:
        logging.error(f"Scheduler: {e}")

async def on_shutdown(bot: Bot):
    try:
        await bot.delete_webhook()
    except:
        pass

def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(admin_router)
    dp.include_router(router)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    web.run_app(app, host="0.0.0.0", port=PORT, access_log=None)

if __name__ == "__main__":
    main()
