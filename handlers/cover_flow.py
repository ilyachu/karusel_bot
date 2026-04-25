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


@router.message(F.text == "🖼 Обложка")
async def cover_start(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(CarouselFlow.cover_waiting_for_text)
    await message.answer(
        "🖼 Обложка\n\n"
        "Отправьте текст, пост или идею. Я соберу короткий headline и сделаю poster/retro PNG."
    )


@router.message(CarouselFlow.cover_waiting_for_text, F.text)
async def cover_text_received(message: types.Message, state: FSMContext):
    is_valid, error_msg = validate_text_length(message.text)
    if not is_valid:
        await message.answer(error_msg)
        return
    await state.update_data(cover_text=message.text)
    await state.set_state(CarouselFlow.cover_choosing_style)
    await message.answer(
        "Выберите визуальный режим:",
        reply_markup=_style_keyboard(),
    )


@router.callback_query(CarouselFlow.cover_choosing_style, F.data.startswith("cover_style:"))
async def cover_style_selected(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    style = callback.data.split(":", 1)[1]
    if style not in COVER_STYLES:
        style = "orange_poster"
    await state.update_data(cover_style=style)
    await state.set_state(CarouselFlow.cover_choosing_background)
    await callback.message.edit_text(
        "Фон обложки:",
        reply_markup=_background_keyboard(),
    )


@router.callback_query(CarouselFlow.cover_choosing_background, F.data == "cover_bg:default")
async def cover_default_background_selected(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(cover_background_data_url="")
    await state.set_state(CarouselFlow.cover_choosing_format)
    await callback.message.edit_text(
        "Выберите формат обложки:",
        reply_markup=_format_keyboard(),
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
        await state.set_state(CarouselFlow.cover_choosing_format)
        await message.answer(
            "Фон загружен. Выберите формат обложки:",
            reply_markup=_format_keyboard(),
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
    data = await state.get_data()
    style = data.get("cover_style", "orange_poster")
    base_text = data.get("cover_text", "")
    background_data_url = data.get("cover_background_data_url", "")
    await state.set_state(CarouselFlow.cover_processing)
    await callback.message.edit_text("🎨 Собираю обложку...")

    try:
        raw_plan = await generate_cover_plan(base_text, style, format_key)
        raw_plan["background_data_url"] = background_data_url
        plan = CoverPlan(**raw_plan)
        rendered_bytes = await asyncio.to_thread(render_cover_html, plan)
    except Exception as exc:
        logging.exception("Cover generation failed: %s", exc)
        await callback.message.edit_text("😔 Не удалось собрать обложку. Попробуйте другой текст.")
        await state.clear()
        return

    await callback.message.delete()
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
    )
    await state.clear()


def _style_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Orange Poster", callback_data="cover_style:orange_poster")],
            [InlineKeyboardButton(text="Acid Poster", callback_data="cover_style:acid_poster")],
            [InlineKeyboardButton(text="Retro Film Burn", callback_data="cover_style:retro_polaroid")],
            [InlineKeyboardButton(text="Blue Type", callback_data="cover_style:blue_type")],
            [InlineKeyboardButton(text="Grid Steps", callback_data="cover_style:grid_steps")],
            [InlineKeyboardButton(text="Blur Field", callback_data="cover_style:blur_field")],
        ]
    )


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
            [InlineKeyboardButton(text="16:9", callback_data="cover_format:wide")],
            [InlineKeyboardButton(text="4:5", callback_data="cover_format:post")],
            [InlineKeyboardButton(text="9:16", callback_data="cover_format:story")],
        ]
    )
