from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func
from datetime import datetime, timedelta

from database import AsyncSessionLocal
from models import User, Subscription, Payment, Tariff
from keyboards import admin_keyboard
from config import ADMIN_IDS
from xui_client import xui

admin_router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

class AdminStates(StatesGroup):
    waiting_broadcast = State()
    waiting_block_id = State()
    waiting_unblock_id = State()
    waiting_grant_id = State()
    waiting_grant_plan = State()
    waiting_extend_id = State()
    waiting_extend_days = State()
    waiting_search = State()
    waiting_tariff_price = State()

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
        active = await db.execute(select(func.count(Subscription.id)).where(Subscription.is_active == True))
        users = await db.execute(select(User).order_by(User.created_at.desc()).limit(15))
        users = users.scalars().all()
    text = f"👥 Всего: *{total.scalar()}* | Активных подписок: *{active.scalar()}*\n\n"
    for u in users:
        text += f"`{u.telegram_id}` | @{u.username or 'нет'} | {u.created_at.strftime('%d.%m.%Y')}\n"
    await call.message.answer(text, parse_mode="Markdown")
    await call.answer()

@admin_router.callback_query(F.data == "admin_active_subs")
async def admin_active_subs(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Subscription).where(Subscription.is_active == True).order_by(Subscription.expires_at)
        )
        subs = result.scalars().all()
    if not subs:
        await call.message.answer("Нет активных подписок.")
        return
    text = "📋 *Активные подписки:*\n\n"
    for s in subs:
        days_left = (s.expires_at - datetime.utcnow()).days
        text += f"ID: `{s.user_id}` | {s.plan} | истекает: {s.expires_at.strftime('%d.%m.%Y')} | осталось: {days_left} дн.\n"
    await call.message.answer(text, parse_mode="Markdown")
    await call.answer()

@admin_router.callback_query(F.data == "admin_search")
async def admin_search_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.waiting_search)
    await call.message.answer("Введи Telegram ID или @username:")
    await call.answer()

@admin_router.message(AdminStates.waiting_search)
async def admin_search_user(message: Message, state: FSMContext):
    await state.clear()
    query = message.text.strip().lstrip("@")
    async with AsyncSessionLocal() as db:
        if query.isdigit():
            result = await db.execute(select(User).where(User.telegram_id == int(query)))
        else:
            result = await db.execute(select(User).where(User.username == query))
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("Пользователь не найден.")
            return
        result2 = await db.execute(select(Subscription).where(
            Subscription.user_id == user.telegram_id, Subscription.is_active == True
        ))
        sub = result2.scalar_one_or_none()
        result3 = await db.execute(select(func.sum(Payment.amount)).where(
            Payment.user_id == user.telegram_id, Payment.status == "paid"
        ))
        total_paid = result3.scalar() or 0

    text = (
        f"👤 *Пользователь*\n\n"
        f"ID: `{user.telegram_id}`\n"
        f"Username: @{user.username or 'нет'}\n"
        f"Имя: {user.full_name or 'нет'}\n"
        f"Зарегистрирован: {user.created_at.strftime('%d.%m.%Y')}\n"
        f"Оплатил всего: *{total_paid} руб.*\n\n"
    )
    if sub:
        days_left = (sub.expires_at - datetime.utcnow()).days
        text += (
            f"✅ *Активная подписка*\n"
            f"Тариф: {sub.plan}\n"
            f"Истекает: {sub.expires_at.strftime('%d.%m.%Y')}\n"
            f"Осталось: {days_left} дн.\n"
            f"Ключ: `{sub.vpn_key}`"
        )
    else:
        text += "❌ Нет активной подписки"
    await message.answer(text, parse_mode="Markdown")

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
        text += f"ID: `{p.user_id}` | {p.amount} руб. | {p.plan} | {p.paid_at.strftime('%d.%m.%Y')}\n"
    await call.message.answer(text, parse_mode="Markdown")
    await call.answer()

@admin_router.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    async with AsyncSessionLocal() as db:
        total_revenue = await db.execute(select(func.sum(Payment.amount)).where(Payment.status == "paid"))
        total_subs = await db.execute(select(func.count(Subscription.id)))
        active_subs = await db.execute(select(func.count(Subscription.id)).where(Subscription.is_active == True))
        total_users = await db.execute(select(func.count(User.id)))
        month_revenue = await db.execute(select(func.sum(Payment.amount)).where(
            Payment.status == "paid",
            Payment.paid_at >= datetime.utcnow().replace(day=1)
        ))
    await call.message.answer(
        f"📊 *Статистика*\n\n"
        f"Пользователей: *{total_users.scalar()}*\n"
        f"Активных подписок: *{active_subs.scalar()}*\n"
        f"Всего подписок: *{total_subs.scalar()}*\n"
        f"Выручка всего: *{total_revenue.scalar() or 0} руб.*\n"
        f"Выручка за месяц: *{month_revenue.scalar() or 0} руб.*",
        parse_mode="Markdown"
    )
    await call.answer()

@admin_router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.waiting_broadcast)
    await call.message.answer("Напиши сообщение для рассылки:")
    await call.answer()

@admin_router.message(AdminStates.waiting_broadcast)
async def admin_broadcast_send(message: Message, bot: Bot, state: FSMContext):
    await state.clear()
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

@admin_router.callback_query(F.data == "admin_block")
async def admin_block_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.waiting_block_id)
    await call.message.answer("Введи Telegram ID пользователя для блокировки:")
    await call.answer()

@admin_router.message(AdminStates.waiting_block_id)
async def admin_block_user(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    try:
        user_id = int(message.text.strip())
    except:
        await message.answer("Неверный ID.")
        return
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Subscription).where(
            Subscription.user_id == user_id, Subscription.is_active == True
        ))
        sub = result.scalar_one_or_none()
        if sub:
            await xui.disable_client(sub.xui_client_id)
            sub.is_active = False
            await db.commit()
            await message.answer(f"🚫 Подписка пользователя `{user_id}` заблокирована.", parse_mode="Markdown")
            try:
                await bot.send_message(user_id, "⚠️ Ваша подписка была заблокирована администратором.")
            except:
                pass
        else:
            await message.answer("У пользователя нет активной подписки.")

@admin_router.callback_query(F.data == "admin_unblock")
async def admin_unblock_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.waiting_unblock_id)
    await call.message.answer("Введи Telegram ID пользователя для разблокировки:")
    await call.answer()

@admin_router.message(AdminStates.waiting_unblock_id)
async def admin_unblock_user(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    try:
        user_id = int(message.text.strip())
    except:
        await message.answer("Неверный ID.")
        return
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Subscription).where(
            Subscription.user_id == user_id
        ).order_by(Subscription.id.desc()))
        sub = result.scalars().first()
        if sub:
            await xui.enable_client(sub.xui_client_id)
            sub.is_active = True
            await db.commit()
            await message.answer(f"✅ Подписка пользователя `{user_id}` разблокирована.", parse_mode="Markdown")
            try:
                await bot.send_message(user_id, "✅ Ваша подписка восстановлена администратором.")
            except:
                pass
        else:
            await message.answer("Подписка не найдена.")

@admin_router.callback_query(F.data == "admin_grant")
async def admin_grant_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.waiting_grant_id)
    await call.message.answer("Введи Telegram ID пользователя для выдачи подписки:")
    await call.answer()

@admin_router.message(AdminStates.waiting_grant_id)
async def admin_grant_id(message: Message, state: FSMContext):
    await state.update_data(grant_user_id=message.text.strip())
    await state.set_state(AdminStates.waiting_grant_plan)
    await message.answer("Введи slug тарифа (1m / 3m / test):")

@admin_router.message(AdminStates.waiting_grant_plan)
async def admin_grant_plan(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()
    try:
        user_id = int(data.get("grant_user_id"))
    except:
        await message.answer("Неверный ID.")
        return
    slug = message.text.strip()
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Tariff).where(Tariff.slug == slug))
        tariff = result.scalar_one_or_none()
        if not tariff:
            await message.answer("Тариф не найден.")
            return
        from handlers import activate_subscription
        await activate_subscription(user_id, tariff, db)
        await db.commit()
    await message.answer(f"✅ Подписка *{tariff.name}* выдана пользователю `{user_id}`.", parse_mode="Markdown")
    try:
        await bot.send_message(user_id, f"🎁 Администратор выдал вам подписку *{tariff.name}*!\n\nИди в «Мои подписки».", parse_mode="Markdown")
    except:
        pass

@admin_router.callback_query(F.data == "admin_extend")
async def admin_extend_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.waiting_extend_id)
    await call.message.answer("Введи Telegram ID пользователя для продления:")
    await call.answer()

@admin_router.message(AdminStates.waiting_extend_id)
async def admin_extend_id(message: Message, state: FSMContext):
    await state.update_data(extend_user_id=message.text.strip())
    await state.set_state(AdminStates.waiting_extend_days)
    await message.answer("На сколько дней продлить?")

@admin_router.message(AdminStates.waiting_extend_days)
async def admin_extend_days(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()
    try:
        user_id = int(data.get("extend_user_id"))
        days = int(message.text.strip())
    except:
        await message.answer("Неверные данные.")
        return
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Subscription).where(
            Subscription.user_id == user_id, Subscription.is_active == True
        ))
        sub = result.scalar_one_or_none()
        if not sub:
            await message.answer("Активная подписка не найдена.")
            return
        sub.expires_at = sub.expires_at + timedelta(days=days)
        await db.commit()
    await message.answer(f"✅ Подписка пользователя `{user_id}` продлена на *{days}* дней.", parse_mode="Markdown")
    try:
        await bot.send_message(user_id, f"🎁 Ваша подписка продлена на {days} дней администратором!")
    except:
        pass

@admin_router.callback_query(F.data == "admin_tariffs")
async def admin_tariffs(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Tariff))
        tariffs = result.scalars().all()
    buttons = []
    for t in tariffs:
        buttons.append([InlineKeyboardButton(
            text=f"{t.name} — {int(t.price)} руб. ({t.days} дн.)",
            callback_data=f"edit_tariff_{t.slug}"
        )])
    await call.message.answer("Выбери тариф для изменения цены:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await call.answer()

@admin_router.callback_query(F.data.startswith("edit_tariff_"))
async def edit_tariff_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    slug = call.data.split("edit_tariff_")[1]
    await state.update_data(tariff_slug=slug)
    await state.set_state(AdminStates.waiting_tariff_price)
    await call.message.answer(f"Введи новую цену для тарифа *{slug}* (в рублях):", parse_mode="Markdown")
    await call.answer()

@admin_router.message(AdminStates.waiting_tariff_price)
async def edit_tariff_price(message: Message, state: FSMContext):
    data = await state.get_data()
    slug = data.get("tariff_slug")
    await state.clear()
    try:
        price = float(message.text.strip())
    except:
        await message.answer("Неверная цена.")
        return
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Tariff).where(Tariff.slug == slug))
        tariff = result.scalar_one_or_none()
        if tariff:
            tariff.price = price
            await db.commit()
            await message.answer(f"✅ Цена тарифа *{tariff.name}* изменена на *{int(price)} руб.*", parse_mode="Markdown")

from models import Server
from server_manager import get_active_servers

class ServerStates(StatesGroup):
    waiting_server_name = State()
    waiting_server_url = State()
    waiting_server_token = State()
    waiting_server_inbound = State()
    waiting_server_sub_url = State()
    waiting_delete_server_id = State()

@admin_router.callback_query(F.data == "admin_servers")
async def admin_servers(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Server))
        servers = result.scalars().all()
    if not servers:
        text = "Серверов нет."
    else:
        text = "🖥 *Серверы:*\n\n"
        for s in servers:
            status = "✅" if s.is_active else "❌"
            text += f"{status} ID:{s.id} | *{s.name}* | inbound:{s.inbound_id}\n`{s.url}`\n\n"
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить сервер", callback_data="admin_server_add")],
        [InlineKeyboardButton(text="🗑 Удалить сервер", callback_data="admin_server_del")],
    ])
    await call.message.answer(text, reply_markup=buttons, parse_mode="Markdown")
    await call.answer()

@admin_router.callback_query(F.data == "admin_server_add")
async def admin_server_add(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(ServerStates.waiting_server_name)
    await call.message.answer("Введи название сервера (например: RU-1):")
    await call.answer()

@admin_router.message(ServerStates.waiting_server_name)
async def server_name(message: Message, state: FSMContext):
    await state.update_data(server_name=message.text.strip())
    await state.set_state(ServerStates.waiting_server_url)
    await message.answer("Введи URL панели (например: https://russ.official-happ.ru:12822/lpTK27EkL3HLJGkZgp):")

@admin_router.message(ServerStates.waiting_server_url)
async def server_url(message: Message, state: FSMContext):
    await state.update_data(server_url=message.text.strip())
    await state.set_state(ServerStates.waiting_server_token)
    await message.answer("Введи API токен сервера:")

@admin_router.message(ServerStates.waiting_server_token)
async def server_token(message: Message, state: FSMContext):
    await state.update_data(server_token=message.text.strip())
    await state.set_state(ServerStates.waiting_server_inbound)
    await message.answer("Введи ID inbound (обычно 4):")

@admin_router.message(ServerStates.waiting_server_inbound)
async def server_inbound(message: Message, state: FSMContext):
    await state.update_data(server_inbound=message.text.strip())
    await state.set_state(ServerStates.waiting_server_sub_url)
    await message.answer("Введи URL подписки (например: https://russ.official-happ.ru:2096/sub):")

@admin_router.message(ServerStates.waiting_server_sub_url)
async def server_sub_url(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    async with AsyncSessionLocal() as db:
        db.add(Server(
            name=data["server_name"],
            url=data["server_url"],
            token=data["server_token"],
            inbound_id=int(data["server_inbound"]),
            sub_url=message.text.strip(),
            is_active=True
        ))
        await db.commit()
    await message.answer(f"✅ Сервер *{data['server_name']}* добавлен!", parse_mode="Markdown")

@admin_router.callback_query(F.data == "admin_server_del")
async def admin_server_del(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(ServerStates.waiting_delete_server_id)
    await call.message.answer("Введи ID сервера для удаления:")
    await call.answer()

@admin_router.message(ServerStates.waiting_delete_server_id)
async def server_delete(message: Message, state: FSMContext):
    await state.clear()
    try:
        server_id = int(message.text.strip())
    except:
        await message.answer("Неверный ID.")
        return
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Server).where(Server.id == server_id))
        server = result.scalar_one_or_none()
        if not server:
            await message.answer("Сервер не найден.")
            return
        server.is_active = False
        await db.commit()
    await message.answer(f"✅ Сервер ID:{server_id} деактивирован.")
