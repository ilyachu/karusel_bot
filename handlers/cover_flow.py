import asyncio
from io import BytesIO
import logging

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup

from services.cover_renderer import (
    COVER_FORMATS,
    COVER_STYLES,
    CoverPlan,
    image_bytes_to_data_url,
    render_cover_html,
)
from services.gemini_client import generate_cover_plan
from utils.states import CarouselFlow
from utils.validation import validate_file_size, validate_text_length


router = Router()


@router.callback_query(F.data == "cover_noop")
async def cover_noop(callback: types.CallbackQuery):
    await callback.answer()


@router.message(F.text == "🖼 Обложка")
async def cover_start(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(CarouselFlow.cover_waiting_for_text)
    await message.answer(
        "🖼 Обложка\n\n"
        "Отправьте текст, пост или идею. Я соберу короткий headline и сделаю типографическую обложку.\n\n"
        "4:5 — основной Instagram feed формат. 16:9 — широкая обложка для Telegram, сайта, YouTube и landscape-поста."
    )


@router.message(CarouselFlow.cover_waiting_for_text, F.text)
async def cover_text_received(message: types.Message, state: FSMContext):
    is_valid, error_msg = validate_text_length(message.text)
    if not is_valid:
        await message.answer(error_msg)
        return
    await state.update_data(cover_text=message.text)
    await state.set_state(CarouselFlow.cover_choosing_format)
    await message.answer(
        "Сначала выберите формат обложки.\n\n"
        "4:5 — основной Instagram feed. 16:9 — широкая для Telegram, сайта, YouTube. 9:16 — stories/reels.",
        reply_markup=_format_keyboard(),
    )


@router.callback_query(CarouselFlow.cover_choosing_style, F.data.startswith("cover_style:"))
async def cover_style_selected(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    style = callback.data.split(":", 1)[1]
    if style not in COVER_STYLES:
        style = "orange_poster"
    data = await state.get_data()
    format_key = data.get("cover_format_key", "post")
    base_text = data.get("cover_text", "")
    background_data_url = data.get("cover_background_data_url", "")
    await state.update_data(
        cover_style=style,
        cover_format_key=format_key,
        cover_text=base_text,
        cover_background_data_url=background_data_url,
    )
    await state.set_state(CarouselFlow.cover_processing)
    status = await callback.message.answer("🎨 Собираю обложку...")

    try:
        raw_plan = await generate_cover_plan(base_text, style, format_key)
        raw_plan["background_data_url"] = background_data_url
        plan = CoverPlan(**raw_plan)
        rendered_bytes = await asyncio.to_thread(render_cover_html, plan)
    except Exception as exc:
        logging.exception("Cover generation failed: %s", exc)
        await status.edit_text("😔 Не удалось собрать обложку. Попробуйте другой текст.")
        await state.clear()
        return

    await status.delete()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Другой вариант", callback_data="cover_regenerate"),
            InlineKeyboardButton(text="🎨 Другой стиль", callback_data="cover_change_style"),
        ],
    ])
    await callback.message.answer_photo(
        BufferedInputFile(
            rendered_bytes,
            filename=f"cover_{plan.style}_{plan.format_key}.png",
        ),
        caption=(
            "🖼 Обложка готова\n"
            f"Стиль: {COVER_STYLES[plan.style]['label']}\n"
            f"Формат: {COVER_FORMATS[plan.format_key]['label']}\n"
            f"Фон: {'свой' if plan.background_data_url else 'стандартный'}\n"
            "Автор: chu_il"
        ),
        reply_markup=kb,
    )
    # НЕ очищаем state — данные нужны для регенерации и смены стиля


@router.callback_query(CarouselFlow.cover_choosing_background, F.data == "cover_bg:default")
async def cover_default_background_selected(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(cover_background_data_url="")
    await state.set_state(CarouselFlow.cover_choosing_style)
    await callback.message.edit_text(
        "Выберите конкретный стиль обложки.\n\nСначала идут группы, ниже под каждой группой — сами стили.",
        reply_markup=_style_keyboard(),
    )


@router.callback_query(CarouselFlow.cover_choosing_background, F.data == "cover_bg:upload")
async def cover_upload_background_selected(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CarouselFlow.cover_waiting_for_background)
    await callback.message.edit_text(
        "Загрузите фон: фото или файл изображения до 10 МБ.\n\n"
        "Я поставлю его full-bleed под типографику и добавлю стиль выбранного режима."
    )


@router.message(CarouselFlow.cover_waiting_for_background, F.photo | F.document)
async def cover_background_uploaded(message: types.Message, state: FSMContext, bot):
    try:
        file_id = ""
        file_size = 0
        mime_type = "image/jpeg"
        if message.photo:
            photo = message.photo[-1]
            file_id = photo.file_id
            file_size = photo.file_size or 0
        elif message.document:
            if not message.document.mime_type or not message.document.mime_type.startswith("image/"):
                await message.answer("⚠️ Отправьте именно изображение: JPG, PNG или WEBP.")
                return
            file_id = message.document.file_id
            file_size = message.document.file_size or 0
            mime_type = message.document.mime_type

        if file_size:
            is_valid, error_msg = validate_file_size(file_size)
            if not is_valid:
                await message.answer(error_msg)
                return

        file = await bot.get_file(file_id)
        file_bytes = BytesIO()
        await bot.download_file(file.file_path, file_bytes)
        data_url = image_bytes_to_data_url(file_bytes.getvalue(), mime_type)
        await state.update_data(cover_background_data_url=data_url)
        await state.set_state(CarouselFlow.cover_choosing_style)
        await message.answer(
            "Фон загружен. Теперь выберите конкретный стиль обложки.",
            reply_markup=_style_keyboard(),
        )
    except Exception as exc:
        logging.exception("Cover background upload failed: %s", exc)
        await message.answer("😔 Не удалось загрузить фон. Попробуйте другое изображение.")


@router.message(CarouselFlow.cover_waiting_for_background)
async def cover_background_wrong_file(message: types.Message):
    await message.answer("Отправьте фото или файл изображения.")


@router.callback_query(CarouselFlow.cover_choosing_format, F.data.startswith("cover_format:"))
async def cover_format_selected(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    format_key = callback.data.split(":", 1)[1]
    if format_key not in COVER_FORMATS:
        format_key = "post"
    await state.update_data(cover_format_key=format_key)
    await state.set_state(CarouselFlow.cover_choosing_background)
    await callback.message.edit_text(
        "Теперь выберите фон обложки:",
        reply_markup=_background_keyboard(),
    )


def _style_keyboard() -> InlineKeyboardMarkup:
    groups = [
        ("Группа: плакатные", ["orange_poster", "acid_poster", "red_manifesto", "blur_field"]),
        ("Группа: типографичные", ["blue_type", "grid_steps", "paper_brief"]),
        ("Группа: атмосферные", ["retro_polaroid", "quiet_editorial", "chalk_notes"]),
    ]
    rows = []
    for group_name, styles in groups:
        rows.append([InlineKeyboardButton(text=f"— {group_name} —", callback_data="cover_noop")])
        for i in range(0, len(styles), 2):
            chunk = styles[i:i+2]
            rows.append([
                InlineKeyboardButton(
                    text=COVER_STYLES[s].get("button", COVER_STYLES[s]["label"]),
                    callback_data=f"cover_style:{s}",
                )
                for s in chunk
            ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _background_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Стандартный фон", callback_data="cover_bg:default")],
            [InlineKeyboardButton(text="Загрузить свой фон", callback_data="cover_bg:upload")],
        ]
    )


def _format_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="4:5 Instagram feed", callback_data="cover_format:post")],
            [InlineKeyboardButton(text="16:9 широкая", callback_data="cover_format:wide")],
            [InlineKeyboardButton(text="9:16 stories/reels", callback_data="cover_format:story")],
        ]
    )


@router.callback_query(F.data == "cover_regenerate")
async def cover_regenerate(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    style = data.get("cover_style", "orange_poster")
    format_key = data.get("cover_format_key", "post")
    base_text = data.get("cover_text", "")
    background_data_url = data.get("cover_background_data_url", "")
    await state.set_state(CarouselFlow.cover_processing)
    status = await callback.message.answer("🎨 Генерирую другой вариант...")

    try:
        raw_plan = await generate_cover_plan(base_text, style, format_key)
        raw_plan["background_data_url"] = background_data_url
        plan = CoverPlan(**raw_plan)
        rendered_bytes = await asyncio.to_thread(render_cover_html, plan)
    except Exception as exc:
        logging.exception("Cover regeneration failed: %s", exc)
        await status.edit_text("😔 Не удалось сгенерировать. Попробуйте снова.")
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
    await callback.message.answer_photo(
        BufferedInputFile(
            rendered_bytes,
            filename=f"cover_{plan.style}_{plan.format_key}.png",
        ),
        caption=(
            "🖼 Обложка готова\n"
            f"Стиль: {COVER_STYLES[plan.style]['label']}\n"
            f"Формат: {COVER_FORMATS[plan.format_key]['label']}\n"
            f"Фон: {'свой' if plan.background_data_url else 'стандартный'}\n"
            "Автор: chu_il"
        ),
        reply_markup=kb,
    )
    # НЕ очищаем state — данные нужны для регенерации и смены стиля


@router.callback_query(F.data == "cover_change_style")
async def cover_change_style(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CarouselFlow.cover_choosing_style)
    await callback.message.answer(
        "Выберите другой конкретный стиль обложки:",
        reply_markup=_style_keyboard(),
    )


@router.callback_query(F.data == "cover_publish")
async def cover_publish(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(
        "✅ Обложка сохранена! Можете скачать её из чата или отправить «🖼 Обложка» для новой."
    )
    await state.clear()
