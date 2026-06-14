from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🛒 Купить VPN"), KeyboardButton(text="📋 Мои подписки")],
        [KeyboardButton(text="📖 Инструкция"), KeyboardButton(text="🆘 Поддержка")],
    ], resize_keyboard=True)

def tariffs_keyboard(tariffs):
    buttons = []
    for t in tariffs:
        price = "Бесплатно" if t.price == 0 else f"{int(t.price)} руб."
        buttons.append([InlineKeyboardButton(text=f"{t.name} — {price}", callback_data=f"buy_{t.slug}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def payment_keyboard(url: str, label: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=url)],
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"check_{label}")],
    ])

def subscription_keyboard(sub_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Продлить", callback_data=f"renew_{sub_id}")],
    ])

def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="💰 Платежи", callback_data="admin_payments")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
    ])
