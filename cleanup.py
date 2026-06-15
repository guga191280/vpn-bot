from database import AsyncSessionLocal
from models import Payment, Subscription
from sqlalchemy import select, delete
from datetime import datetime, timedelta
import logging

async def cleanup_old_data():
    async with AsyncSessionLocal() as db:
        # удаляем pending платежи старше 24 часов
        cutoff = datetime.utcnow() - timedelta(hours=24)
        await db.execute(
            delete(Payment).where(
                Payment.status == "pending",
                Payment.created_at < cutoff
            )
        )
        # удаляем неактивные подписки старше 90 дней
        cutoff2 = datetime.utcnow() - timedelta(days=90)
        await db.execute(
            delete(Subscription).where(
                Subscription.is_active == False,
                Subscription.expires_at < cutoff2
            )
        )
        await db.commit()
        logging.info("Cleanup done")
