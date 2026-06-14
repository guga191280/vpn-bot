from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from sqlalchemy import select, func
from datetime import datetime

from database import AsyncSessionLocal
from models import User, Subscription, Payment
from keyboards import admin_keyboard
from config import ADMIN_IDS
from xui_client import xui

admin_router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@admin_router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("🔧 Админ-панель", reply_markup=admin_keyboard())

@admin_router.callback_query(F.data == "admin_users")
async def admin_users(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    async with AsyncSessionLocal() as db:
        total = await db.execute(select(func.count(User.id)))
        active = await db.execute(
            select(func.count(Subscription.id)).where(Subscription.is_active == True)
        )
    await call.message.answer(
        f"👥 Всего пользователей: *{total.scalar()}*\n"
        f"✅ Активных подписок: *{active.scalar()}*",
        parse_mode="Markdown"
    )
    await call.answer()

@admin_router.callback_query(F.data == "admin_payments")
async def admin_payments(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Payment).where(Payment.status == "paid").order_by(Payment.paid_at.desc()).limit(10)
        )
        payments = result.scalars().all()
    if not payments:
        await call.message.answer("Платежей нет.")
        return
    text = "💰 *Последние платежи:*\n\n"
    for p in payments:
        text += f"ID: {p.user_id} | {p.amount} руб. | {p.plan} | {p.paid_at.strftime('%d.%m.%Y')}\n"
    await call.message.answer(text, parse_mode="Markdown")
    await call.answer()

@admin_router.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    async with AsyncSessionLocal() as db:
        total_revenue = await db.execute(
            select(func.sum(Payment.amount)).where(Payment.status == "paid")
        )
        total_subs = await db.execute(select(func.count(Subscription.id)))
        active_subs = await db.execute(
            select(func.count(Subscription.id)).where(Subscription.is_active == True)
        )
    await call.message.answer(
        f"📊 *Статистика*\n\n"
        f"Выручка: *{total_revenue.scalar() or 0} руб.*\n"
        f"Всего подписок: *{total_subs.scalar()}*\n"
        f"Активных: *{active_subs.scalar()}*",
        parse_mode="Markdown"
    )
    await call.answer()

broadcast_state = {}

@admin_router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    broadcast_state[call.from_user.id] = True
    await call.message.answer("Напиши сообщение для рассылки:")
    await call.answer()

@admin_router.message(F.text)
async def admin_broadcast_send(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    if not broadcast_state.get(message.from_user.id):
        return
    broadcast_state.pop(message.from_user.id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()

    sent, failed = 0, 0
    for user in users:
        try:
            await bot.send_message(user.telegram_id, message.text)
            sent += 1
        except:
            failed += 1

    await message.answer(f"📢 Отправлено: {sent}, ошибок: {failed}")
