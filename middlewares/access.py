from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from aiogram.fsm.context import FSMContext
from typing import Callable, Dict, Any, Awaitable, Union
from config import ADMIN_ID
from utils.database import is_user_allowed
from handlers.common import Feedback

class AccessMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        # Allow feedback flow for everyone
        state: FSMContext | None = data.get("state")
        if state is not None:
            current_state = await state.get_state()
            if current_state == Feedback.waiting_for_message.state:
                return await handler(event, data)

        if user.id == ADMIN_ID or is_user_allowed(user.id):
            return await handler(event, data)

        # If user is not allowed
        if isinstance(event, Message):
            await event.answer("⛔️ У вас нет доступа к этому боту.")
        elif isinstance(event, CallbackQuery):
            await event.answer("⛔️ У вас нет доступа к этому боту.", show_alert=True)

        return
