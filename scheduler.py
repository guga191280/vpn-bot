from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from datetime import datetime, timedelta
from aiogram import Bot

from database import AsyncSessionLocal
from models import Subscription
from xui_client import xui

scheduler = AsyncIOScheduler()

def setup_scheduler(bot: Bot):
    scheduler.add_job(check_expiring, "interval", hours=12, args=[bot])
    scheduler.add_job(deactivate_expired, "interval", hours=6)
    scheduler.start()

async def check_expiring(bot: Bot):
    threshold = datetime.utcnow() + timedelta(days=3)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Subscription).where(
                Subscription.is_active == True,
                Subscription.expires_at <= threshold,
                Subscription.expires_at > datetime.utcnow(),
                Subscription.notified_expiry == False
            )
        )
        subs = result.scalars().all()
        for sub in subs:
            try:
                days_left = (sub.expires_at - datetime.utcnow()).days
                await bot.send_message(
                    sub.user_id,
                    f"⚠️ Твоя подписка истекает через {days_left} дн. ({sub.expires_at.strftime('%d.%m.%Y')})\n\nНажми «Мои подписки» → Продлить."
                )
                sub.notified_expiry = True
            except:
                pass
        await db.commit()

async def deactivate_expired():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Subscription).where(
                Subscription.is_active == True,
                Subscription.expires_at < datetime.utcnow()
            )
        )
        subs = result.scalars().all()
        for sub in subs:
            sub.is_active = False
            await xui.login()
            await xui.disable_client(sub.xui_client_id)
        await db.commit()
