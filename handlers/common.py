from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from utils.database import get_user_logo, set_user_logo, reset_user_logo
from utils.states import CarouselFlow
from config import ADMIN_ID

class Settings(StatesGroup):
    waiting_for_logo = State()

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()  # Clear any existing state
    kb = [
        [KeyboardButton(text="Создать карусель")],
        [KeyboardButton(text="🚀 Insta Auto")],
        [KeyboardButton(text="⚡️ Быстрый режим")],
        [KeyboardButton(text="🎨 Настройки логотипа")],
        [KeyboardButton(text="Помощь")]
    ]
    
    if message.from_user.id == ADMIN_ID:
        kb.append([KeyboardButton(text="/admin")])

    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await message.answer(
        "Привет! Я бот для создания красивых каруселей.\n"
        "Отправь мне текст, голосовое сообщение или перешли пост, и я превращу это в слайды.",
        reply_markup=keyboard
    )

@router.message(F.text == "Создать карусель")
async def cmd_create_carousel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("📝 Отправьте мне текст, голосовое сообщение или перешлите пост для создания карусели.")

@router.message(F.text == "🚀 Insta Auto")
async def cmd_insta_auto(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(CarouselFlow.insta_auto_waiting_for_text)
    await message.answer(
        "🚀 Insta Auto включен.\n\n"
        "Отправьте текст, голосовое или перешлите пост. Я сам соберу Instagram-ready карусель, "
        "подготовлю caption и export-пакет."
    )

@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено. Отправьте новый текст для начала.")

@router.message(F.text == "🎨 Настройки логотипа")
async def cmd_settings_logo(message: types.Message):
    current_logo = get_user_logo(message.from_user.id)
    logo_display = current_logo if current_logo else "chu ai (по умолчанию)"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить логотип", callback_data="settings_change_logo")],
        [InlineKeyboardButton(text="🔄 Сбросить на стандартный", callback_data="settings_reset_logo")]
    ])
    
    await message.answer(
        f"🎨 **Настройки логотипа**\n\n"
        f"Текущий логотип: `{logo_display}`\n\n"
        f"Вы можете установить свой текст, который будет отображаться внизу каждого слайда.",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "settings_change_logo")
async def settings_change_logo(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("📝 Введите новый текст для логотипа (максимум 20 символов):")
    await state.set_state(Settings.waiting_for_logo)

@router.callback_query(F.data == "settings_reset_logo")
async def settings_reset_logo(callback: types.CallbackQuery):
    reset_user_logo(callback.from_user.id)
    await callback.answer("✅ Логотип сброшен!")
    await callback.message.edit_text(
        f"🎨 **Настройки логотипа**\n\n"
        f"Текущий логотип: `chu ai (по умолчанию)`\n\n"
        f"Вы можете установить свой текст, который будет отображаться внизу каждого слайда.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить логотип", callback_data="settings_change_logo")],
            [InlineKeyboardButton(text="🔄 Сбросить на стандартный", callback_data="settings_reset_logo")]
        ]),
        parse_mode="Markdown"
    )

@router.message(Settings.waiting_for_logo)
async def settings_save_logo(message: types.Message, state: FSMContext):
    new_logo = message.text.strip()
    if len(new_logo) > 20:
        await message.answer("⚠️ Слишком длинный логотип! Максимум 20 символов. Попробуйте снова.")
        return
        
    set_user_logo(message.from_user.id, new_logo)
    await state.clear()
    await message.answer(f"✅ Логотип изменен на: `{new_logo}`")

@router.message(Command("help"))
@router.message(lambda message: message.text == "Помощь")
async def cmd_help(message: types.Message):
    await message.answer(
        "Как мной пользоваться:\n\n"
        "1. **Текст**: Просто отправь мне текст, и я предложу структуру слайдов.\n"
        "2. **Голос**: Запиши голосовое, я расшифрую его и сделаю карусель.\n"
        "3. **Пересылка**: Перешли сообщение из канала, я сделаю из него слайды.\n\n"
        "Режимы:\n"
        "• `🚀 Insta Auto` — минимум действий, сразу карусель под Instagram\n"
        "• `⚡️ Быстрый режим` — короткий ручной сценарий\n\n"
        "Команды:\n"
        "/start - Перезапуск\n"
        "/cancel - Отмена текущего действия\n"
        "/help - Справка"
    )
