import asyncio
import json
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, BufferedInputFile
from aiogram.enums import ChatAction

from utils.states import CarouselFlow, TestRenderFlow

from utils.validation import validate_text_length, validate_file_size
import logging
import os
from io import BytesIO
from dataclasses import asdict, dataclass
from config import (
    EXPORT_PUBLIC_BASE_URL,
    INSTAGRAM_ACCESS_TOKEN,
    INSTAGRAM_API_BASE,
    INSTAGRAM_MEDIA_PROXY_BASE_URL,
    INSTAGRAM_MEDIA_PROXY_BOT_ALIAS,
    INSTAGRAM_MEDIA_PROXY_SECRET,
    INSTAGRAM_MEDIA_PROXY_TTL_SECONDS,
    INSTAGRAM_USER_ID,
    ADMIN_ID,
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
    attach_slide_html_to_plan,
    generate_final_slides,
    generate_instagram_carousel_plan,
    generate_instagram_caption,
)
from services.export_hosting import build_public_export_info
from services.instagram_package import build_instagram_export, update_export_metadata
from services.layout_engine import (
    LAYOUT_STYLE_LABELS,
    VISUAL_MODE_LABELS,
    apply_theme_selection_policy,
    apply_theme_override,
    build_fallback_instagram_plan,
    build_instagram_layout_specs,
    CarouselPlan,
    enforce_default_cta_slide,
    parse_carousel_plan,
    resolve_visual_mode,
    SlidePlanEntry,
)
from services.background_registry import (
    load_background_preset_buffer,
    load_background_preset_data_url,
    pick_background_preset,
)
from services.html_renderer import render_layout_spec_html
from services.cover_renderer import image_bytes_to_data_url
from services.experimental_carousel_renderer import (
    STYLE_PRESETS,
    render_experimental_carousel,
)
from services.instagram_publisher import InstagramPublisher
from services.meta_publish import MetaCredentials, build_carousel_publish_plan, load_export_package
from services.threads_publish import build_threads_publish_plan, serialize_threads_publish_plan
from services.threads_publisher import ThreadsPublisher
from services.openai_speech import transcribe_voice
from services.image_renderer import render_layout_spec
from handlers.common import (
    INSTA_REWRITE_LABELS,
    resolve_target_slide_count,
    show_insta_auto_setup,
)

router = Router()


def _resolve_user_logo_for_message(message: types.Message) -> str:
    user_id = message.from_user.id if message.from_user else message.chat.id
    return get_user_logo(user_id)


def _build_pipeline_status(step: int, total_steps: int, title: str, detail: str = "") -> str:
    lines = [
        "⏳ Генерация карусели",
        "",
        f"Шаг {step}/{total_steps}: {title}",
    ]
    if detail:
        lines.append(detail)
    return "\n".join(lines)

# --- 1. Input Handling ---

# Move generic text handler to the bottom or restrict it to default state
@router.message(F.text & ~F.text.in_({"Помощь", "Создать карусель", "🚀 Insta Auto", "🖼 Обложка", "/start", "/help", "/cancel"}), StateFilter(None))
async def handle_text_input(message: types.Message, state: FSMContext):
    # Validate text length
    is_valid, error_msg = validate_text_length(message.text)
    if not is_valid:
        await message.answer(error_msg)
        return
    await run_insta_auto_pipeline(message, message.text, state)

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
        await message.answer(f"📝 Распознанный текст:\n\n{text}", reply_markup=kb)
        await state.set_state(CarouselFlow.waiting_for_text_confirmation)
    except Exception as e:
        logging.error(f"Voice processing failed: {e}")
        await message.answer("😔 Не удалось обработать голосовое сообщение.")
    finally:
        if os.path.exists(destination):
            os.remove(destination)

@router.message((F.forward_from | F.forward_from_chat), StateFilter(None))
async def handle_forward(message: types.Message, state: FSMContext):
    text = message.text or message.caption or ""
    if not text:
        await message.answer("⚠️ В этом сообщении нет текста.")
        return
    await run_insta_auto_pipeline(message, text, state)

# --- 2. Voice Confirmation Flow ---

@router.callback_query(CarouselFlow.waiting_for_text_confirmation, F.data == "voice_confirm")
async def voice_confirm(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    text = data.get("draft_text", "")
    await callback.message.answer("✅ Принято. Собираю карусель...")
    await run_insta_auto_pipeline(callback.message, text, state)

@router.callback_query(CarouselFlow.waiting_for_text_confirmation, F.data == "voice_edit")
async def voice_edit(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("✍️ Отправьте мне исправленный текст.")

@router.message(CarouselFlow.waiting_for_text_confirmation, F.text)
async def voice_edit_text(message: types.Message, state: FSMContext):
    await message.answer("✅ Текст обновлен. Собираю карусель...")
    await run_insta_auto_pipeline(message, message.text, state)


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
        mime_type = message.document.mime_type
    else:
        photo = message.photo[-1]
        file_id = photo.file_id
        file_size = photo.file_size or 0
        mime_type = "image/jpeg"

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
        insta_custom_bg_mime_type=mime_type,
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
    data = await state.get_data()
    target_slides = resolve_target_slide_count(text, data.get("insta_slide_count", "auto"))
    custom_bg_selected = bool(data.get("insta_custom_bg_bytes"))
    status = await message.answer(
        _build_pipeline_status(
            1,
            5,
            "Собираю структуру",
            f"Планирую {target_slides} слайдов" + (" со своим фоном." if custom_bg_selected else "."),
        )
    )
    await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_PHOTO)
    rewrite_style = data.get("insta_rewrite_style", "concise")

    await status.edit_text(
        _build_pipeline_status(
            2,
            5,
            "Генерирую тексты",
            "Собираю план карусели и раскладываю материал по слайдам.",
        )
    )
    raw_plan = await generate_instagram_carousel_plan(
        text,
        target_slides,
        rewrite_style,
        layout_style_override=data.get("insta_layout_style", "auto"),
        theme_hint_override=data.get("insta_theme_override", "auto"),
        color_palette=data.get("insta_color_palette", "auto"),
        visual_mode=data.get("insta_visual_mode", "auto"),
    )
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

    layout_style = data.get("insta_layout_style", carousel_plan.layout_style)
    if not layout_style or layout_style == "auto":
        # AI уже выбрал стиль в generate_instagram_carousel_plan — используем его
        layout_style = carousel_plan.layout_style
    logging.info(f"Layout style: {layout_style} (from state: {data.get('insta_layout_style')}, from plan: {carousel_plan.layout_style})")
    if layout_style and layout_style != "auto":
        from dataclasses import replace
        carousel_plan = replace(carousel_plan, layout_style=layout_style)
    visual_decision = resolve_visual_mode(carousel_plan, visual_mode)
    refreshed_raw_plan = await attach_slide_html_to_plan(
        text,
        {"carousel": asdict(carousel_plan), "slides": [asdict(slide) for slide in carousel_plan.slides]},
        layout_style_override=layout_style,
        theme_hint_override=carousel_plan.theme_hint,
        color_palette=data.get("insta_color_palette", "auto"),
        visual_mode=visual_decision.resolved_mode,
    )
    refreshed_plan = parse_carousel_plan(refreshed_raw_plan)
    from dataclasses import replace
    carousel_plan = replace(
        carousel_plan,
        slides=refreshed_plan.slides,
        layout_style=layout_style,
    )

    await status.edit_text(
        _build_pipeline_status(
            3,
            5,
            "Генерирую подпись",
            "Подготавливаю caption для публикации.",
        )
    )
    caption = await generate_instagram_caption(text, slides_content)
    threads_summary = ""
    user_logo = _resolve_user_logo_for_message(message)
    layout_specs = build_instagram_layout_specs(carousel_plan, visual_mode=visual_mode, layout_style=layout_style)
    custom_bg_bytes = data.get("insta_custom_bg_bytes")
    custom_bg_mime_type = data.get("insta_custom_bg_mime_type", "image/jpeg")
    custom_background_data_url = image_bytes_to_data_url(custom_bg_bytes, custom_bg_mime_type) if custom_bg_bytes else ""
    logging.info(f"Custom background: bytes={len(custom_bg_bytes) if custom_bg_bytes else 0}, mime={custom_bg_mime_type}, data_url_len={len(custom_background_data_url)}")

    await status.edit_text(
        _build_pipeline_status(
            4,
            5,
            "Рендерю слайды",
            "Собираю финальные изображения 1080×1350.",
        )
    )
    rendered_buffers: list[BytesIO] = []
    media_group = []
    render_mode = "html"
    fallback_reason = ""
    preset_background_ids: list[str] = []
    for layout_spec in layout_specs:
        preset = None if custom_bg_bytes else pick_background_preset(
            layout_style=layout_spec.layout_style,
            theme_hint=layout_spec.theme,
            slide_role=layout_spec.role,
            archetype=getattr(layout_spec, "archetype", ""),
        )
        preset_background_data_url = load_background_preset_data_url(preset.preset_id) if preset else ""
        preset_background_buffer = load_background_preset_buffer(preset.preset_id) if preset else None
        if preset:
            preset_background_ids.append(preset.preset_id)
        if custom_bg_bytes:
            logging.info(f"Rendering slide {layout_spec.slide_index} with custom background")
            try:
                render_mode = "html-custom-bg"
                rendered_bytes = await asyncio.to_thread(
                    render_layout_spec_html,
                    layout_spec,
                    user_logo,
                    custom_background_data_url,
                    "strong",
                    allow_ai_html=False,
                )
            except Exception as exc:
                logging.warning("HTML renderer unavailable for custom background, falling back to Pillow: %s", exc)
                render_mode = "pillow-custom-bg"
                fallback_reason = str(exc)
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
                    preset_background_data_url,
                    "medium",
                )
            except Exception as exc:
                logging.warning("HTML renderer unavailable, falling back to Pillow: %s", exc)
                render_mode = "pillow-fallback"
                fallback_reason = str(exc)
                image_buffer = render_layout_spec(
                    layout_spec,
                    logo_text=user_logo,
                    bg_source=preset_background_buffer,
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
            "preset_background_ids": preset_background_ids,
            "threads_summary": threads_summary,
            "fallback_reason": fallback_reason,
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

    await status.edit_text(
        _build_pipeline_status(
            5,
            5,
            "Готовлю выдачу",
            "Сохраняю экспорт и отправляю карусель в чат.",
        )
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
    if custom_background_data_url:
        update_export_metadata(
            export_dir,
            {"custom_background_data_url": custom_background_data_url},
        )
    action_rows = []
    if message.from_user and message.from_user.id == ADMIN_ID:
        action_rows.append(
            [
                InlineKeyboardButton(text="📸 Опубликовать в Instagram", callback_data=f"instagram_publish:{export_id}"),
                InlineKeyboardButton(text="🧵 Опубликовать в Threads", callback_data=f"threads_publish:{export_id}"),
            ]
        )
        action_rows.append(
            [InlineKeyboardButton(text="🛰 Advanced Meta plan", callback_data=f"meta_prepare:{export_id}")]
        )
    actions = InlineKeyboardMarkup(inline_keyboard=action_rows) if action_rows else None
    unique_presets = list(dict.fromkeys(preset_background_ids))
    if custom_bg_bytes:
        background_label = "свой загруженный"
    elif unique_presets:
        background_label = "авто-пресеты бота"
    else:
        background_label = "без отдельного фонового изображения"

    caption_preview = caption if len(caption) <= 1200 else caption[:1200] + "..."
    await message.answer(
        "✅ Карусель готова.\n\n"
        f"Слайдов: {len(slides_content)}\n"
        f"Подача текста: {INSTA_REWRITE_LABELS.get(rewrite_style, 'Коротко и ясно')}\n"
        f"Стиль: {LAYOUT_STYLE_LABELS.get(layout_style, layout_style)}\n"
        f"Визуал: {VISUAL_MODE_LABELS.get(visual_decision.resolved_mode, visual_decision.resolved_mode)}\n"
        f"Фон: {background_label}\n"
        f"Рендер: {render_mode}\n"
        f"Экспорт: {export_id}\n\n"
        f"Подпись:\n{caption_preview}",
        reply_markup=actions,
    )
    if render_mode != "html" and not custom_bg_bytes:
        human_reason = "HTML-рендер недоступен в текущем контейнере."
        if "playwright" in fallback_reason.lower() or "chromium" in fallback_reason.lower():
            human_reason = "Chromium/Playwright недоступен в контейнере."
        elif "html_body" in fallback_reason.lower():
            human_reason = "На сервере оказались несовместимые версии renderer и layout-модели."
        await message.answer(f"⚠️ Рендер в упрощённом формате.\nПричина: {human_reason}")
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


# ---------------------------------------------------------------------------
# Experimental carousel renderer (separate test path)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ExperimentalExportPackage:
    pngs: list[bytes]
    export_id: str
    export_dir: str


def _rebuild_carousel_plan(plan_dict: dict) -> CarouselPlan:
    """Rebuild a ``CarouselPlan`` from a dict (e.g. from metadata)."""
    slides_data = plan_dict.get("slides", []) or []
    slides = [SlidePlanEntry(**slide) for slide in slides_data]
    plan_kwargs = {key: value for key, value in plan_dict.items() if key != "slides"}
    plan_kwargs["slides"] = slides
    return CarouselPlan(**plan_kwargs)


def _build_experimental_export_package(
    export_record: dict,
    style: "StylePreset",
) -> _ExperimentalExportPackage:
    """Build a new export package by re-rendering the saved plan through
    the experimental deterministic renderer in the chosen style.

    Pure / sync / side-effect-on-disk. Caller is expected to wrap in
    ``asyncio.to_thread(...)`` from an async handler.
    """

    package = load_export_package(export_record["export_dir"])
    metadata = package.metadata

    plan = _rebuild_carousel_plan(metadata.get("carousel_plan") or {})
    layout_specs = build_instagram_layout_specs(
        plan,
        visual_mode=plan.theme_hint,
        layout_style=plan.layout_style,
    )

    chat_id = int(export_record["chat_id"])
    user_id = chat_id
    try:
        logo_text = get_user_logo(user_id) or "chu ai"
    except Exception:
        logo_text = "chu ai"

    custom_bg_data_url = (metadata.get("custom_background_data_url") or "").strip()
    preset_data_url = ""
    # Preset background data URLs are not persisted in metadata in v1;
    # pass an empty string so the experimental renderer falls back to the
    # styled surface. Custom background is the variable we want to A/B test.

    pngs = render_experimental_carousel(
        layout_specs,
        logo_text=logo_text,
        custom_background_data_url=custom_bg_data_url,
        preset_background_data_url=preset_data_url,
        style=style,
    )

    source_text = metadata.get("source_text", "") or "carousel"
    caption_text = package.caption or ""
    png_buffers = [BytesIO(png) for png in pngs]
    # Append the style id to the slug so admins can tell experimental
    # exports apart on disk.
    slug_source = (source_text[:60] if source_text else "carousel") + f"-{style.id}"
    new_export_dir = build_instagram_export(
        png_buffers,
        caption_text,
        slug_source,
        chat_id,
        extra_metadata={
            "render_mode": f"experimental-datatalks-{style.id}",
            "parent_export_id": export_record["export_id"],
            "style_id": style.id,
            "style_label": style.label,
            "carousel_plan": asdict(plan),
            "layout_specs": [spec.to_dict() for spec in layout_specs],
        },
    )
    new_package = load_export_package(new_export_dir)
    new_metadata = new_package.metadata
    new_export_id = new_metadata["export_id"]
    save_export_package(
        export_id=new_export_id,
        chat_id=chat_id,
        export_dir=new_export_dir,
        export_slug=new_metadata["export_slug"],
        theme=plan.theme_hint,
        render_mode=f"experimental-datatalks-{style.id}",
    )
    return _ExperimentalExportPackage(
        pngs=pngs,
        export_id=new_export_id,
        export_dir=new_export_dir,
    )


@router.callback_query(F.data.startswith("carousel_exp_render:"))
async def carousel_experimental_render(callback: types.CallbackQuery):
    await callback.answer()
    if not (callback.from_user and callback.from_user.id == ADMIN_ID):
        await callback.message.answer("⚠️ Тестовый рендер доступен только админу.")
        return

    # Callback format: carousel_exp_render:<export_id>[:<style_id>]
    # Older 2-segment form falls back to dark_teal for cached buttons.
    parts = callback.data.split(":", 2)
    export_id = parts[1]
    style_id = parts[2] if len(parts) >= 3 else "dark_teal"

    from services.experimental_carousel_renderer import STYLE_PRESETS

    style = STYLE_PRESETS.get(style_id)
    if not style:
        await callback.message.answer(f"⚠️ Неизвестный стиль: {style_id}.")
        return

    export_record = get_export_package(export_id)
    if not export_record:
        await callback.message.answer(
            "⚠️ Export package не найден. Сгенерируйте карусель заново."
        )
        return

    status = await callback.message.answer(f"🧪 {style.label} — рендерю…")
    try:
        package = await asyncio.to_thread(
            _build_experimental_export_package,
            export_record,
            style,
        )
    except Exception as exc:
        logging.exception("Experimental render failed for export %s", export_id)
        await status.edit_text(f"⚠️ {style.label} не удался: {exc}")
        return

    media_group = [
        InputMediaPhoto(
            media=BufferedInputFile(
                png,
                filename=f"experimental_slide_{index+1:02d}.png",
            )
        )
        for index, png in enumerate(package.pngs)
    ]
    if not media_group:
        await status.edit_text("⚠️ Нечего рендерить: пустой набор слайдов.")
        return
    await callback.message.answer_media_group(media_group)
    await callback.message.answer(
        f"🧪 {style.label}. Сравни с обычным и с другими пресетами.\n\n"
        f"Export: {package.export_id}"
    )
    await status.edit_text(f"✅ {style.label} готов.")


# ---------------------------------------------------------------------------
# Test-render entry point (admin-only mini-FSM)
# ---------------------------------------------------------------------------


_TEST_RENDER_BUTTON_ROW = [
    [
        InlineKeyboardButton(text="🧪 Dark+Teal", callback_data="test_render_style:dark_teal"),
        InlineKeyboardButton(text="🧪 Paper+Orange", callback_data="test_render_style:paper_orange"),
    ],
    [
        InlineKeyboardButton(text="🧪 White+Coral", callback_data="test_render_style:white_coral")
    ],
]


async def _generate_test_render_plan(text: str) -> tuple[list, "CarouselPlan"]:
    """Run the LLM plan pipeline without rendering.

    Returns a tuple of ``(layout_specs, carousel_plan)``. Raises on
    unrecoverable plan failure.
    """

    target_slides = resolve_target_slide_count(text, "auto")
    rewrite_style = "concise"
    raw_plan = await generate_instagram_carousel_plan(
        text,
        target_slides,
        rewrite_style,
        layout_style_override="auto",
        theme_hint_override="auto",
        color_palette="auto",
        visual_mode="auto",
    )
    if raw_plan:
        carousel_plan = parse_carousel_plan(raw_plan)
    else:
        slides_content = await generate_final_slides(text, target_slides, rewrite_style)
        if not slides_content:
            raise RuntimeError("LLM вернул пустой план и fallback тоже не сработал.")
        carousel_plan = build_fallback_instagram_plan(slides_content)

    carousel_plan = enforce_default_cta_slide(carousel_plan, visual_mode="auto")
    carousel_plan, _ = apply_theme_selection_policy(carousel_plan, text)

    layout_specs = build_instagram_layout_specs(
        carousel_plan,
        visual_mode=carousel_plan.theme_hint,
        layout_style=carousel_plan.layout_style,
    )
    return layout_specs, carousel_plan


async def cmd_test_render(message: types.Message, state: FSMContext):
    """Entry point for the test-render mini-FSM.

    Triggered by the '🧪 Тестовый рендер' main-menu button or the
    /test_render command. Restricted to ``ADMIN_ID`` by the caller.
    """

    if not (message.from_user and message.from_user.id == ADMIN_ID):
        await message.answer("⚠️ Тестовый рендер доступен только админу.")
        return

    await state.clear()
    await state.set_state(TestRenderFlow.waiting_for_text)
    await message.answer(
        "🧪 Тестовый рендер. Пришли текст для карусели (или голосовое сообщение).\n"
        "Я сгенерирую план и покажу превью 3 стилей.\n\n"
        "Чтобы выйти, нажми /start."
    )


@router.message(TestRenderFlow.waiting_for_text, F.text)
async def test_render_text(message: types.Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.answer("🧪 Пришли непустой текст.")
        return
    if text.startswith("/"):
        # Allow the user to escape the FSM with /start.
        if text == "/start":
            await state.clear()
        return

    is_valid, error_msg = validate_text_length(text)
    if not is_valid:
        await message.answer(error_msg)
        return

    status = await message.answer("🧪 Готовлю план…")
    try:
        layout_specs, carousel_plan = await _generate_test_render_plan(text)
    except Exception as exc:
        logging.exception("Test render plan generation failed")
        await status.edit_text(f"⚠️ Не удалось сгенерировать план: {exc}")
        return

    if not layout_specs:
        await status.edit_text("⚠️ Пустой план — попробуй другой текст.")
        return

    await state.update_data(
        test_render_text=text,
        layout_specs=[spec.to_dict() for spec in layout_specs],
        carousel_plan=asdict(carousel_plan),
    )
    await state.set_state(TestRenderFlow.waiting_for_style)
    await status.edit_text(
        f"🧪 План готов ({len(layout_specs)} слайдов). Выбери стиль:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=_TEST_RENDER_BUTTON_ROW),
    )


@router.message(TestRenderFlow.waiting_for_text, F.voice)
async def test_render_voice(message: types.Message, state: FSMContext, bot):
    status = await message.answer("🧪 Расшифровываю голос…")
    try:
        text = await transcribe_voice(bot, message)
    except Exception as exc:
        logging.exception("Voice transcription failed for test render")
        await status.edit_text(f"⚠️ Не удалось распознать голос: {exc}")
        return
    if not text:
        await status.edit_text("⚠️ Пустая расшифровка. Пришли текст.")
        return

    is_valid, error_msg = validate_text_length(text)
    if not is_valid:
        await status.edit_text(error_msg)
        return

    try:
        layout_specs, carousel_plan = await _generate_test_render_plan(text)
    except Exception as exc:
        logging.exception("Test render plan generation failed after voice")
        await status.edit_text(f"⚠️ Не удалось сгенерировать план: {exc}")
        return

    if not layout_specs:
        await status.edit_text("⚠️ Пустой план — попробуй другой текст.")
        return

    await state.update_data(
        test_render_text=text,
        layout_specs=[spec.to_dict() for spec in layout_specs],
        carousel_plan=asdict(carousel_plan),
    )
    await state.set_state(TestRenderFlow.waiting_for_style)
    await status.edit_text(
        f"🧪 План готов ({len(layout_specs)} слайдов, из голоса). Выбери стиль:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=_TEST_RENDER_BUTTON_ROW),
    )


@router.callback_query(TestRenderFlow.waiting_for_style, F.data.startswith("test_render_style:"))
async def test_render_style_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    style_id = callback.data.split(":", 1)[1]
    style = STYLE_PRESETS.get(style_id)
    if not style:
        await callback.message.answer(f"⚠️ Неизвестный стиль: {style_id}.")
        return

    data = await state.get_data()
    layout_specs_dicts = data.get("layout_specs") or []
    if not layout_specs_dicts:
        await callback.message.answer("🧪 Сначала пришли текст.")
        await state.set_state(TestRenderFlow.waiting_for_text)
        return

    # Reconstruct LayoutSpec objects.
    layout_specs = []
    for spec_dict in layout_specs_dicts:
        try:
            layout_specs.append(LayoutSpec(**spec_dict))
        except Exception as exc:
            logging.exception("Failed to reconstruct LayoutSpec")
            await callback.message.answer(f"⚠️ Ошибка состояния: {exc}. Пришли текст заново.")
            await state.set_state(TestRenderFlow.waiting_for_text)
            return

    status = await callback.message.answer(f"🧪 {style.label} — рендерю…")
    try:
        pngs = await asyncio.to_thread(
            render_experimental_carousel,
            layout_specs,
            "chu ai",
            "",
            "",
            style,
        )
    except Exception as exc:
        logging.exception("Test render failed for style %s", style_id)
        await status.edit_text(f"⚠️ {style.label} не удался: {exc}")
        return

    if not pngs:
        await status.edit_text("⚠️ Нечего рендерить.")
        return

    media_group = [
        InputMediaPhoto(
            media=BufferedInputFile(
                png,
                filename=f"test_slide_{index+1:02d}.png",
            )
        )
        for index, png in enumerate(pngs)
    ]
    await callback.message.answer_media_group(media_group)
    await callback.message.answer(
        f"🧪 {style.label}. Тестовый рендер. Прогоняй тот же текст через другие стили.",
    )
    # Re-show the style picker so the admin can keep iterating.
    await status.edit_text(
        f"✅ {style.label} готов. Выбери другой стиль или пришли новый текст.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=_TEST_RENDER_BUTTON_ROW),
    )

