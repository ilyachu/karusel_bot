"""Helper functions for message formatting and navigation."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def add_step_indicator(message: str, current_step: int, total_steps: int = 5) -> str:
    """
    Add step progress indicator to message.
    
    Args:
        message: The message text
        current_step: Current step number (1-5)
        total_steps: Total number of steps (default 5)
        
    Returns:
        Message with step indicator prepended
    """
    emoji_map = {
        1: "📝",
        2: "✏️", 
        3: "👁️",
        4: "🎨",
        5: "📍"
    }
    emoji = emoji_map.get(current_step, "•")
    return f"{emoji} Шаг {current_step}/{total_steps} • {message}"


def add_back_button(keyboard: InlineKeyboardMarkup, 
                   callback_data: str = "back") -> InlineKeyboardMarkup:
    """
    Add back button to existing inline keyboard.
    
    Args:
        keyboard: Existing inline keyboard
        callback_data: Callback data for back button
        
    Returns:
        Modified keyboard with back button appended
    """
    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback_data)]
    )
    return keyboard
