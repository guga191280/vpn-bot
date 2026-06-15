from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🛒 Купить VPN"), KeyboardButton(text="📋 Мои подписки")],
        [KeyboardButton(text="🆓 Тест"), KeyboardButton(text="🆘 Поддержка")],
        [KeyboardButton(text="📖 Инструкция")],
    ], resize_keyboard=True)

def tariffs_keyboard(tariffs):
    buttons = []
    for t in tariffs:
        if t.slug == "test":
            continue
        buttons.append([InlineKeyboardButton(text=f"{t.name} — {int(t.price)} руб.", callback_data=f"buy_{t.slug}")])
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
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
         InlineKeyboardButton(text="📋 Подписки", callback_data="admin_active_subs")],
        [InlineKeyboardButton(text="💰 Платежи", callback_data="admin_payments"),
         InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🔍 Поиск юзера", callback_data="admin_search"),
         InlineKeyboardButton(text="🎁 Выдать подписку", callback_data="admin_grant")],
        [InlineKeyboardButton(text="⏳ Продлить", callback_data="admin_extend"),
         InlineKeyboardButton(text="🚫 Заблокировать", callback_data="admin_block")],
        [InlineKeyboardButton(text="✅ Разблокировать", callback_data="admin_unblock"),
         InlineKeyboardButton(text="🔧 Тарифы", callback_data="admin_tariffs")],
        [InlineKeyboardButton(text="🖥 Серверы", callback_data="admin_servers"),
         InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
    ])
