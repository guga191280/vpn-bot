from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from sqlalchemy import select
from datetime import datetime, timedelta

from database import AsyncSessionLocal
from models import User, Subscription, Payment, Tariff
from keyboards import main_menu, tariffs_keyboard, payment_keyboard, subscription_keyboard
from payment import create_payment_label, get_payment_url, check_payment
from xui_client import xui
from config import ADMIN_IDS

router = Router()

INSTRUCTIONS = """
📱 *Инструкция по подключению VPN*

1. Скачай приложение:
   • Android: *HAPP VPN*, *v2rayNG*
   • iOS: *HAPP VPN*, *Streisand* или *Shadowrocket*
   • Windows: *HAPP VPN*, *v2rayN*
   • macOS: *V2Box*

2. Открой ссылку подписки из раздела «Мои подписки»
3. Скопируй ссылку → вставь в приложение → подключись

❓ Проблемы? Пиши в поддержку: @digitalTech78
"""

def progress_bar(used: float, total: float, length: int = 10) -> str:
    if total == 0:
        return "∞"
    pct = min(used / total, 1.0)
    filled = int(pct * length)
    bar = "█" * filled + "░" * (length - filled)
    return f"{bar} {pct*100:.0f}%"

@router.message(CommandStart())
async def cmd_start(message: Message):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if not user:
            db.add(User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                full_name=message.from_user.full_name
            ))
            await db.commit()
    await message.answer("👋 Привет! Добро пожаловать в VPN сервис.\n\nВыбери действие:", reply_markup=main_menu())

@router.message(F.text == "🛒 Купить VPN")
async def buy_vpn(message: Message):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Tariff).where(Tariff.is_active == True))
        tariffs = result.scalars().all()
    await message.answer("💎 Выбери тариф:", reply_markup=tariffs_keyboard(tariffs))

@router.callback_query(F.data.startswith("buy_"))
async def process_buy(call: CallbackQuery):
    slug = call.data.split("_", 1)[1]
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Tariff).where(Tariff.slug == slug))
        tariff = result.scalar_one_or_none()
        if not tariff:
            await call.answer("Тариф не найден")
            return
        if tariff.price == 0:
            existing = await db.execute(select(Subscription).where(
                Subscription.user_id == call.from_user.id,
                Subscription.plan == "test"
            ))
            if existing.scalar_one_or_none():
                await call.message.answer("❌ Тестовая подписка уже была использована.")
                await call.answer()
                return
            await activate_subscription(call.from_user.id, tariff, db)
            await db.commit()
            await call.message.answer("✅ Тестовая подписка активирована!")
            await call.message.answer(INSTRUCTIONS, parse_mode="Markdown")
            await call.answer()
            return
        label = await create_payment_label(call.from_user.id, slug)
        url = get_payment_url(tariff.price, label, f"VPN {tariff.name}")
        db.add(Payment(
            user_id=call.from_user.id,
            amount=tariff.price,
            plan=slug,
            label=label,
            status="pending"
        ))
        await db.commit()
    await call.message.answer(
        f"💳 *{tariff.name}* — *{int(tariff.price)} руб.*\n\nПосле оплаты нажми «Я оплатил».",
        reply_markup=payment_keyboard(url, label),
        parse_mode="Markdown"
    )
    await call.answer()

@router.callback_query(F.data.startswith("check_"))
async def check_pay(call: CallbackQuery):
    label = call.data.split("_", 1)[1]
    await call.answer("Проверяю...")
    paid = await check_payment(label)
    if not paid:
        await call.message.answer("❌ Оплата не найдена. Подожди минуту и попробуй снова.")
        return
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Payment).where(Payment.label == label))
        payment = result.scalar_one_or_none()
        if not payment or payment.status == "paid":
            await call.message.answer("⚠️ Платёж уже обработан.")
            return
        payment.status = "paid"
        payment.paid_at = datetime.utcnow()
        result2 = await db.execute(select(Tariff).where(Tariff.slug == payment.plan))
        tariff = result2.scalar_one_or_none()
        await activate_subscription(payment.user_id, tariff, db)
        await db.commit()
    await call.message.answer("✅ *Оплата прошла!* Подписка активирована.\n\nИди в «Мои подписки».", parse_mode="Markdown")
    await call.message.answer(INSTRUCTIONS, parse_mode="Markdown")

async def activate_subscription(user_id: int, tariff, db):
    await xui.login()
    client = await xui.create_client(tariff.days, tariff.traffic_gb, user_id)
    vpn_key = await xui.get_client_url(client["client_id"])
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id, Subscription.is_active == True)
    )
    old_sub = result.scalar_one_or_none()
    if old_sub:
        old_sub.is_active = False
    sub = Subscription(
        user_id=user_id,
        xui_client_id=client["client_id"],
        vpn_key=vpn_key,
        plan=tariff.slug,
        traffic_limit_gb=tariff.traffic_gb,
        expires_at=datetime.utcnow() + timedelta(days=tariff.days),
        is_active=True
    )
    db.add(sub)

@router.message(F.text == "📋 Мои подписки")
async def my_subscriptions(message: Message):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Subscription).where(
                Subscription.user_id == message.from_user.id,
                Subscription.is_active == True
            )
        )
        sub = result.scalar_one_or_none()
    if not sub:
        await message.answer("❌ У тебя нет активных подписок.\n\nНажми «Купить VPN» чтобы начать.")
        return
    now = datetime.utcnow()
    days_left = (sub.expires_at - now).days
    status = "✅ Активна" if sub.expires_at > now else "❌ Истекла"
    traffic_text = f"Трафик: {progress_bar(0, sub.traffic_limit_gb)}\n" if sub.traffic_limit_gb > 0 else "Трафик: ∞ безлимит\n"
    text = (
        f"📋 *Твоя подписка*\n\n"
        f"Статус: {status}\n"
        f"Истекает: {sub.expires_at.strftime('%d.%m.%Y')}\n"
        f"Осталось: *{days_left} дн.*\n"
        f"{traffic_text}\n"
        f"🔑 *Ключ подписки:*\n`{sub.vpn_key}`"
    )
    await message.answer(text, reply_markup=subscription_keyboard(sub.id), parse_mode="Markdown")

@router.callback_query(F.data.startswith("renew_"))
async def renew_sub(call: CallbackQuery):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Tariff).where(Tariff.is_active == True))
        tariffs = result.scalars().all()
    await call.message.answer("Выбери тариф для продления:", reply_markup=tariffs_keyboard(tariffs))
    await call.answer()

@router.message(F.text == "🆓 Тест")
async def test_sub(message: Message):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Subscription).where(
            Subscription.user_id == message.from_user.id,
            Subscription.plan == "test"
        ))
        existing = result.scalar_one_or_none()
        if existing:
            await message.answer("❌ Тестовая подписка уже была использована.")
            return
        result2 = await db.execute(select(Tariff).where(Tariff.slug == "test"))
        tariff = result2.scalar_one_or_none()
        await activate_subscription(message.from_user.id, tariff, db)
        await db.commit()
    await message.answer("✅ Тестовая подписка на 30 дней / 500 MB активирована!\n\nИди в «Мои подписки».")
    await message.answer(INSTRUCTIONS, parse_mode="Markdown")

@router.message(F.text == "📖 Инструкция")
async def instructions(message: Message):
    await message.answer(INSTRUCTIONS, parse_mode="Markdown")

@router.message(F.text == "🆘 Поддержка")
async def support(message: Message):
    await message.answer(
        "🆘 *Поддержка*\n\nНапиши нам: @digitalTech78\n\nВремя ответа: обычно в течение часа.",
        parse_mode="Markdown"
    )
