import asyncio
import logging

from aiogram import Router, types, F, Bot
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from utils.database import get_user_logo, is_user_allowed, set_user_logo, reset_user_logo
from utils.states import CarouselFlow
from utils.validation import validate_text_length
from services.layout_engine import LAYOUT_STYLE_LABELS
from config import ADMIN_ID


class Settings(StatesGroup):
    waiting_for_logo = State()


class Feedback(StatesGroup):
    waiting_for_message = State()


router = Router()

# ─── Понятные названия для пользователя ───

INSTA_REWRITE_LABELS = {
    "exact": "Как есть",
    "concise": "Короче",
    "educational": "Подробнее",
    "marketing": "Ярче",
}

INSTA_COLOR_LABELS = {
    "auto": "Авто",
    "dark": "Тёмная",
    "light": "Светлая",
    "warm": "Тёплая",
    "bold": "Яркая",
}

# Маппинг понятных цветов на внутренние темы
INSTA_COLOR_TO_THEMES = {
    "auto": "auto",
    "dark": "growth_black",
    "light": "founder_brief",
    "warm": "memory_archive",
    "bold": "creator_bold",
}

INSTA_COLOR_DESCRIPTIONS = {
    "auto": "AI сам подберёт цвета под текст",
    "dark": "тёмные глубокие тона, строгий стиль",
    "light": "светлые чистые тона, минимализм",
    "warm": "природные оттенки, уютный стиль",
    "bold": "яркие контрастные цвета, смелый стиль",
}

INSTA_SLIDE_COUNT_LABELS = {
    "auto": "Авто",
    "4": "4",
    "5": "5",
    "6": "6",
    "7": "7",
}

INSTA_CARD_SIZE_LABEL = "1080×1350, вертикаль 4:5"


def resolve_target_slide_count(text: str, slide_count_setting: str = "auto") -> int:
    if slide_count_setting in {"4", "5", "6", "7"}:
        return int(slide_count_setting)

    word_count = len((text or "").split())
    return max(4, min(7, word_count // 15 + 2))


def _insta_setup_summary(data: dict) -> str:
    layout_style = data.get("insta_layout_style", "auto")
    color_key = data.get("insta_color_palette", "auto")
    rewrite_style = data.get("insta_rewrite_style", "concise")
    slide_count = data.get("insta_slide_count", "auto")
    custom_bg = data.get("insta_custom_bg_bytes")

    style_label = LAYOUT_STYLE_LABELS.get(layout_style, "Авто")
    if layout_style == "auto":
        style_label = "Авто (AI выберет)"
    color_label = INSTA_COLOR_LABELS.get(color_key, "Авто")
    color_desc = INSTA_COLOR_DESCRIPTIONS.get(color_key, "")
    rewrite_label = INSTA_REWRITE_LABELS.get(rewrite_style, "Короче")
    slide_count_label = INSTA_SLIDE_COUNT_LABELS.get(slide_count, "Авто")
    background_label = "свой загружен" if custom_bg else "авто из коллекции бота"

    return (
        "Карусель\n\n"
        "Настройте параметры и отправьте текст:\n\n"
        f"Стиль: {style_label}\n"
        f"Палитра: {color_label} — {color_desc}\n"
        f"Текст: {rewrite_label}\n"
        f"Слайды: {slide_count_label}\n"
        f"Фон: {background_label}\n"
        f"Размер: {INSTA_CARD_SIZE_LABEL}"
    )


def _build_insta_setup_keyboard(data: dict | None = None) -> InlineKeyboardMarkup:
    data = data or {}
    layout_style = data.get("insta_layout_style", "auto")
    color_key = data.get("insta_color_palette", "auto")
    rewrite_style = data.get("insta_rewrite_style", "concise")
    slide_count = data.get("insta_slide_count", "auto")
    custom_bg = data.get("insta_custom_bg_bytes")

    def section(title: str) -> list[InlineKeyboardButton]:
        return [InlineKeyboardButton(text=title, callback_data="insta_noop")]

    # Стиль
    style_rows = [section("Стиль")]
    style_btns = []
    for key in ("auto", "magazine", "terminal", "poster", "carddeck"):
        label = LAYOUT_STYLE_LABELS.get(key, "Авто")
        if key == layout_style:
            label = f"✅ {label}"
        style_btns.append(InlineKeyboardButton(text=label, callback_data=f"insta_layout:{key}"))
    style_rows.extend([style_btns[:3], style_btns[3:]])

    # Цвета
    color_rows = [section("Палитра")]
    color_btns = []
    for key in ("auto", "dark", "light", "warm", "bold"):
        label = INSTA_COLOR_LABELS[key]
        if key == color_key:
            label = f"✅ {label}"
        color_btns.append(InlineKeyboardButton(text=label, callback_data=f"insta_color:{key}"))
    color_rows.extend([color_btns[:3], color_btns[3:]])

    # Текст
    text_rows = [section("Текст")]
    text_btns = []
    for key in ("exact", "concise", "educational", "marketing"):
        label = INSTA_REWRITE_LABELS[key]
        if key == rewrite_style:
            label = f"✅ {label}"
        text_btns.append(InlineKeyboardButton(text=label, callback_data=f"insta_copy:{key}"))
    text_rows.extend([text_btns[:2], text_btns[2:]])

    slide_rows = [section("Слайды")]
    slide_btns = []
    for key in ("auto", "4", "5", "6", "7"):
        label = INSTA_SLIDE_COUNT_LABELS[key]
        if key == slide_count:
            label = f"✅ {label}"
        slide_btns.append(InlineKeyboardButton(text=label, callback_data=f"insta_slides:{key}"))
    slide_rows.extend([slide_btns[:3], slide_btns[3:]])

    # Дополнительно
    custom_label = "Свой фон: выбран" if custom_bg else "Загрузить свой фон"
    extra_rows = [
        [InlineKeyboardButton(text=custom_label, callback_data="insta_upload_bg")],
        [InlineKeyboardButton(text="Сбросить настройки", callback_data="insta_reset_setup")],
    ]

    return InlineKeyboardMarkup(
        inline_keyboard=[*style_rows, *color_rows, *text_rows, *slide_rows, *extra_rows]
    )


async def show_insta_auto_setup(message: types.Message, state: FSMContext, *, edit: bool = False):
    data = await state.get_data()
    text = _insta_setup_summary(data)
    keyboard = _build_insta_setup_keyboard(data)
    if edit:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


async def start_insta_creation_setup(
    message: types.Message,
    state: FSMContext,
    *,
    intro: str | None = None,
):
    await state.clear()
    await state.update_data(
        insta_rewrite_style="concise",
        insta_color_palette="auto",
        insta_layout_style="auto",
        insta_slide_count="auto",
        insta_theme_override="auto",
        insta_visual_mode="auto",
        insta_card_format="auto",
        insta_custom_bg_bytes=None,
        insta_custom_bg_mime_type="image/jpeg",
    )
    await state.set_state(CarouselFlow.insta_auto_waiting_for_text)
    if intro:
        await message.answer(intro)
    await show_insta_auto_setup(message, state)


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    kb = [
        [KeyboardButton(text="🚀 Insta Auto")],
    ]
    # The "🆕 Карусель NEW" button is available to all allowed users
    # (admins are also in the allowed list, so this is a superset of
    # the previous admin-only gate).
    if is_user_allowed(message.from_user.id):
        kb.append([KeyboardButton(text="🆕 Карусель NEW")])
    kb.extend(
        [
            [KeyboardButton(text="🖼 Обложка")],
            [KeyboardButton(text="🎨 Настройки логотипа")],
            [KeyboardButton(text="📬 Обратная связь")],
            [KeyboardButton(text="Помощь")],
        ]
    )
    if message.from_user.id == ADMIN_ID:
        kb.append([KeyboardButton(text="/admin")])
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer(
        "Привет! Я бот для создания красивых каруселей.\n"
        "Отправь мне текст, голосовое сообщение или перешли пост, и я превращу это в слайды.",
        reply_markup=keyboard
    )


@router.message(Command("test_render"))
async def cmd_test_render_command(message: types.Message, state: FSMContext):
    """Command shortcut for the experimental renderer.

    Available to all allowed users (not just admins).
    """
    from handlers.carousel_flow import cmd_test_render

    if not is_user_allowed(message.from_user.id):
        await message.answer("⛔️ У вас нет доступа к этому боту.")
        return
    await cmd_test_render(message, state)


@router.message(F.text == "🆕 Карусель NEW")
async def cmd_test_render_menu(message: types.Message, state: FSMContext):
    """Main-menu entry to the experimental renderer.

    Available to all allowed users.
    """
    from handlers.carousel_flow import cmd_test_render

    if not is_user_allowed(message.from_user.id):
        await message.answer("⛔️ У вас нет доступа к этому боту.")
        return
    await cmd_test_render(message, state)


@router.message(F.text == "🚀 Insta Auto")
async def cmd_insta_auto(message: types.Message, state: FSMContext):
    await start_insta_creation_setup(message, state)


# ─── Callback handlers ───

@router.callback_query(
    StateFilter(CarouselFlow.insta_auto_waiting_for_text, CarouselFlow.insta_auto_waiting_for_background),
    F.data == "insta_noop",
)
async def insta_noop(callback: types.CallbackQuery):
    await callback.answer()


@router.callback_query(
    StateFilter(CarouselFlow.insta_auto_waiting_for_text, CarouselFlow.insta_auto_waiting_for_background),
    F.data.startswith("insta_layout:"),
)
async def insta_layout_selected(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    layout_style = callback.data.split(":", 1)[1]
    if layout_style not in LAYOUT_STYLE_LABELS and layout_style != "auto":
        return
    await state.update_data(insta_layout_style=layout_style)
    await state.set_state(CarouselFlow.insta_auto_waiting_for_text)
    await show_insta_auto_setup(callback.message, state, edit=True)


@router.callback_query(
    StateFilter(CarouselFlow.insta_auto_waiting_for_text, CarouselFlow.insta_auto_waiting_for_background),
    F.data.startswith("insta_color:"),
)
async def insta_color_selected(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    color_key = callback.data.split(":", 1)[1]
    if color_key not in INSTA_COLOR_TO_THEMES:
        return
    theme = INSTA_COLOR_TO_THEMES[color_key]
    await state.update_data(
        insta_color_palette=color_key,
        insta_theme_override=theme,
    )
    await state.set_state(CarouselFlow.insta_auto_waiting_for_text)
    await show_insta_auto_setup(callback.message, state, edit=True)


@router.callback_query(
    StateFilter(CarouselFlow.insta_auto_waiting_for_text, CarouselFlow.insta_auto_waiting_for_background),
    F.data.startswith("insta_copy:"),
)
async def insta_copy_selected(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    rewrite_style = callback.data.split(":", 1)[1]
    if rewrite_style not in INSTA_REWRITE_LABELS:
        return
    await state.update_data(insta_rewrite_style=rewrite_style)
    await state.set_state(CarouselFlow.insta_auto_waiting_for_text)
    await show_insta_auto_setup(callback.message, state, edit=True)


@router.callback_query(
    StateFilter(CarouselFlow.insta_auto_waiting_for_text, CarouselFlow.insta_auto_waiting_for_background),
    F.data.startswith("insta_slides:"),
)
async def insta_slide_count_selected(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    slide_count = callback.data.split(":", 1)[1]
    if slide_count not in INSTA_SLIDE_COUNT_LABELS:
        return
    await state.update_data(insta_slide_count=slide_count)
    await state.set_state(CarouselFlow.insta_auto_waiting_for_text)
    await show_insta_auto_setup(callback.message, state, edit=True)


@router.callback_query(
    StateFilter(CarouselFlow.insta_auto_waiting_for_text, CarouselFlow.insta_auto_waiting_for_background),
    F.data == "insta_upload_bg",
)
async def insta_upload_background(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CarouselFlow.insta_auto_waiting_for_background)
    await callback.message.edit_text(
        "📎 Пришлите одну картинку для фона карточек.\n\n"
        "Подойдет фото или файл изображения. После загрузки вы вернетесь на этот же экран настроек.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Назад к настройкам", callback_data="insta_back_to_setup")]
            ]
        ),
    )


@router.callback_query(CarouselFlow.insta_auto_waiting_for_background, F.data == "insta_back_to_setup")
async def insta_back_to_setup(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CarouselFlow.insta_auto_waiting_for_text)
    await show_insta_auto_setup(callback.message, state, edit=True)


@router.callback_query(
    StateFilter(CarouselFlow.insta_auto_waiting_for_text, CarouselFlow.insta_auto_waiting_for_background),
    F.data == "insta_reset_setup",
)
async def insta_reset_setup(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(
        insta_rewrite_style="concise",
        insta_color_palette="auto",
        insta_layout_style="auto",
        insta_slide_count="auto",
        insta_theme_override="auto",
        insta_visual_mode="auto",
        insta_card_format="auto",
        insta_custom_bg_bytes=None,
        insta_custom_bg_mime_type="image/jpeg",
    )
    await state.set_state(CarouselFlow.insta_auto_waiting_for_text)
    await show_insta_auto_setup(callback.message, state, edit=True)


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


@router.message(Settings.waiting_for_logo, F.text)
async def settings_save_logo(message: types.Message, state: FSMContext):
    new_logo = message.text.strip()
    if len(new_logo) > 20:
        await message.answer("⚠️ Слишком длинный логотип! Максимум 20 символов. Попробуйте снова.")
        return
    set_user_logo(message.from_user.id, new_logo)
    await state.clear()
    await message.answer(f"✅ Логотип изменен на: `{new_logo}`")


@router.message(Settings.waiting_for_logo)
async def settings_logo_wrong_input(message: types.Message):
    await message.answer("Отправьте логотип текстом, максимум 20 символов.")


@router.message(F.text == "📬 Обратная связь")
async def cmd_feedback_start(message: types.Message, state: FSMContext):
    await state.set_state(Feedback.waiting_for_message)
    await message.answer(
        "Напишите ваше сообщение, предложение или баг-репорт. Я передам разработчику."
    )


@router.message(Feedback.waiting_for_message)
async def cmd_feedback_receive(message: types.Message, state: FSMContext, bot: Bot):
    user = message.from_user
    username = f"@{user.username}" if user.username else "без username"
    admin_text = (
        f"📬 Обратная связь от {username} (ID: {user.id})\n\n"
        f"{message.text}"
    )
    try:
        await bot.send_message(ADMIN_ID, admin_text)
    except Exception as exc:
        logging.warning("Failed to forward feedback to admin %s: %s", ADMIN_ID, exc)
    await state.clear()
    await message.answer("✅ Спасибо! Ваше сообщение передано разработчику.")


@router.message(Command("help"))
@router.message(lambda message: message.text == "Помощь")
async def cmd_help(message: types.Message):
    await message.answer(
        "Как мной пользоваться:\n\n"
        "1. **Текст**: Просто отправь мне текст, и я сделаю карусель.\n"
        "2. **Голос**: Запиши голосовое, я расшифрую его и сделаю карусель.\n"
        "3. **Пересылка**: Перешли сообщение из канала, я сделаю из него слайды.\n\n"
        "Режимы:\n"
        "• `🚀 Insta Auto` — настрой стиль, цвета, подачу текста и отправь материал\n"
        "• `🖼 Обложка` — отдельная обложка из текста\n\n"
        "Команды:\n"
        "/start - Перезапуск\n"
        "/cancel - Отмена текущего действия\n"
        "/help - Справка"
    )
