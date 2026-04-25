import asyncio
import json
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, BufferedInputFile
from aiogram.enums import ChatAction

from utils.states import CarouselFlow
from utils.background_styles import BACKGROUND_STYLES, REWRITE_STYLES, PRESETS
from utils.messages import add_step_indicator, add_back_button
from utils.validation import validate_text_length, validate_file_size
import logging
import os
from io import BytesIO
from dataclasses import asdict
from config import (
    EXPORT_PUBLIC_BASE_URL,
    INSTAGRAM_ACCESS_TOKEN,
    INSTAGRAM_API_BASE,
    INSTAGRAM_MEDIA_PROXY_BASE_URL,
    INSTAGRAM_MEDIA_PROXY_BOT_ALIAS,
    INSTAGRAM_MEDIA_PROXY_SECRET,
    INSTAGRAM_MEDIA_PROXY_TTL_SECONDS,
    INSTAGRAM_USER_ID,
    THREADS_ACCESS_TOKEN,
    THREADS_API_BASE,
    THREADS_MEDIA_PROXY_BASE_URL,
    THREADS_MEDIA_PROXY_BOT_ALIAS,
    THREADS_MEDIA_PROXY_SECRET,
    THREADS_MEDIA_PROXY_TTL_SECONDS,
    THREADS_USER_ID,
)
from utils.database import (
    create_meta_publish_job,
    create_threads_publish_job,
    get_export_package,
    get_user_logo,
    save_export_package,
)

from services.gemini_client import (
    analyze_text_and_propose_slides,
    generate_final_slides,
    generate_instagram_carousel_plan,
    generate_instagram_caption,
    generate_threads_summary,
)
from services.export_hosting import build_public_export_info
from services.instagram_package import build_instagram_export, update_export_metadata
from services.layout_engine import (
    DEFAULT_CTA_BODY,
    DEFAULT_CTA_TITLE,
    THEME_LABELS,
    VISUAL_MODE_LABELS,
    apply_theme_selection_policy,
    apply_theme_override,
    build_fallback_instagram_plan,
    build_instagram_layout_specs,
    enforce_default_cta_slide,
    parse_carousel_plan,
    resolve_preset_visual_profile,
    resolve_visual_mode,
)
from services.html_renderer import browser_binaries_hint, render_layout_spec_html
from services.instagram_publisher import InstagramPublisher
from services.meta_publish import MetaCredentials, build_carousel_publish_plan, load_export_package
from services.threads_publish import build_threads_publish_plan, serialize_threads_publish_plan
from services.threads_publisher import ThreadsPublisher
from services.openai_speech import transcribe_voice
from services.fal_client import generate_background
from services.image_renderer import render_layout_spec, render_slide
from handlers.common import (
    INSTA_CARD_FORMAT_LABELS,
    INSTA_REWRITE_LABELS,
    show_insta_auto_setup,
)

router = Router()

# --- 1. Input Handling ---

# --- 1. Input Handling ---

# Move generic text handler to the bottom or restrict it to default state
@router.message(F.text & ~F.text.in_({"Помощь", "Создать карусель", "🚀 Insta Auto", "🖼 Обложка", "⚡️ Быстрый режим", "/start", "/help", "/cancel"}), StateFilter(None))
async def handle_text_input(message: types.Message, state: FSMContext):
    # Validate text length
    is_valid, error_msg = validate_text_length(message.text)
    if not is_valid:
        await message.answer(error_msg)
        return
    await process_text_input(message, message.text, state)

@router.message(F.voice, StateFilter(None))
async def handle_voice_input(message: types.Message, state: FSMContext, bot):
    await message.answer("🎤 Слушаю и распознаю...")
    
    file_id = message.voice.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    
    # Validate voice duration
    if message.voice.duration and message.voice.duration > 300:  # 5 minutes
        await message.answer("⚠️ Голосовое сообщение слишком длинное! Максимум 5 минут.")
        return
    
    destination = f"voice_{file_id}.ogg"
    
    try:
        await bot.download_file(file_path, destination)
        
        # Show typing indicator during transcription
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        
        text = await transcribe_voice(destination)
        
        if not text:
            await message.answer("😔 Не удалось распознать текст. Попробуйте еще раз.")
            return

        await state.update_data(draft_text=text)
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Все верно", callback_data="voice_confirm")],
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data="voice_edit")]
        ])
    finally:
        # Ensure cleanup even if error occurs
        if os.path.exists(destination):
            os.remove(destination)
    
    await message.answer(f"📝 Распознанный текст:\n\n{text}", reply_markup=kb)
    await state.set_state(CarouselFlow.waiting_for_text_confirmation)

@router.message((F.forward_from | F.forward_from_chat), StateFilter(None))
async def handle_forward(message: types.Message, state: FSMContext):
    text = message.text or message.caption or ""
    if not text:
        await message.answer("⚠️ В этом сообщении нет текста.")
        return
    await process_text_input(message, text, state)

# --- 2. Voice Confirmation Flow ---

@router.callback_query(CarouselFlow.waiting_for_text_confirmation, F.data == "voice_confirm")
async def voice_confirm(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    text = data.get("draft_text", "")
    await callback.message.answer("✅ Принято. Анализирую текст...")
    await process_text_input(callback.message, text, state)

@router.callback_query(CarouselFlow.waiting_for_text_confirmation, F.data == "voice_edit")
async def voice_edit(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("✍️ Отправьте мне исправленный текст.")

@router.message(CarouselFlow.waiting_for_text_confirmation, F.text)
async def voice_edit_text(message: types.Message, state: FSMContext):
    await message.answer("✅ Текст обновлен. Анализирую...")
    await process_text_input(message, message.text, state)


@router.message(CarouselFlow.insta_auto_waiting_for_text, F.text)
async def insta_auto_text(message: types.Message, state: FSMContext):
    await run_insta_auto_pipeline(message, message.text, state)


@router.message(CarouselFlow.insta_auto_waiting_for_text, F.voice)
async def insta_auto_voice(message: types.Message, state: FSMContext, bot):
    await message.answer("🎤 Слушаю и собираю Insta-ready карусель...")
    file_id = message.voice.file_id
    file = await bot.get_file(file_id)
    destination = f"voice_{file_id}.ogg"

    try:
        await bot.download_file(file.file_path, destination)
        text = await transcribe_voice(destination)
    finally:
        if os.path.exists(destination):
            os.remove(destination)

    if not text:
        await message.answer("😔 Не удалось распознать голосовое. Попробуйте текстом.")
        return

    await run_insta_auto_pipeline(message, text, state)


@router.message(CarouselFlow.insta_auto_waiting_for_text, F.forward_from | F.forward_from_chat)
async def insta_auto_forward(message: types.Message, state: FSMContext):
    text = message.text or message.caption or ""
    if not text:
        await message.answer("⚠️ В этом сообщении нет текста.")
        return
    await run_insta_auto_pipeline(message, text, state)


@router.message(CarouselFlow.insta_auto_waiting_for_background, F.photo | F.document)
async def insta_auto_custom_background(message: types.Message, state: FSMContext, bot):
    if message.document:
        if not message.document.mime_type or not message.document.mime_type.startswith("image/"):
            await message.answer("⚠️ Нужна именно картинка: фото или файл изображения.")
            return
        file_id = message.document.file_id
        file_size = message.document.file_size or 0
    else:
        photo = message.photo[-1]
        file_id = photo.file_id
        file_size = photo.file_size or 0

    if file_size:
        is_valid, error_msg = validate_file_size(file_size)
        if not is_valid:
            await message.answer(error_msg)
            return

    file = await bot.get_file(file_id)
    file_bytes = BytesIO()
    await bot.download_file(file.file_path, file_bytes)
    file_bytes.seek(0)

    await state.update_data(
        insta_custom_bg_bytes=file_bytes.getvalue(),
        insta_visual_preset="custom",
    )
    await state.set_state(CarouselFlow.insta_auto_waiting_for_text)
    await message.answer("✅ Фон загружен. Теперь можно отправить текст или поменять настройки.")
    await show_insta_auto_setup(message, state)


@router.message(CarouselFlow.insta_auto_waiting_for_background, F.text)
async def insta_auto_background_text_fallback(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Действие отменено.")
        return
    await message.answer("📎 Сейчас жду картинку для фона. Отправьте фото или нажмите «Назад к настройкам».")


async def run_insta_auto_pipeline(message: types.Message, text: str, state: FSMContext):
    is_valid, error_msg = validate_text_length(text)
    if not is_valid:
        await message.answer(error_msg)
        return

    await state.update_data(base_text=text)
    status = await message.answer("🚀 Собираю Insta-ready карусель...")
    await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_PHOTO)
    data = await state.get_data()
    rewrite_style = data.get("insta_rewrite_style", "concise")

    analysis = await analyze_text_and_propose_slides(text)
    recommended = analysis.get("recommended_slides", 6)
    target_slides = max(4, min(7, recommended))

    raw_plan = await generate_instagram_carousel_plan(text, target_slides, rewrite_style)
    if raw_plan:
        carousel_plan = parse_carousel_plan(raw_plan)
        slides_content = [
            {"title": slide.title, "body": slide.body}
            for slide in carousel_plan.slides
        ]
    else:
        slides_content = await generate_final_slides(text, target_slides, rewrite_style)

    if not slides_content:
        await status.edit_text("😔 Не удалось собрать тексты для карусели.")
        return

    if not raw_plan:
        carousel_plan = build_fallback_instagram_plan(slides_content)
    visual_mode = data.get("insta_visual_mode", "auto")
    carousel_plan = enforce_default_cta_slide(carousel_plan, visual_mode=visual_mode)
    slides_content = [
        {"title": slide.title, "body": slide.body}
        for slide in carousel_plan.slides
    ]
    theme_override = data.get("insta_theme_override", "auto")
    if theme_override and theme_override != "auto":
        carousel_plan, theme_decision = apply_theme_override(carousel_plan, theme_override)
    else:
        carousel_plan, theme_decision = apply_theme_selection_policy(carousel_plan, text)

    visual_decision = resolve_visual_mode(carousel_plan, visual_mode)
    caption = await generate_instagram_caption(text, slides_content)
    threads_summary = await generate_threads_summary(text, slides_content, caption)
    user_logo = get_user_logo(message.chat.id)
    layout_specs = build_instagram_layout_specs(carousel_plan, visual_mode=visual_mode)
    custom_bg_bytes = data.get("insta_custom_bg_bytes")

    rendered_buffers: list[BytesIO] = []
    media_group = []
    render_mode = "html"
    for layout_spec in layout_specs:
        if custom_bg_bytes:
            render_mode = "pillow-custom-bg"
            image_buffer = await asyncio.to_thread(
                render_layout_spec,
                layout_spec,
                user_logo,
                BytesIO(custom_bg_bytes),
            )
            rendered_bytes = image_buffer.getvalue()
        else:
            try:
                rendered_bytes = await asyncio.to_thread(
                    render_layout_spec_html,
                    layout_spec,
                    user_logo,
                )
            except Exception as exc:
                logging.warning("HTML renderer unavailable, falling back to Pillow: %s", exc)
                render_mode = "pillow-fallback"
                image_buffer = render_layout_spec(
                    layout_spec,
                    logo_text=user_logo,
                    bg_source=None,
                )
                rendered_bytes = image_buffer.getvalue()
        rendered_buffers.append(BytesIO(rendered_bytes))
        media_group.append(
            InputMediaPhoto(
                media=BufferedInputFile(
                    rendered_bytes,
                    filename=f"instagram_slide_{layout_spec.slide_index}.png",
                )
            )
        )

    export_dir = build_instagram_export(
        rendered_buffers,
        caption,
        text,
        message.chat.id,
        extra_metadata={
            "carousel_plan": asdict(carousel_plan),
            "layout_specs": [spec.to_dict() for spec in layout_specs],
            "render_mode": render_mode,
            "theme_decision": theme_decision.to_dict() if theme_decision else None,
            "visual_mode": visual_mode,
            "resolved_visual_mode": visual_decision.resolved_mode,
            "visual_decision": visual_decision.to_dict(),
            "rewrite_style": rewrite_style,
            "custom_background": bool(custom_bg_bytes),
            "threads_summary": threads_summary,
        },
    )
    export_package = load_export_package(export_dir)
    export_metadata = export_package.metadata
    export_id = export_metadata["export_id"]
    save_export_package(
        export_id=export_id,
        chat_id=message.chat.id,
        export_dir=export_dir,
        export_slug=export_metadata["export_slug"],
        theme=carousel_plan.theme_hint,
        render_mode=render_mode,
    )

    await status.delete()
    sent_messages = await message.answer_media_group(media_group)
    telegram_media_items = []
    for index, sent_message in enumerate(sent_messages, start=1):
        if sent_message.photo:
            telegram_media_items.append(
                {
                    "file_id": sent_message.photo[-1].file_id,
                    "media_type": "photo",
                    "order_index": index,
                }
            )
    if telegram_media_items:
        update_export_metadata(
            export_dir,
            {"telegram_media_items": telegram_media_items},
        )
    actions = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🛰 Prepare Meta Publish", callback_data=f"meta_prepare:{export_id}"),
                InlineKeyboardButton(text="📸 Publish to Instagram", callback_data=f"instagram_publish:{export_id}"),
                InlineKeyboardButton(text="🧵 Publish to Threads", callback_data=f"threads_publish:{export_id}"),
            ]
        ]
    )

    caption_preview = caption if len(caption) <= 1200 else caption[:1200] + "..."
    card_format = data.get("insta_card_format", "auto")
    await message.answer(
        "✅ Карусель готова.\n\n"
        f"Слайдов: {len(slides_content)}\n"
        f"Подача текста: {INSTA_REWRITE_LABELS.get(rewrite_style, 'Коротко и ясно')}\n"
        f"Формат карточек: {INSTA_CARD_FORMAT_LABELS.get(card_format, 'Авто')}\n"
        f"Визуал: {VISUAL_MODE_LABELS.get(visual_decision.resolved_mode, visual_decision.resolved_mode)}"
        f"{' + свой фон' if custom_bg_bytes else ''}\n"
        f"Рендер: {render_mode}\n"
        f"Экспорт: {export_id}\n\n"
        f"Подпись:\n{caption_preview}",
        reply_markup=actions,
    )
    if render_mode != "html":
        await message.answer(browser_binaries_hint())
    await state.clear()


@router.callback_query(F.data.startswith("meta_prepare:"))
async def meta_prepare_publish(callback: types.CallbackQuery):
    await callback.answer()
    export_id = callback.data.split(":", 1)[1]
    export_record = get_export_package(export_id)
    if not export_record:
        await callback.message.answer("⚠️ Export package не найден. Сгенерируйте карусель заново.")
        return

    try:
        public_info = build_public_export_info(export_record["export_dir"])
    except Exception as exc:
        await callback.message.answer(
            "⚠️ Не могу подготовить Meta publish без public hosting.\n\n"
            f"Причина: {exc}\n"
            "Нужно задать `EXPORT_PUBLIC_BASE_URL` и раздавать export-пакеты по публичному URL."
        )
        return

    plan = build_carousel_publish_plan(
        export_dir=export_record["export_dir"],
        public_base_url=public_info.public_base_url,
        credentials=MetaCredentials(
            ig_user_id="<IG_USER_ID>",
            access_token="<ACCESS_TOKEN>",
        ),
    )
    plan_json = json.dumps(
        {
            "public_export": {
                "export_id": public_info.export_id,
                "export_slug": public_info.export_slug,
                "slide_urls": public_info.slide_urls,
                "caption_url": public_info.caption_url,
                "metadata_url": public_info.metadata_url,
            },
            "publish_plan": {
                "child_requests": [
                    upload.request.payload for upload in plan.media_uploads
                ],
                "carousel_request": plan.create_carousel_request.payload,
                "publish_request": plan.publish_request.payload,
                "polling": {
                    "interval_seconds": plan.poll_carousel_plan.interval_seconds,
                    "max_attempts": plan.poll_carousel_plan.max_attempts,
                },
            },
        },
        ensure_ascii=False,
        indent=2,
    )
    job_id = create_meta_publish_job(
        export_id=export_id,
        status="prepared_without_credentials",
        plan_json=plan_json,
    )

    await callback.message.answer(
        "🛰 Meta publish prepared.\n\n"
        f"Export ID: {public_info.export_id}\n"
        f"Job ID: {job_id}\n"
        f"Slides: {len(public_info.slide_urls)}\n"
        f"Public base: {public_info.public_base_url}\n"
        f"First slide URL: {public_info.slide_urls[0]}\n\n"
        "Следующий шаг: подключить Meta account и подставить реальные `IG_USER_ID` + `ACCESS_TOKEN`."
    )


@router.callback_query(F.data.startswith("instagram_publish:"))
async def instagram_publish(callback: types.CallbackQuery):
    await callback.answer()
    export_id = callback.data.split(":", 1)[1]
    export_record = get_export_package(export_id)
    if not export_record:
        await callback.message.answer("⚠️ Export package не найден. Сгенерируйте карусель заново.")
        return

    if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_USER_ID:
        await callback.message.answer(
            "⚠️ Instagram publisher не настроен.\n\n"
            "Нужно задать `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_USER_ID`, "
            "`INSTAGRAM_API_BASE` и media proxy переменные."
        )
        return

    publisher = InstagramPublisher(
        access_token=INSTAGRAM_ACCESS_TOKEN,
        user_id=INSTAGRAM_USER_ID,
        bot=callback.bot,
        api_base=INSTAGRAM_API_BASE,
        media_proxy_base_url=INSTAGRAM_MEDIA_PROXY_BASE_URL,
        media_proxy_bot_alias=INSTAGRAM_MEDIA_PROXY_BOT_ALIAS,
        media_proxy_secret=INSTAGRAM_MEDIA_PROXY_SECRET,
        media_proxy_ttl_seconds=INSTAGRAM_MEDIA_PROXY_TTL_SECONDS,
    )

    await callback.message.answer("📸 Публикую карусель в Instagram...")
    result = await publisher.publish_export(export_dir=export_record["export_dir"])

    if result.success:
        job_id = create_meta_publish_job(
            export_id=export_id,
            status="published_to_instagram",
            plan_json=json.dumps(
                {
                    "ig_user_id": INSTAGRAM_USER_ID,
                    "creation_id": result.creation_id,
                    "published_id": result.published_id,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
        await callback.message.answer(
            "✅ Карусель опубликована в Instagram.\n\n"
            f"Export ID: {export_id}\n"
            f"Job ID: {job_id}\n"
            f"Container ID: {result.creation_id}\n"
            f"Instagram ID: {result.published_id}"
        )
        return

    await callback.message.answer(
        "❌ Не удалось опубликовать карусель в Instagram.\n\n"
        f"Export ID: {export_id}\n"
        f"Ошибка: {result.error_message}"
    )


@router.callback_query(F.data.startswith("threads_publish:"))
async def threads_prepare_publish(callback: types.CallbackQuery):
    await callback.answer()
    export_id = callback.data.split(":", 1)[1]
    export_record = get_export_package(export_id)
    if not export_record:
        await callback.message.answer("⚠️ Export package не найден. Сгенерируйте карусель заново.")
        return

    if not THREADS_ACCESS_TOKEN:
        await callback.message.answer(
            "⚠️ Threads publisher не настроен.\n\n"
            "Нужно задать `THREADS_ACCESS_TOKEN`, при необходимости `THREADS_USER_ID`, "
            "`THREADS_API_BASE` и `EXPORT_PUBLIC_BASE_URL`."
        )
        return

    plan = build_threads_publish_plan(
        export_record["export_dir"],
        public_base_url=EXPORT_PUBLIC_BASE_URL or None,
    )

    plan_json = json.dumps(serialize_threads_publish_plan(plan), ensure_ascii=False, indent=2)
    job_id = create_threads_publish_job(
        export_id=export_id,
        status="prepared_for_threads_publish",
        plan_json=plan_json,
    )

    publisher = ThreadsPublisher(
        access_token=THREADS_ACCESS_TOKEN,
        bot=callback.bot,
        user_id=THREADS_USER_ID,
        api_base=THREADS_API_BASE,
        media_proxy_base_url=THREADS_MEDIA_PROXY_BASE_URL,
        media_proxy_bot_alias=THREADS_MEDIA_PROXY_BOT_ALIAS,
        media_proxy_secret=THREADS_MEDIA_PROXY_SECRET,
        media_proxy_ttl_seconds=THREADS_MEDIA_PROXY_TTL_SECONDS,
    )
    await callback.message.answer("🧵 Публикую карусель в Threads...")
    result = await publisher.publish_export(
        export_dir=export_record["export_dir"],
        public_base_url=EXPORT_PUBLIC_BASE_URL or None,
    )

    if result.success:
        await callback.message.answer(
            "✅ Карусель опубликована в Threads.\n\n"
            f"Export ID: {plan.public_export.export_id}\n"
            f"Job ID: {job_id}\n"
            f"Slides: {len(plan.posts)}\n"
            f"Container ID: {result.creation_id}\n"
            f"Threads ID: {result.published_id}"
        )
        return

    await callback.message.answer(
        "❌ Не удалось опубликовать карусель в Threads.\n\n"
        f"Export ID: {plan.public_export.export_id}\n"
        f"Job ID: {job_id}\n"
        f"Ошибка: {result.error_message}"
    )

# --- 3. Analysis & Slide Count Selection ---

async def process_text_input(message: types.Message, text: str, state: FSMContext, is_fast_mode: bool = False):
    await state.update_data(base_text=text)
    
    # Show typing indicator
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    
    analysis = await analyze_text_and_propose_slides(text)
    rec_slides = analysis.get("recommended_slides", 5)
    plan = analysis.get("slides_plan", [])
    
    # Format plan for user
    plan_text = f"📊 **План карусели** (на основе вашего текста):\n\n"
    for slide in plan:
        plan_text += f"🔹 **Слайд {slide.get('slide_index')}**: {slide.get('title')}\n_{slide.get('summary')}_\n\n"
    
    plan_text += f"💡 Рекомендуемое количество слайдов: **{rec_slides}**.\n"
    plan_text += "Выберите количество, и я **напишу полный текст** для каждого слайда:"
    
    # Add step indicator
    response_text = add_step_indicator(
        plan_text,
        current_step=1
    )
    
    # Buttons 1-8
    buttons = []
    row = []
    prefix = "fast_slides_" if is_fast_mode else "slides_"
    
    for i in range(1, 9):
        label = f"✅ {i}" if i == rec_slides else str(i)
        row.append(InlineKeyboardButton(text=label, callback_data=f"{prefix}{i}"))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
        
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    # No back button on first step
    
    await message.answer(response_text, reply_markup=kb)
    
    if is_fast_mode:
        await state.set_state(CarouselFlow.fast_mode_choosing_slide_count)
    else:
        await state.set_state(CarouselFlow.choosing_slide_count)

@router.callback_query(CarouselFlow.choosing_slide_count, F.data.startswith("slides_"))
async def slides_count_chosen(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    count = int(callback.data.split("_")[1])
    await state.update_data(target_slides_count=count)
    
    # Ask for Rewrite Style with step indicator
    message_text = add_step_indicator(
        f"Стиль текста\n\nВыбрано слайдов: {count}. Теперь выберите стиль текста:",
        current_step=2
    )
    
    buttons = []
    for key, label in REWRITE_STYLES.items():
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"rewrite_{key}")])
        
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    kb = add_back_button(kb, callback_data="back_to_slide_count")
    
    await callback.message.edit_text(message_text, reply_markup=kb)
    await state.set_state(CarouselFlow.choosing_rewrite_style)

@router.callback_query(CarouselFlow.choosing_rewrite_style, F.data.startswith("rewrite_"))
async def rewrite_style_chosen(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    style_key = callback.data.replace("rewrite_", "", 1)
    await state.update_data(rewrite_style=style_key)
    
    await callback.message.edit_text(f"⏳ Генерирую тексты в стиле '{REWRITE_STYLES.get(style_key)}'...")
    
    data = await state.get_data()
    base_text = data["base_text"]
    count = data["target_slides_count"]
    
    slides_content = await generate_final_slides(base_text, count, style_key)
    
    if not slides_content:
        await callback.message.edit_text("😔 Не удалось сгенерировать текст. Попробуйте еще раз.")
        return

    await state.update_data(slides_content=slides_content)
    
    # Show Preview with step indicator
    preview_header = add_step_indicator("Предпросмотр слайдов", current_step=3)
    preview_text = f"{preview_header}\n\n"
    for i, slide in enumerate(slides_content):
        preview_text += f"**Слайд {i+1}:** {slide['title']}\n{slide['body']}\n\n"
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Все отлично, далее", callback_data="preview_ok")],
        [InlineKeyboardButton(text="✏️ Редактировать вручную", callback_data="preview_edit")],
        [InlineKeyboardButton(text="🔄 Перегенерировать", callback_data="preview_regen")]
    ])
    kb = add_back_button(kb, callback_data="back_to_rewrite_style")
    
    # Split text if too long (Telegram limit 4096)
    if len(preview_text) > 4000:
        preview_text = preview_text[:4000] + "..."
        
    await callback.message.edit_text(preview_text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(CarouselFlow.preview_text)

@router.callback_query(CarouselFlow.preview_text, F.data == "preview_regen")
async def preview_regen(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    # Go back to style selection
    buttons = []
    for key, label in REWRITE_STYLES.items():
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"rewrite_{key}")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("Выберите стиль текста заново:", reply_markup=kb)
    await state.set_state(CarouselFlow.choosing_rewrite_style)

@router.callback_query(CarouselFlow.preview_text, F.data == "preview_edit")
async def preview_edit(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    data = await state.get_data()
    slides_content = data.get("slides_content", [])
    
    import json
    # Dump JSON with indent for easier editing
    json_text = json.dumps(slides_content, indent=2, ensure_ascii=False)
    
    await callback.message.answer(
        "Скопируйте JSON ниже, отредактируйте его и отправьте мне в ответ:\n\n"
        f"```json\n{json_text}\n```",
        parse_mode="Markdown"
    )
    await state.set_state(CarouselFlow.editing_text)

@router.message(CarouselFlow.editing_text, F.text)
async def text_edited(message: types.Message, state: FSMContext):
    # Check for cancel command explicitly if global handler isn't catching it due to state filter
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Действие отменено.")
        return

    # Try to parse JSON
    import json
    try:
        # Clean markdown
        text = message.text
        if text.startswith("```json"): text = text[7:]
        if text.startswith("```"): text = text[3:]
        if text.endswith("```"): text = text[:-3]
        
        slides_content = json.loads(text)
        if not isinstance(slides_content, list): raise ValueError
        
        await state.update_data(slides_content=slides_content)
        await message.answer("✅ Текст обновлен! Переходим к визуалу.")
        
        # Proceed to Visual Method Selection
        await ask_visual_method(message, state)
        
    except Exception as e:
        logging.error(f"Error parsing JSON in text_edited: {e}")
        await message.answer("❌ Ошибка формата JSON. Пожалуйста, скопируйте код выше, исправьте и отправьте снова. Или нажмите /cancel.")

@router.callback_query(CarouselFlow.preview_text, F.data == "preview_ok")
async def preview_ok(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    # Ensure we keep the current slides_content (whether edited or original)
    # The state already has 'slides_content', so we just proceed.
    await ask_visual_method(callback.message, state)

async def ask_visual_method(message: types.Message, state: FSMContext):
    message_text = add_step_indicator(
        "Выбор визуала\n\nВыберите готовый шаблон или загрузите свой фон.",
        current_step=4,
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖼 Готовые шаблоны", callback_data="visual_preset")],
        [InlineKeyboardButton(text="📸 Свой фон", callback_data="visual_custom")]
    ])
    kb = add_back_button(kb, callback_data="back_to_preview")
    
    if isinstance(message, types.CallbackQuery): # Handle if called from callback
        await message.edit_text(message_text, reply_markup=kb)
    else:
        await message.answer(message_text, reply_markup=kb)
    await state.set_state(CarouselFlow.choosing_visual_method)

# --- 4. Generation & Rendering ---

# --- 5. Visual Method Selection ---

@router.callback_query(CarouselFlow.choosing_visual_method, F.data == "visual_gen")
async def visual_gen_chosen(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer(
        "AI-генерация фона временно убрана. Доступны готовые шаблоны и свой фон.",
        show_alert=True,
    )
    await ask_visual_method(callback.message, state)

@router.callback_query(CarouselFlow.choosing_visual_method, F.data == "visual_preset")
async def visual_preset_chosen(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    # Show presets
    buttons = []
    for key, preset in PRESETS.items():
        buttons.append([InlineKeyboardButton(text=preset["title"], callback_data=f"preset_{key}")])
        
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    kb = add_back_button(kb, callback_data="back_to_visual_method")
    await callback.message.edit_text(
        "Выберите готовый шаблон. Текст будет сверстан в новом формате, без старой схемы «фон + блок текста».",
        reply_markup=kb,
    )
    await state.set_state(CarouselFlow.choosing_preset)

@router.callback_query(CarouselFlow.choosing_visual_method, F.data == "visual_custom")
async def visual_custom_chosen(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    # Initialize custom backgrounds list
    await state.update_data(custom_backgrounds=[])
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_visual_method")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="custom_bg_cancel")]
    ])
    
    await callback.message.edit_text(
        "📸 Загрузите свои фоновые изображения (до 10 файлов).\n\n"
        "💡 Если загрузите один файл - он будет использован для всех слайдов.\n"
        "💡 Если несколько - будут использоваться в случайном порядке.\n\n"
        "Отправьте фото или файл изображения:",
        reply_markup=kb
    )
    await state.set_state(CarouselFlow.waiting_for_custom_background)

# Handler for custom background uploads (photos and documents)
@router.message(CarouselFlow.waiting_for_custom_background, F.photo | F.document)
async def handle_custom_background_upload(message: types.Message, state: FSMContext, bot):
    data = await state.get_data()
    custom_backgrounds = data.get("custom_backgrounds", [])
    
    # Check limit
    if len(custom_backgrounds) >= 10:
        await message.answer("⚠️ Достигнут лимит в 10 файлов. Нажмите '✅ Готово' для продолжения.")
        return
    
    try:
        # Handle photo or document
        if message.photo:
            file_id = message.photo[-1].file_id  # Get largest photo size
        elif message.document:
            # Check if it's an image
            if not message.document.mime_type or not message.document.mime_type.startswith('image/'):
                await message.answer("⚠️ Пожалуйста, отправьте изображение (фото или файл изображения).")
                return
            file_id = message.document.file_id
        else:
            return
        
        # Download file to BytesIO
        file = await bot.get_file(file_id)
        file_bytes = BytesIO()
        await bot.download_file(file.file_path, file_bytes)
        file_bytes.seek(0)
        
        # Store in state as bytes
        custom_backgrounds.append(file_bytes.getvalue())
        await state.update_data(custom_backgrounds=custom_backgrounds)
        
        count = len(custom_backgrounds)
        
        # Show confirmation buttons
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"✅ Готово ({count} фото)", callback_data="custom_bg_done")],
            [InlineKeyboardButton(text="➕ Добавить еще", callback_data="custom_bg_add_more")] if count < 10 else [],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="custom_bg_cancel")]
        ])
        
        await message.answer(
            f"📸 Загружено изображений: {count}/10\n\n"
            f"{'💡 Один файл будет использован для всех слайдов.' if count == 1 else '💡 Файлы будут использоваться в случайном порядке.'}\n\n"
            "Что дальше?",
            reply_markup=kb
        )
        
    except Exception as e:
        logging.error(f"Error downloading custom background: {e}")
        await message.answer("😔 Ошибка при загрузке файла. Попробуйте другой файл.")

# Handler for "Add more" button
@router.callback_query(CarouselFlow.waiting_for_custom_background, F.data == "custom_bg_add_more")
async def custom_bg_add_more(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("📸 Отправьте еще изображение:")

# Handler for "Done" button
@router.callback_query(CarouselFlow.waiting_for_custom_background, F.data == "custom_bg_done")
async def custom_bg_done(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    data = await state.get_data()
    custom_backgrounds = data.get("custom_backgrounds", [])
    
    if not custom_backgrounds:
        await callback.message.edit_text("⚠️ Вы не загрузили ни одного изображения. Отправьте хотя бы одно.")
        return
    
    # Set bg_type to custom
    await state.update_data(bg_type="custom")
    
    # Proceed to text position selection
    await ask_text_position(callback.message, state)

# Handler for "Cancel" button
@router.callback_query(CarouselFlow.waiting_for_custom_background, F.data == "custom_bg_cancel")
async def custom_bg_cancel(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text("❌ Загрузка отменена.")
    await state.clear()



@router.callback_query(CarouselFlow.choosing_gen_style, F.data.startswith("genstyle_"))
async def gen_style_chosen(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    key = callback.data.replace("genstyle_", "", 1)
    
    if key == "custom":
        await callback.message.edit_text("Напишите промт для генерации фона (на английском лучше, но можно и на русском):")
        await state.set_state(CarouselFlow.entering_custom_prompt)
    else:
        style = BACKGROUND_STYLES.get(key)
        await state.update_data(bg_type="gen", gen_prompt=style["base_prompt"])
        await ask_text_position(callback.message, state)

@router.message(CarouselFlow.entering_custom_prompt, F.text)
async def custom_prompt_entered(message: types.Message, state: FSMContext):
    await state.update_data(bg_type="gen", gen_prompt=message.text)
    await ask_text_position(message, state)

@router.callback_query(CarouselFlow.choosing_preset, F.data.startswith("preset_"))
async def preset_chosen(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    key = callback.data.replace("preset_", "", 1)
    preset = PRESETS.get(key)
    if not preset:
        await callback.message.edit_text("😔 Шаблон не найден. Попробуйте выбрать другой.")
        return

    profile = resolve_preset_visual_profile(key)
    await state.update_data(
        bg_type="preset",
        preset_key=key,
        preset_url=preset["url"],
        preset_profile=profile,
    )
    await callback.message.edit_text(
        f"🎨 Собираю карусель по шаблону «{preset['title']}»..."
    )
    await state.set_state(CarouselFlow.processing)
    await generate_carousel(callback.message, state, user_id=callback.from_user.id)

# --- 7. Text Position & Final Generation ---

async def ask_text_position(message: types.Message, state: FSMContext):
    message_text = add_step_indicator("Позиция текста\n\nГде разместить текст на слайде?", current_step=5)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬆️ Сверху", callback_data="pos_top")],
        [InlineKeyboardButton(text="⏺ По центру", callback_data="pos_center")],
        [InlineKeyboardButton(text="⬇️ Снизу", callback_data="pos_bottom")]
    ])
    
    # Dynamic back button based on bg_type
    data = await state.get_data()
    bg_type = data.get("bg_type")
    
    if bg_type == "gen":
        kb = add_back_button(kb, callback_data="back_to_gen_style")
    elif bg_type == "preset":
        kb = add_back_button(kb, callback_data="back_to_preset")
    elif bg_type == "custom":
        kb = add_back_button(kb, callback_data="back_to_custom_bg")
    else:
        # Fallback to visual method if bg_type not set
        kb = add_back_button(kb, callback_data="back_to_visual_method")
    
    if isinstance(message, types.CallbackQuery):
        await message.edit_text(message_text, reply_markup=kb)
    else:
        await message.answer(message_text, reply_markup=kb)
    await state.set_state(CarouselFlow.choosing_text_position)

# --- 8. Back Navigation Handlers ---

@router.callback_query(F.data == "back_to_slide_count")
async def back_to_slide_count(callback: types.CallbackQuery, state: FSMContext):
    """Go back to slide count selection"""
    await callback.answer()
    
    data = await state.get_data()
    base_text = data.get("base_text", "")
    
    # Re-analyze and show slide count selection
    await process_text_input(callback.message, base_text, state)

@router.callback_query(F.data == "back_to_rewrite_style")
async def back_to_rewrite_style(callback: types.CallbackQuery, state: FSMContext):
    """Go back to rewrite style selection"""
    await callback.answer()
    
    data = await state.get_data()
    count = data.get("target_slides_count", 5)
    selected_style = data.get("rewrite_style")
    
    # Show rewrite style selection with current selection marked
    message_text = add_step_indicator(
        f"Стиль текста\n\nВыбрано слайдов: {count}. Теперь выберите стиль текста:",
        current_step=2
    )
    
    buttons = []
    for key, label in REWRITE_STYLES.items():
        # Mark currently selected style with ✅
        display_label = f"✅ {label}" if key == selected_style else label
        buttons.append([InlineKeyboardButton(text=display_label, callback_data=f"rewrite_{key}")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    kb = add_back_button(kb, callback_data="back_to_slide_count")
    
    await callback.message.edit_text(message_text, reply_markup=kb)
    await state.set_state(CarouselFlow.choosing_rewrite_style)

@router.callback_query(F.data == "back_to_preview")
async def back_to_preview(callback: types.CallbackQuery, state: FSMContext):
    """Go back to preview text screen"""
    await callback.answer()
    
    data = await state.get_data()
    slides_content = data.get("slides_content", [])
    
    # Re-show preview
    preview_header = add_step_indicator("Предпросмотр слайдов", current_step=3)
    preview_text = f"{preview_header}\n\n"
    for i, slide in enumerate(slides_content):
        preview_text += f"**Слайд {i+1}:** {slide['title']}\n{slide['body']}\n\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Все отлично, далее", callback_data="preview_ok")],
        [InlineKeyboardButton(text="✏️ Редактировать вручную", callback_data="preview_edit")],
        [InlineKeyboardButton(text="🔄 Перегенерировать", callback_data="preview_regen")]
    ])
    kb = add_back_button(kb, callback_data="back_to_rewrite_style")
    
    # Split text if too long
    if len(preview_text) > 4000:
        preview_text = preview_text[:4000] + "..."
    
    await callback.message.edit_text(preview_text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(CarouselFlow.preview_text)

@router.callback_query(F.data == "back_to_visual_method")
async def back_to_visual_method(callback: types.CallbackQuery, state: FSMContext):
    """Go back to visual method selection"""
    await callback.answer()
    await ask_visual_method(callback.message, state)

@router.callback_query(F.data == "back_to_gen_style")
async def back_to_gen_style(callback: types.CallbackQuery, state: FSMContext):
    """Go back to gen style selection"""
    await callback.answer()
    
    # Show gen style selection
    buttons = []
    for key, style in BACKGROUND_STYLES.items():
        buttons.append([InlineKeyboardButton(text=style["title"], callback_data=f"genstyle_{key}")])
    
    buttons.append([InlineKeyboardButton(text="✨ Свой промт", callback_data="genstyle_custom")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    kb = add_back_button(kb, callback_data="back_to_visual_method")
    await callback.message.edit_text("Выберите стиль генерации или напишите свой промт:", reply_markup=kb)
    await state.set_state(CarouselFlow.choosing_gen_style)

@router.callback_query(F.data == "back_to_preset")
async def back_to_preset(callback: types.CallbackQuery, state: FSMContext):
    """Go back to preset selection"""
    await callback.answer()
    
    # Show presets
    buttons = []
    for key, preset in PRESETS.items():
        buttons.append([InlineKeyboardButton(text=preset["title"], callback_data=f"preset_{key}")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    kb = add_back_button(kb, callback_data="back_to_visual_method")
    await callback.message.edit_text("Выберите готовый фон:", reply_markup=kb)
    await state.set_state(CarouselFlow.choosing_preset)

@router.callback_query(F.data == "back_to_custom_bg")
async def back_to_custom_bg(callback: types.CallbackQuery, state: FSMContext):
    """Go back to custom background upload"""
    await callback.answer()
    
    # Re-initialize custom backgrounds
    await state.update_data(custom_backgrounds=[])
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_visual_method")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="custom_bg_cancel")]
    ])
    
    await callback.message.edit_text(
        "📸 Загрузите свои фоновые изображения (до 10 файлов).\n\n"
        "💡 Если загрузите один файл - он будет использован для всех слайдов.\n"
        "💡 Если несколько - будут использоваться в случайном порядке.\n\n"
        "Отправьте фото или файл изображения:",
        reply_markup=kb
    )
    await state.set_state(CarouselFlow.waiting_for_custom_background)

# --- 9. Position Selection ---


@router.callback_query(CarouselFlow.choosing_font, F.data.startswith("font_"))
async def font_chosen_std(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    font_key = callback.data.replace("font_", "", 1)
    await state.update_data(font=font_key)
    
    # Proceed to text position
    await ask_text_position(callback.message, state)

@router.callback_query(CarouselFlow.choosing_text_position, F.data.startswith("pos_"))
async def position_chosen(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    pos = callback.data.replace("pos_", "", 1)
    await state.update_data(text_position=pos)
    
    await callback.message.edit_text(" Начинаю сборку карусели! Это займет немного времени...")
    await state.set_state(CarouselFlow.processing)
    
    await generate_carousel(callback.message, state, user_id=callback.from_user.id)

async def generate_carousel(message: types.Message, state: FSMContext, user_id: int = None):
    data = await state.get_data()
    slides_content = data.get("slides_content", [])
    bg_type = data.get("bg_type")
    text_position = data.get("text_position", "center")
    
    # Handle font style (Standard uses 'font', Fast uses 'font_style')
    font_style = data.get("font") or data.get("font_style") or "standard"
    
    # Get user logo
    # Use provided user_id or fallback to message.chat.id (safer than from_user for bot messages)
    target_user_id = user_id if user_id else message.chat.id
    user_logo = get_user_logo(target_user_id)
    
    # Check for custom cover
    has_custom_cover = data.get("has_custom_cover", False)
    cover_bytes = data.get("cover_image_bytes")
    
    logging.info(f"Generating carousel. Slides: {len(slides_content)}, BG: {bg_type}, Cover: {has_custom_cover}, CoverBytes: {len(cover_bytes) if cover_bytes else 0}")

    if bg_type == "preset":
        await _generate_template_carousel(
            message=message,
            state=state,
            slides_content=slides_content,
            user_logo=user_logo,
            preset_key=data.get("preset_key", "lofi"),
            preset_title=PRESETS.get(data.get("preset_key", ""), {}).get("title", "Готовый шаблон"),
        )
        return
    
    media_group = []
    total_slides = len(slides_content)
    
    # Determine background source
    # If preset, we use the same URL for all.
    # If gen, we generate ONE image and use it for all.
    
    common_bg_source = None
    
    if bg_type == "preset":
        common_bg_source = data.get("preset_url")
    elif bg_type == "gen":
        base_prompt = data.get("gen_prompt")
        prompt = f"{base_prompt} --no text"
        await message.edit_text(f"🎨 Генерирую единый фон для всех слайдов...")
        common_bg_source = generate_background(prompt)
        if not common_bg_source:
             await message.edit_text("😔 Ошибка генерации фона.")
             return
    elif bg_type == "custom":
        # Handle both Standard (list) and Fast (single bytes)
        custom_backgrounds = data.get("custom_backgrounds", [])
        custom_bg_bytes = data.get("custom_bg_bytes")
        
        if custom_bg_bytes:
            # Fast mode single custom bg
            common_bg_source = BytesIO(custom_bg_bytes)
        elif custom_backgrounds:
            # Standard mode list
            pass # Handled per slide
        else:
            logging.error("No custom backgrounds found")
            await message.edit_text("😔 Ошибка: не найдены загруженные фоны.")
            return

    for i, slide in enumerate(slides_content):
        await message.edit_text(f"🎨 Рисую слайд {i+1} из {total_slides}...\\nТема: {slide['title']}")
        
        current_bg_source = None
        
        # 1. Check for Custom Cover (First Slide)
        if i == 0 and has_custom_cover and cover_bytes:
            logging.info("Using custom cover for slide 1")
            current_bg_source = BytesIO(cover_bytes)
        
        # 2. If no cover, use standard logic
        if not current_bg_source:
            if bg_type == "custom":
                if data.get("custom_bg_bytes"):
                    # Fast mode: use common source
                    if isinstance(common_bg_source, BytesIO): common_bg_source.seek(0)
                    current_bg_source = common_bg_source
                else:
                    # Standard mode: random/sequential from list
                    import random
                    custom_backgrounds = data.get("custom_backgrounds", [])
                    if custom_backgrounds:
                        bg_bytes = random.choice(custom_backgrounds) if len(custom_backgrounds) > 1 else custom_backgrounds[0]
                        current_bg_source = BytesIO(bg_bytes)
            else:
                # Preset or Gen
                if isinstance(common_bg_source, BytesIO):
                     common_bg_source.seek(0)
                current_bg_source = common_bg_source
            
        if not current_bg_source:
             logging.error(f"Failed to get background for slide {i}")
             continue

        # Render
        image_buffer = render_slide(
            current_bg_source,
            slide["title"],
            slide["body"],
            text_position=text_position,
            font_style=font_style,
            logo_text=user_logo,
            slide_index=i + 1,
            total_slides=total_slides,
        )
        
        input_file = BufferedInputFile(image_buffer.getvalue(), filename=f"slide_{i+1}.png")
        media_group.append(InputMediaPhoto(media=input_file))
        
    if media_group:
        await message.delete()
        await message.answer_media_group(media_group)
        await message.answer("✨ Готово! 🚀")
    else:
        await message.edit_text("😔 Не удалось создать слайды.")
    
    # Clean up state to prevent memory leaks
    await state.clear()


async def _generate_template_carousel(
    message: types.Message,
    state: FSMContext,
    slides_content: list[dict],
    user_logo: str,
    preset_key: str,
    preset_title: str,
):
    if not slides_content:
        await message.edit_text("😔 Не нашел тексты слайдов для сборки.")
        await state.clear()
        return

    profile = resolve_preset_visual_profile(preset_key)
    theme = profile["theme"]
    visual_mode = profile["visual_mode"]
    plan = build_fallback_instagram_plan(slides_content, theme_hint=theme)
    specs = build_instagram_layout_specs(plan, visual_mode=visual_mode)

    media_group = []
    render_mode = "html"
    for spec in specs:
        await message.edit_text(
            f"🎨 Рисую слайд {spec.slide_index} из {spec.total_slides}...\n"
            f"Шаблон: {preset_title}"
        )
        try:
            rendered_bytes = await asyncio.to_thread(
                render_layout_spec_html,
                spec,
                user_logo,
            )
        except Exception as exc:
            logging.warning("Template HTML renderer unavailable, falling back to Pillow: %s", exc)
            render_mode = "pillow-fallback"
            image_buffer = render_layout_spec(
                spec,
                logo_text=user_logo,
                bg_source=None,
            )
            rendered_bytes = image_buffer.getvalue()

        media_group.append(
            InputMediaPhoto(
                media=BufferedInputFile(
                    rendered_bytes,
                    filename=f"template_slide_{spec.slide_index}.png",
                )
            )
        )

    if media_group:
        try:
            await message.delete()
        except Exception:
            pass
        await message.answer_media_group(media_group)
        await message.answer(
            "✨ Готово! 🚀\n\n"
            f"Шаблон: {preset_title}\n"
            f"Визуал: {VISUAL_MODE_LABELS.get(visual_mode, visual_mode)}"
            f" · {profile['label']}"
        )
        if render_mode != "html":
            await message.answer(browser_binaries_hint())
    else:
        await message.edit_text("😔 Не удалось создать слайды.")

    await state.clear()

# --- Fast Mode Handlers ---

@router.message(F.text == "⚡️ Быстрый режим")
async def fast_mode_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "⚡️ Быстрый режим временно убран, чтобы не дублировать основной сценарий.\n\n"
        "Используйте `Создать карусель` или `🚀 Insta Auto`.",
        parse_mode="Markdown",
    )

@router.message(CarouselFlow.fast_mode_waiting_for_text, F.text)
async def fast_handle_text(message: types.Message, state: FSMContext):
    await start_fast_mode_selection(message, message.text, state)

@router.message(CarouselFlow.fast_mode_waiting_for_text, F.voice)
async def fast_handle_voice(message: types.Message, state: FSMContext, bot):
    await message.answer("🎤 Слушаю...")
    file_id = message.voice.file_id
    file = await bot.get_file(file_id)
    destination = f"voice_{file_id}.ogg"
    await bot.download_file(file.file_path, destination)
    text = await transcribe_voice(destination)
    if os.path.exists(destination): os.remove(destination)
    
    if not text:
        await message.answer("😔 Не удалось распознать.")
        return

    await start_fast_mode_selection(message, text, state)

@router.message(CarouselFlow.fast_mode_waiting_for_text, F.forward_from | F.forward_from_chat)
async def fast_handle_forward(message: types.Message, state: FSMContext):
    text = message.text or message.caption or ""
    if not text:
        await message.answer("⚠️ Нет текста.")
        return
    await start_fast_mode_selection(message, text, state)

async def start_fast_mode_selection(message: types.Message, text: str, state: FSMContext):
    # Validate text length
    is_valid, error_msg = validate_text_length(text)
    if not is_valid:
        await message.answer(error_msg)
        await state.clear()
        return
        
    await state.update_data(base_text=text)
    
    # Buttons 1-8
    buttons = []
    row = []
    for i in range(1, 9):
        row.append(InlineKeyboardButton(text=str(i), callback_data=f"fast_slides_{i}"))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row: buttons.append(row)
    
    # Add cancel button
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="fast_cancel")])
    
    await message.answer("🔢 На сколько слайдов разбить текст?", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.set_state(CarouselFlow.fast_mode_choosing_slide_count)

# Modified process_text_input to handle fast mode flag
# (I will need to modify the original function or copy logic)
# To avoid breaking original, I'll create a helper or just duplicate the analysis part for now since it's short.



@router.callback_query(CarouselFlow.fast_mode_choosing_slide_count, F.data.startswith("fast_slides_"))
async def fast_slides_chosen(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    count = int(callback.data.split("_")[2])
    await state.update_data(target_slides_count=count)
    
    # Ask for Rewrite Style
    buttons = []
    for key, label in REWRITE_STYLES.items():
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"fast_rewrite_{key}")])
        
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    # Add back button to slide count (restart selection)
    kb = add_back_button(kb, callback_data="fast_back_to_slide_count")
    
    await callback.message.edit_text("✍️ Выберите стиль текста:", reply_markup=kb)
    await state.set_state(CarouselFlow.fast_mode_choosing_rewrite_style)

@router.callback_query(CarouselFlow.fast_mode_choosing_rewrite_style, F.data.startswith("fast_rewrite_"))
async def fast_rewrite_style_chosen(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    style_key = callback.data.replace("fast_rewrite_", "", 1)
    await state.update_data(rewrite_style=style_key)
    
    await callback.message.edit_text(f"⏳ Генерирую тексты в стиле '{REWRITE_STYLES.get(style_key)}'...")
    
    data = await state.get_data()
    base_text = data["base_text"]
    count = data["target_slides_count"]
    
    slides_content = await generate_final_slides(base_text, count, style_key)
    if not slides_content:
        await callback.message.edit_text("😔 Ошибка генерации текста.")
        return
        
    await state.update_data(slides_content=slides_content)
    
    # Show Preview
    preview_text = "👀 **Предпросмотр:**\n\n"
    for i, slide in enumerate(slides_content):
        preview_text += f"**Слайд {i+1}:** {slide['title']}\n{slide['body']}\n\n"
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Все отлично, далее", callback_data="fast_preview_ok")],
        [InlineKeyboardButton(text="🔄 Перегенерировать", callback_data="fast_preview_regen")]
    ])
    kb = add_back_button(kb, callback_data="fast_back_to_rewrite_style")
    
    if len(preview_text) > 4000:
        preview_text = preview_text[:4000] + "..."
        
    await callback.message.edit_text(preview_text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(CarouselFlow.fast_mode_preview_text)

@router.callback_query(CarouselFlow.fast_mode_preview_text, F.data == "fast_preview_regen")
async def fast_preview_regen(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    # Go back to style selection
    buttons = []
    for key, label in REWRITE_STYLES.items():
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"fast_rewrite_{key}")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    kb = add_back_button(kb, callback_data="fast_back_to_slide_count")
    await callback.message.edit_text("Выберите стиль текста заново:", reply_markup=kb)
    await state.set_state(CarouselFlow.fast_mode_choosing_rewrite_style)

@router.callback_query(CarouselFlow.fast_mode_preview_text, F.data == "fast_preview_ok")
async def fast_preview_ok(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    # Proceed directly to visual method selection
    await ask_visual_method(callback.message, state)

@router.callback_query(CarouselFlow.waiting_for_cover_image, F.data == "upload_cover_no")
async def skip_cover_upload(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(has_custom_cover=False)
    await ask_visual_method(callback.message, state)

@router.callback_query(CarouselFlow.waiting_for_cover_image, F.data == "upload_cover_yes")
async def ask_cover_upload(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text("📸 Отправьте фото для обложки (первого слайда):")
    # Stay in waiting_for_cover_image state, but now waiting for message

@router.message(CarouselFlow.waiting_for_cover_image, F.photo)
async def handle_cover_upload(message: types.Message, state: FSMContext, bot):
    file_id = message.photo[-1].file_id
    file = await bot.get_file(file_id)
    file_bytes = BytesIO()
    await bot.download_file(file.file_path, file_bytes)
    file_bytes.seek(0)
    
    await state.update_data(has_custom_cover=True, cover_image_bytes=file_bytes.getvalue())
    await ask_visual_method(message, state)

async def ask_visual_method(message: types.Message, state: FSMContext):
    # Proceed to visual selection (existing logic)
    buttons = [
        [InlineKeyboardButton(text="🤖 AI Генерация", callback_data="fast_vis_gen")],
        [InlineKeyboardButton(text="🎨 Готовые пресеты", callback_data="fast_vis_preset")],
        [InlineKeyboardButton(text="📤 Свой фон (для всех)", callback_data="fast_vis_custom")]
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    # Add back button to preview
    kb = add_back_button(kb, callback_data="fast_back_to_preview") # This back button should go to the cover question now
    await message.answer("🎨 Как оформим остальные слайды?", reply_markup=kb)
    await state.set_state(CarouselFlow.fast_mode_choosing_visual)

# --- Fast Mode Back Handlers ---

@router.callback_query(F.data == "fast_back_to_slide_count")
async def fast_back_to_slide_count(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    await start_fast_mode_selection(callback.message, data.get("base_text"), state)

@router.callback_query(F.data == "fast_back_to_rewrite_style")
async def fast_back_to_rewrite_style(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    # Show rewrite style selection again
    buttons = []
    for key, label in REWRITE_STYLES.items():
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"fast_rewrite_{key}")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    kb = add_back_button(kb, callback_data="fast_back_to_slide_count")
    await callback.message.edit_text("✍️ Выберите стиль текста:", reply_markup=kb)
    await state.set_state(CarouselFlow.fast_mode_choosing_rewrite_style)

@router.callback_query(F.data == "fast_back_to_preview")
async def fast_back_to_preview(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    slides_content = data.get("slides_content", [])
    
    preview_text = "👀 **Предпросмотр:**\n\n"
    for i, slide in enumerate(slides_content):
        preview_text += f"**Слайд {i+1}:** {slide['title']}\n{slide['body']}\n\n"
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Все отлично, далее", callback_data="fast_preview_ok")],
        [InlineKeyboardButton(text="🔄 Перегенерировать", callback_data="fast_preview_regen")]
    ])
    kb = add_back_button(kb, callback_data="fast_back_to_rewrite_style")
    
    if len(preview_text) > 4000:
        preview_text = preview_text[:4000] + "..."
        
    await callback.message.edit_text(preview_text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(CarouselFlow.fast_mode_preview_text)

@router.callback_query(CarouselFlow.fast_mode_choosing_visual, F.data == "fast_vis_gen")
async def fast_vis_gen(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    buttons = []
    for key, style in BACKGROUND_STYLES.items():
        buttons.append([InlineKeyboardButton(text=style["title"], callback_data=f"fast_gen_{key}")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    kb = add_back_button(kb, callback_data="fast_back_to_visual_method")
    await callback.message.edit_text("Выберите стиль генерации:", reply_markup=kb)

@router.callback_query(CarouselFlow.fast_mode_choosing_visual, F.data.startswith("fast_gen_"))
async def fast_gen_chosen(callback: types.CallbackQuery, state: FSMContext):
    key = callback.data.replace("fast_gen_", "", 1)
    style = BACKGROUND_STYLES.get(key)
    await state.update_data(bg_type="gen", gen_prompt=style["base_prompt"])
    await ask_font(callback.message, state)

@router.callback_query(CarouselFlow.fast_mode_choosing_visual, F.data == "fast_vis_preset")
async def fast_vis_preset(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    buttons = []
    for key, preset in PRESETS.items():
        buttons.append([InlineKeyboardButton(text=preset["title"], callback_data=f"fast_preset_{key}")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    kb = add_back_button(kb, callback_data="fast_back_to_visual_method")
    await callback.message.edit_text("Выберите пресет:", reply_markup=kb)

@router.callback_query(CarouselFlow.fast_mode_choosing_visual, F.data.startswith("fast_preset_"))
async def fast_preset_chosen(callback: types.CallbackQuery, state: FSMContext):
    key = callback.data.replace("fast_preset_", "", 1)
    preset = PRESETS.get(key)
    await state.update_data(bg_type="preset", preset_url=preset["url"])
    await ask_font(callback.message, state)

@router.callback_query(CarouselFlow.fast_mode_choosing_visual, F.data == "fast_vis_custom")
async def fast_vis_custom(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    kb = add_back_button(kb, callback_data="fast_back_to_visual_method")
    await callback.message.edit_text("📸 Отправьте фоновое изображение (одно для всех слайдов):", reply_markup=kb)
    await state.set_state(CarouselFlow.fast_mode_waiting_for_custom_bg)

@router.callback_query(F.data == "fast_back_to_visual_method")
async def fast_back_to_visual_method(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await fast_preview_ok(callback, state)

# Add cancel handler for Fast Mode
@router.callback_query(F.data == "fast_cancel")
async def fast_cancel(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("❌ Отменено. Используйте /start для нового запуска.")

@router.message(CarouselFlow.fast_mode_waiting_for_custom_bg, F.photo | F.document)
async def fast_custom_upload(message: types.Message, state: FSMContext, bot):
    # Handle upload with validation
    try:
        if message.photo:
            file_id = message.photo[-1].file_id
            file_size = message.photo[-1].file_size
        elif message.document:
            file_id = message.document.file_id
            file_size = message.document.file_size
            # Validate file type
            if not message.document.mime_type or not message.document.mime_type.startswith('image/'):
                await message.answer("⚠️ Пожалуйста, отправьте изображение.")
                return
        else:
            return
        
        # Validate file size
        is_valid, error_msg = validate_file_size(file_size)
        if not is_valid:
            await message.answer(error_msg)
            return
        
        file = await bot.get_file(file_id)
        file_bytes = BytesIO()
        await bot.download_file(file.file_path, file_bytes)
        file_bytes.seek(0)
        
        await state.update_data(bg_type="custom", custom_bg_bytes=file_bytes.getvalue())
        await ask_font(message, state)
    except Exception as e:
        logging.error(f"Error in fast_custom_upload: {e}")
        await message.answer("😔 Ошибка загрузки файла.")

async def ask_font(message: types.Message, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Стандартный", callback_data="font_standard")],
        [InlineKeyboardButton(text="Prosto One", callback_data="font_prosto"), InlineKeyboardButton(text="Rampart One", callback_data="font_rampart")],
        [InlineKeyboardButton(text="Dela Gothic", callback_data="font_dela")]
    ])
    
    # Add back button depending on previous step (visual method)
    # But since we don't track exact previous visual sub-step easily here without passing it,
    # we can just go back to visual method selection (root) or try to infer.
    # Going back to visual method selection is safe.
    kb = add_back_button(kb, callback_data="fast_back_to_visual_method")

    if isinstance(message, types.CallbackQuery):
        await message.edit_text("🔤 Выберите шрифт:", reply_markup=kb)
    else:
        await message.answer("🔤 Выберите шрифт:", reply_markup=kb)
    await state.set_state(CarouselFlow.fast_mode_choosing_font)

@router.callback_query(CarouselFlow.fast_mode_choosing_font, F.data.startswith("font_"))
async def font_chosen(callback: types.CallbackQuery, state: FSMContext):
    font = callback.data.replace("font_", "", 1)
    await state.update_data(font_style=font)
    
    # Ask about Cover (Moved here as requested)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да, загрузить обложку", callback_data="cover_yes")],
        [InlineKeyboardButton(text="Нет, оставить как есть", callback_data="cover_no")]
    ])
    await callback.message.edit_text("🖼 Хотите загрузить отдельное фото для первого слайда (обложки)?", reply_markup=kb)
    await state.set_state(CarouselFlow.fast_mode_waiting_for_cover)

@router.callback_query(CarouselFlow.fast_mode_waiting_for_cover, F.data == "cover_no")
async def cover_no(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    # Proceed to text position
    await ask_text_position(callback.message, state)

@router.callback_query(CarouselFlow.fast_mode_waiting_for_cover, F.data == "cover_yes")
async def cover_yes(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text("📸 Отправьте фото для обложки:")

@router.message(CarouselFlow.fast_mode_waiting_for_cover, F.photo | F.document)
async def cover_upload(message: types.Message, state: FSMContext, bot):
    try:
        if message.photo: file_id = message.photo[-1].file_id
        elif message.document: file_id = message.document.file_id
        else: return
        
        file = await bot.get_file(file_id)
        file_bytes = BytesIO()
        await bot.download_file(file.file_path, file_bytes)
        file_bytes.seek(0)
        
        await state.update_data(has_custom_cover=True, cover_image_bytes=file_bytes.getvalue())
        # Proceed to text position
        await ask_text_position(message, state)
    except Exception as e:
        logging.error(f"Error in cover_upload: {e}")
        await message.answer("😔 Ошибка загрузки. Попробуйте снова или нажмите 'Нет'.")

async def generate_fast_carousel(message: types.Message, state: FSMContext):
    data = await state.get_data()
    slides = data["slides_content"]
    bg_type = data["bg_type"]
    font_style = data.get("font_style", "standard")
    user_logo = get_user_logo(message.chat.id)
    
    # Prepare common background
    common_bg = None
    if bg_type == "gen":
        prompt = data["gen_prompt"]
        common_bg = generate_background(prompt + " --no text") # Generate ONCE
    elif bg_type == "preset":
        common_bg = data["preset_url"]
    elif bg_type == "custom":
        common_bg = BytesIO(data["custom_bg_bytes"])
        
    cover_bg = data.get("cover_image_bytes") # Bytes (Fixed key)
    
    media_group = []
    total_slides = len(slides)

    for i, slide in enumerate(slides):
        # Determine BG for this slide
        current_bg = common_bg
        
        if i == 0 and cover_bg:
            current_bg = BytesIO(cover_bg)
            
        # If common_bg is BytesIO, we need to seek(0) or copy it for multiple uses?
        # Image.open() might read it.
        # Better to read bytes once and create new BytesIO for each render if needed, 
        # OR render_slide handles it. render_slide seeks(0).
        # But if we use the SAME BytesIO object 5 times, it might be fine if we seek(0) inside render_slide.
        # render_slide does seek(0).
        
        img_buffer = render_slide(
            current_bg,
            slide['title'],
            slide['body'],
            "center",
            font_style,
            logo_text=user_logo,
            slide_index=i + 1,
            total_slides=total_slides,
        )
        media_group.append(InputMediaPhoto(media=BufferedInputFile(img_buffer.read(), filename=f"slide_{i}.png")))
        
    await message.answer_media_group(media_group)
    await state.clear()
