from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_ID
from utils.database import add_allowed_user, remove_allowed_user, get_all_allowed_users, is_user_allowed

router = Router()

class AdminStates(StatesGroup):
    waiting_for_user_id_add = State()
    waiting_for_user_id_remove = State()

def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить пользователя", callback_data="admin_add_user")],
        [InlineKeyboardButton(text="➖ Удалить пользователя", callback_data="admin_remove_user")],
        [InlineKeyboardButton(text="📋 Список пользователей", callback_data="admin_list_users")],
        [InlineKeyboardButton(text="🔙 Закрыть", callback_data="admin_close")]
    ])

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    await message.answer(
        "👮‍♂️ **Панель администратора**\n\n"
        "Выберите действие:",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_close")
async def admin_close(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()

@router.callback_query(F.data == "admin_add_user")
async def admin_add_user_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    
    await callback.answer()
    await callback.message.answer(
        "Введите Telegram ID пользователя, которого нужно добавить:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_cancel_action")]
        ])
    )
    await state.set_state(AdminStates.waiting_for_user_id_add)

@router.callback_query(F.data == "admin_remove_user")
async def admin_remove_user_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    
    await callback.answer()
    await callback.message.answer(
        "Введите Telegram ID пользователя, которого нужно удалить:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_cancel_action")]
        ])
    )
    await state.set_state(AdminStates.waiting_for_user_id_remove)

@router.callback_query(F.data == "admin_list_users")
async def admin_list_users(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    users = get_all_allowed_users()
    if not users:
        text = "Список пользователей пуст."
    else:
        text = "📋 **Список разрешенных пользователей:**\n\n"
        for uid in users:
            text += f"• `{uid}`\n"
            
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back_to_menu")]
        ]),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_back_to_menu")
@router.callback_query(F.data == "admin_cancel_action")
async def admin_back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "👮‍♂️ **Панель администратора**\n\n"
        "Выберите действие:",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )

@router.message(AdminStates.waiting_for_user_id_add)
async def process_add_user(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        user_id = int(message.text.strip())
        if add_allowed_user(user_id):
            await message.answer(f"✅ Пользователь `{user_id}` добавлен.", parse_mode="Markdown")
        else:
            await message.answer("❌ Ошибка при добавлении пользователя.")
    except ValueError:
        await message.answer("❌ Некорректный ID. Введите число.")
        return

    await state.clear()
    await cmd_admin(message)

@router.message(AdminStates.waiting_for_user_id_remove)
async def process_remove_user(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        user_id = int(message.text.strip())
        if remove_allowed_user(user_id):
            await message.answer(f"✅ Пользователь `{user_id}` удален.", parse_mode="Markdown")
        else:
            await message.answer("❌ Ошибка при удалении пользователя.")
    except ValueError:
        await message.answer("❌ Некорректный ID. Введите число.")
        return

    await state.clear()
    await cmd_admin(message)
