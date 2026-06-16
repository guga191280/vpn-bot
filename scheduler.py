from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from datetime import datetime, timedelta
from aiogram import Bot

from database import AsyncSessionLocal
from models import Subscription, Payment
from xui_client import xui
from cleanup import cleanup_old_data

scheduler = AsyncIOScheduler()

def setup_scheduler(bot: Bot):
    scheduler.add_job(check_expiring, "interval", hours=12, args=[bot])
    scheduler.add_job(deactivate_expired, "interval", hours=6)
    scheduler.add_job(cleanup_old_data, "interval", hours=24)
    scheduler.add_job(daily_restart, "cron", hour=3, minute=0)
    scheduler.add_job(auto_renew, "interval", hours=12, args=[bot])
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
                    f"⚠️ Твоя подписка истекает через *{days_left} дн.* ({sub.expires_at.strftime('%d.%m.%Y')})\n\n"
                    f"Нажми «Мои подписки» → Продлить чтобы не потерять доступ.",
                    parse_mode="Markdown"
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
            try:
                await xui.disable_client(sub.xui_client_id)
            except:
                pass
        await db.commit()

async def auto_renew(bot: Bot):
    # уведомляем об истёкших подписках
    cutoff = datetime.utcnow() - timedelta(hours=1)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Subscription).where(
                Subscription.is_active == False,
                Subscription.expires_at >= cutoff
            )
        )
        subs = result.scalars().all()
        for sub in subs:
            try:
                await bot.send_message(
                    sub.user_id,
                    "❌ Твоя подписка истекла.\n\nНажми «Купить VPN» чтобы продлить доступ.",
                )
            except:
                pass

async def daily_restart():
    import os, signal
    os.kill(os.getpid(), signal.SIGTERM)
