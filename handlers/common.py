import asyncio
import logging

from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from utils.database import get_user_logo, set_user_logo, reset_user_logo
from utils.states import CarouselFlow
from utils.validation import validate_text_length
from services.layout_engine import LAYOUT_STYLE_LABELS, THEME_LABELS, VISUAL_MODE_LABELS
from config import ADMIN_ID

class Settings(StatesGroup):
    waiting_for_logo = State()

router = Router()

INSTA_REWRITE_LABELS = {
    "concise": "Коротко и ясно",
    "educational": "Объяснить по шагам",
    "marketing": "Сильнее продать идею",
    "exact": "Бережно сохранить текст",
}

INSTA_VISUAL_PRESETS = {
    "auto": {
        "label": "Авто",
        "button": "Авто",
        "theme": "auto",
        "visual_mode": "auto",
        "description": "сам подберу визуал по тексту",
    },
    "calm": {
        "label": "Спокойный",
        "button": "Спокойный",
        "theme": "memory_archive",
        "visual_mode": "editorial",
        "description": "спокойные цвета, понятный шрифт, чистый разбор",
    },
    "business": {
        "label": "Мемо",
        "button": "Мемо",
        "theme": "founder_brief",
        "visual_mode": "brief",
        "description": "строго, как продуктовая заметка или решение",
    },
    "facts": {
        "label": "Факты",
        "button": "Цифры",
        "theme": "research_mono",
        "visual_mode": "data",
        "description": "для цифр, сравнений, новостей и аналитики",
    },
    "contrast": {
        "label": "Контрастный",
        "button": "Контраст",
        "theme": "growth_black",
        "visual_mode": "editorial",
        "description": "как обложки: темнее, крупнее, заметнее",
    },
}

INSTA_CARD_FORMAT_LABELS = {
    "auto": "Авто",
    "editorial": "Крупный",
    "brief": "Мемо",
    "data": "Факты",
    "classic": "Читабельно",
}

INSTA_CARD_FORMAT_DESCRIPTIONS = {
    "auto": "бот сам выберет сетку",
    "editorial": "крупный дизайнерский заголовок",
    "brief": "строго, как деловой документ",
    "data": "акцент на цифры и короткие факты",
    "classic": "понятный шрифт и спокойная верстка",
}

INSTA_CARD_SIZE_LABEL = "1080×1350, вертикаль 4:5"


def build_insta_theme_keyboard(selected: str = "auto") -> InlineKeyboardMarkup:
    options = ["auto", "memory_archive", "founder_brief", "growth_black", "research_mono"]
    rows = []
    for option in options:
        label = THEME_LABELS[option]
        if option == selected:
            label = f"✅ {label}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"insta_theme:{option}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_insta_auto_keyboard(selected_theme: str = "auto", selected_visual_mode: str = "auto") -> InlineKeyboardMarkup:
    rows = build_insta_theme_keyboard(selected_theme).inline_keyboard
    visual_options = ("auto", "classic", "editorial", "brief", "data")
    visual_rows = []
    for option in visual_options:
        label = VISUAL_MODE_LABELS[option]
        if option == selected_visual_mode:
            label = f"✅ {label}"
        visual_rows.append(InlineKeyboardButton(text=label, callback_data=f"insta_visual:{option}"))
    rows.extend([visual_rows[:2], visual_rows[2:]])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _insta_setup_summary(data: dict) -> str:
    visual_key = data.get("insta_visual_preset", "auto")
    custom_bg = data.get("insta_custom_bg_bytes")

    visual = INSTA_VISUAL_PRESETS.get(visual_key, INSTA_VISUAL_PRESETS["auto"])
    visual_title = "Своя картинка" if custom_bg else visual["label"]
    visual_desc = "загруженный фон для всех слайдов" if custom_bg else visual["description"]

    presets_list = "\n".join(
        f"• {p['label']} — {p['description']}"
        for p in INSTA_VISUAL_PRESETS.values()
    )

    return (
        "🚀 Insta Auto\n\n"
        "Выберите пресет, потом отправьте текст.\n\n"
        f"🎨 Текущий: {visual_title}\n"
        f"   {visual_desc}\n\n"
        f"Доступные пресеты:\n{presets_list}\n\n"
        f"📐 Формат: 1080×1350 (4:5)\n"
        "📎 Или загрузите свой фон"
    )


def _build_insta_setup_keyboard(data: dict | None = None) -> InlineKeyboardMarkup:
    data = data or {}
    visual_key = data.get("insta_visual_preset", "auto")
    custom_bg = data.get("insta_custom_bg_bytes")

    def section(title: str) -> list[InlineKeyboardButton]:
        return [InlineKeyboardButton(text=title, callback_data="insta_noop")]

    visual_rows = []
    visual_rows.append(section("🎨 ПРЕСЕТ"))
    visual_buttons = []
    for key in ("auto", "calm", "business", "facts", "contrast"):
        label = INSTA_VISUAL_PRESETS[key].get("button", INSTA_VISUAL_PRESETS[key]["label"])
        if key == visual_key and not custom_bg:
            label = f"✅ {label}"
        visual_buttons.append(InlineKeyboardButton(text=label, callback_data=f"insta_pack:{key}"))
    visual_rows.extend([visual_buttons[:3], visual_buttons[3:]])

    custom_label = "✅ Свой фон" if custom_bg else "📎 Свой фон"
    action_rows = [
        [InlineKeyboardButton(text=custom_label, callback_data="insta_upload_bg")],
        [InlineKeyboardButton(text="🖼 Обложка в этом стиле", callback_data="insta_make_cover")],
    ]

    return InlineKeyboardMarkup(
        inline_keyboard=[
            *visual_rows,
            *action_rows,
            [InlineKeyboardButton(text="🔄 Сбросить", callback_data="insta_reset_setup")],
        ]
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
        insta_visual_preset="auto",
        insta_theme_override="auto",
        insta_visual_mode="auto",
        insta_card_format="auto",
        insta_layout_style="auto",
    )
    await state.set_state(CarouselFlow.insta_auto_waiting_for_text)
    if intro:
        await message.answer(intro)
    await show_insta_auto_setup(message, state)

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()  # Clear any existing state
    kb = [
        [KeyboardButton(text="Создать карусель")],
        [KeyboardButton(text="🚀 Insta Auto")],
        [KeyboardButton(text="🖼 Обложка")],
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
    await start_insta_creation_setup(
        message,
        state,
        intro=(
            "📝 Создать карусель\n\n"
            "Теперь этот режим использует тот же Instagram-ready pipeline: текст, дизайн, caption, export и публикация."
        ),
    )

@router.message(F.text == "🚀 Insta Auto")
async def cmd_insta_auto(message: types.Message, state: FSMContext):
    await start_insta_creation_setup(message, state)


@router.callback_query(CarouselFlow.insta_auto_waiting_for_text, F.data.startswith("insta_theme:"))
async def insta_theme_selected(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    theme = callback.data.split(":", 1)[1]
    if theme not in THEME_LABELS:
        return
    theme_to_preset = {
        "auto": "auto",
        "memory_archive": "calm",
        "founder_brief": "business",
        "growth_black": "contrast",
        "research_mono": "facts",
    }
    preset_key = theme_to_preset.get(theme, "auto")
    preset = INSTA_VISUAL_PRESETS[preset_key]
    await state.update_data(
        insta_visual_preset=preset_key,
        insta_theme_override=preset["theme"],
        insta_visual_mode=preset["visual_mode"],
        insta_card_format=preset["visual_mode"],
        insta_custom_bg_bytes=None,
    )
    await show_insta_auto_setup(callback.message, state, edit=True)


@router.callback_query(CarouselFlow.insta_auto_waiting_for_text, F.data.startswith("insta_visual:"))
async def insta_visual_selected(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    visual_mode = callback.data.split(":", 1)[1]
    if visual_mode not in VISUAL_MODE_LABELS:
        return
    card_format = visual_mode if visual_mode in INSTA_CARD_FORMAT_LABELS else "auto"
    await state.update_data(insta_visual_mode=visual_mode, insta_card_format=card_format)
    await show_insta_auto_setup(callback.message, state, edit=True)


@router.callback_query(
    StateFilter(CarouselFlow.insta_auto_waiting_for_text, CarouselFlow.insta_auto_waiting_for_background),
    F.data == "insta_noop",
)
async def insta_noop(callback: types.CallbackQuery):
    await callback.answer()


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
    F.data.startswith("insta_pack:"),
)
async def insta_pack_selected(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    preset_key = callback.data.split(":", 1)[1]
    preset = INSTA_VISUAL_PRESETS.get(preset_key)
    if not preset:
        return
    await state.update_data(
        insta_visual_preset=preset_key,
        insta_theme_override=preset["theme"],
        insta_visual_mode=preset["visual_mode"],
        insta_card_format=preset["visual_mode"],
        insta_custom_bg_bytes=None,
    )
    await state.set_state(CarouselFlow.insta_auto_waiting_for_text)
    await show_insta_auto_setup(callback.message, state, edit=True)


@router.callback_query(
    StateFilter(CarouselFlow.insta_auto_waiting_for_text, CarouselFlow.insta_auto_waiting_for_background),
    F.data.startswith("insta_format:"),
)
async def insta_format_selected(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    card_format = callback.data.split(":", 1)[1]
    if card_format not in INSTA_CARD_FORMAT_LABELS:
        return
    updates = {"insta_card_format": card_format}
    if card_format != "auto":
        updates["insta_visual_mode"] = card_format
    else:
        data = await state.get_data()
        preset = INSTA_VISUAL_PRESETS.get(data.get("insta_visual_preset", "auto"), INSTA_VISUAL_PRESETS["auto"])
        updates["insta_visual_mode"] = preset["visual_mode"]
    await state.update_data(**updates)
    await state.set_state(CarouselFlow.insta_auto_waiting_for_text)
    await show_insta_auto_setup(callback.message, state, edit=True)


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
        insta_visual_preset="auto",
        insta_theme_override="auto",
        insta_visual_mode="auto",
        insta_card_format="auto",
        insta_layout_style="auto",
        insta_custom_bg_bytes=None,
    )
    await state.set_state(CarouselFlow.insta_auto_waiting_for_text)
    await show_insta_auto_setup(callback.message, state, edit=True)


@router.callback_query(
    StateFilter(CarouselFlow.insta_auto_waiting_for_text, CarouselFlow.insta_auto_waiting_for_background),
    F.data == "insta_make_cover",
)
async def insta_make_cover(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CarouselFlow.insta_cover_waiting_for_text)
    await callback.message.edit_text(
        "🖼 Обложка в этом стиле\n\n"
        "Отправьте текст для обложки. Я сгенерирую обложку в текущем визуальном стиле.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад к настройкам", callback_data="insta_cover_back")]
        ]),
    )


@router.callback_query(CarouselFlow.insta_cover_waiting_for_text, F.data == "insta_cover_back")
async def insta_cover_back(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CarouselFlow.insta_auto_waiting_for_text)
    await show_insta_auto_setup(callback.message, state, edit=True)


@router.message(CarouselFlow.insta_cover_waiting_for_text, F.text)
async def insta_cover_text_received(message: types.Message, state: FSMContext):
    is_valid, error_msg = validate_text_length(message.text)
    if not is_valid:
        await message.answer(error_msg)
        return
    data = await state.get_data()
    visual_mode = data.get("insta_visual_mode", "auto")
    from services.cover_renderer import VISUAL_MODE_TO_COVER_STYLE, COVER_FORMATS, COVER_STYLES, CoverPlan, render_cover_html
    from services.gemini_client import generate_cover_plan
    cover_style = VISUAL_MODE_TO_COVER_STYLE.get(visual_mode, "orange_poster")
    base_text = message.text
    format_key = "post"
    await state.set_state(CarouselFlow.cover_processing)
    status = await message.answer("🎨 Собираю обложку...")

    try:
        raw_plan = await generate_cover_plan(base_text, cover_style, format_key)
        plan = CoverPlan(**raw_plan)
        rendered_bytes = await asyncio.to_thread(render_cover_html, plan)
    except Exception as exc:
        logging.exception("Cover generation failed: %s", exc)
        await status.edit_text("😔 Не удалось собрать обложку.")
        await state.clear()
        return

    await status.delete()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Опубликовать", callback_data="cover_publish"),
            InlineKeyboardButton(text="🔄 Другой вариант", callback_data="cover_regenerate"),
        ],
        [InlineKeyboardButton(text="🎨 Другой стиль", callback_data="cover_change_style")],
    ])
    await message.answer_photo(
        BufferedInputFile(
            rendered_bytes,
            filename=f"cover_{plan.style}_{plan.format_key}.png",
        ),
        caption=(
            "🖼 Обложка готова\n"
            f"Стиль: {COVER_STYLES[plan.style]['label']}\n"
            f"Формат: {COVER_FORMATS[plan.format_key]['label']}\n"
            "Автор: chu_il"
        ),
        reply_markup=kb,
    )
    await state.update_data(
        cover_text=base_text,
        cover_style=cover_style,
        cover_format_key=format_key,
        cover_background_data_url="",
    )
    await state.clear()

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
        "• `Создать карусель` — ручная сборка с готовыми шаблонами или своим фоном\n"
        "• `🚀 Insta Auto` — минимум действий, сразу карусель под Instagram\n"
        "• `🖼 Обложка` — отдельная poster/retro обложка из текста\n\n"
        "Команды:\n"
        "/start - Перезапуск\n"
        "/cancel - Отмена текущего действия\n"
        "/help - Справка"
    )
