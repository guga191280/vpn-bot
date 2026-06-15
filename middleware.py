from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable
import time

class AntiSpamMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 1.0):
        self.rate_limit = rate_limit
        self.users = {}

    async def __call__(self, handler: Callable, event: Message, data: Dict[str, Any]) -> Any:
        user_id = event.from_user.id
        now = time.time()
        if user_id in self.users:
            if now - self.users[user_id] < self.rate_limit:
                await event.answer("⏳ Не так быстро!")
                return
        self.users[user_id] = now
        return await handler(event, data)
