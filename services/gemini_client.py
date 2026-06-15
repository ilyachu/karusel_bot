import json
import logging
import os
import re
from copy import deepcopy

from openai import AsyncOpenAI
from services.cover_renderer import normalize_cover_plan

from config import (
    NEURALDEEP_API_KEY,
    NEURALDEEP_BASE_URL,
    NEURALDEEP_MODEL,
    OPENAI_API_KEY,
    OPENAI_FALLBACK_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
)

if NEURALDEEP_API_KEY:
    llm_client = AsyncOpenAI(
        api_key=NEURALDEEP_API_KEY,
        base_url=NEURALDEEP_BASE_URL,
    )
    DEFAULT_MODEL = NEURALDEEP_MODEL
else:
    llm_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    DEFAULT_MODEL = OPENAI_FALLBACK_MODEL

openrouter_fallback_client = (
    AsyncOpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)
    if OPENROUTER_API_KEY
    else None
)
openai_fallback_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

LAYOUT_STYLE_PROMPTS = {
    "magazine": "magazine: аналитика, эссе, разборы. Playfair Display или DM Serif Display, воздух, editorial rhythm, спокойная и умная композиция.",
    "terminal": "terminal: технические обзоры, benchmarks, AI-новости. JetBrains Mono или IBM Plex Mono, CLI-эстетика, панели, прогресс, статусные строки.",
    "poster": "poster: манифесты, анонсы, сильные утверждения. Unbounded или Space Grotesk, огромная типографика, цветовые блоки, жесткая композиция.",
    "carddeck": "carddeck: списки, чеклисты, обучение. Inter или Manrope, стек карточек, glassmorphism, chips, dot progress.",
}


async def generate_final_slides(base_text: str, target_slides_count: int, rewrite_style: str) -> list[dict]:
    style_instructions = {
        "exact": "Максимально сохраняй исходные формулировки, только аккуратно разбей на слайды.",
        "marketing": "Пиши живо, но без рекламной шелухи и банальных клише.",
        "educational": "Пиши ясно, структурно и по делу.",
        "concise": "Пиши коротко, без воды и повторов.",
    }
    instruction = style_instructions.get(rewrite_style, "Пиши ясно и по делу.")

    prompt = f"""Собери карусель из {target_slides_count} слайдов. Верни JSON:
{{"slides": [{{"title": "Короткий заголовок", "body": "Текст до 260 символов"}}]}}
Русский. Каждый слайд — одна мысль. {instruction}

Текст:
{base_text}"""

    try:
        result = await _router_json_request(prompt)
        slides = result.get("slides", [])
        if isinstance(slides, list):
            return await _normalize_slides_language(base_text, slides)
    except Exception as e:
        logging.error(f"Error in generate_final_slides: {e}")

    try:
        result = await _openai_json_request(prompt)
        slides = result.get("slides", [])
        if isinstance(slides, list):
            return await _normalize_slides_language(base_text, slides)
    except Exception as fallback_error:
        logging.error(f"OpenAI fallback failed in generate_final_slides: {fallback_error}")

    return []


async def generate_instagram_caption(base_text: str, slides_content: list[dict]) -> str:
    slides_summary = "\n".join(
        f"- {slide.get('title', '').strip()}: {slide.get('body', '').strip()}"
        for slide in slides_content
    )

    prompt = f"""Напиши Instagram caption на русском: хук + 2-4 абзаца + мягкий CTA + 4-6 хэштегов. Без воды.

Текст: {base_text}
Слайды: {slides_summary}"""

    try:
        text_result = await _router_text_request(prompt)
        return await _normalize_caption_language(base_text, text_result)
    except Exception as e:
        logging.error(f"Error in generate_instagram_caption: {e}")

    try:
        text_result = await _openai_text_request(prompt)
        return await _normalize_caption_language(base_text, text_result)
    except Exception as fallback_error:
        logging.error(f"OpenAI fallback failed in generate_instagram_caption: {fallback_error}")
        return "Сохрани этот пост, чтобы вернуться к нему позже.\n\n#instagram #carousel #ai #opensource"


async def generate_threads_summary(base_text: str, slides_content: list[dict], caption: str = "") -> str:
    slides_summary = "\n".join(
        f"- {slide.get('title', '').strip()}: {slide.get('body', '').strip()}"
        for slide in slides_content
    )

    prompt = f"""Напиши короткий Threads-пост (1-2 предложения, до 220 символов) о сути. Без хэштегов, emoji, CTA.

Текст: {base_text}
Слайды: {slides_summary}"""

    try:
        text_result = await _router_text_request(prompt)
        return _sanitize_threads_summary(await _normalize_caption_language(base_text, text_result))
    except Exception as e:
        logging.error(f"Error in generate_threads_summary: {e}")

    try:
        text_result = await _openai_text_request(prompt)
        return _sanitize_threads_summary(await _normalize_caption_language(base_text, text_result))
    except Exception as fallback_error:
        logging.error(f"OpenAI fallback failed in generate_threads_summary: {fallback_error}")
        return ""


async def generate_cover_plan(base_text: str, style: str, format_key: str) -> dict:
    style_profiles = {
        "orange_poster": "Крупный техно-плакат. Headline 3-5 слов, можно RU/EN смесь. Энергия, дерзость, минимум текста.",
        "acid_poster": "Кислотный плакат. Headline 2-4 слова, яркая формулировка. Панк-энергия, контраст.",
        "retro_polaroid": "Film burn атмосфера. Headline 2-4 слова, атмосферно и коротко. Не полароид — это киноплёнка.",
        "blue_type": "Огромная синяя типографика. Headline 2-5 слов, вопрос или тезис. Минимум элементов, максимум шрифта.",
        "grid_steps": "Сетка и шаги. Headline 3-6 слов, action-формулировка. Хорошо ложится лестницей.",
        "blur_field": "Плакат поверх размытия. Headline 3-5 слов, эмоциональная фраза. Без кликбейта, с силой.",
        "red_manifesto": "Красный манифест. Headline 2-5 слов, резкий тезис. Как плакат поверх газеты.",
        "paper_brief": "Тезис на листе. Headline 3-6 слов, уверенно и без рекламного тона. Деловой стиль.",
        "quiet_editorial": "Спокойный журнал. Headline 3-6 слов, умно и сдержанно. Serif шрифт, пространство.",
        "chalk_notes": "Ручная заметка. Headline 2-4 слова, наивная формулировка. Как маркер на листе.",
    }
    profile = style_profiles.get(style, style_profiles["orange_poster"])

    format_notes = {
        "wide": "Широкий формат 16:9 — headline может быть длиннее, 3-6 слов.",
        "post": "Вертикаль 4:5 — headline 2-5 слов, компактно.",
        "story": "Story 9:16 — headline 2-4 слова, максимально крупно.",
    }
    fmt_note = format_notes.get(format_key, "")

    prompt = f"""JSON-план обложки. Стиль: {profile}. Формат: {fmt_note}
{{"headline": "2-6 слов", "subtitle": "5-12 слов или пусто", "eyebrow_left": "РАЗБОР · № 01", "eyebrow_right": "POSTER · TODAY", "footer_left": "ДЛЯ ЧИТАТЕЛЕЙ", "symbol": "arrow|asterisk|slash|dot", "cta_text": "призыв или пусто"}}
Русский. Одна главная мысль. Не возвращай footer_right.

Текст: {base_text}"""

    try:
        result = await _router_json_request(prompt)
    except Exception as e:
        logging.error(f"Error in generate_cover_plan: {e}")
        result = {}

    if not result:
        try:
            result = await _openai_json_request(prompt)
        except Exception as fallback_error:
            logging.error(f"OpenAI fallback failed in generate_cover_plan: {fallback_error}")
            result = {}

    plan = normalize_cover_plan(result, base_text, style, format_key).to_dict()
    plan["html_body"] = await generate_cover_html_body(base_text, style, format_key, plan)
    return plan


async def generate_instagram_carousel_plan(
    base_text: str,
    target_slides_count: int,
    rewrite_style: str = "concise",
    *,
    layout_style_override: str = "auto",
    theme_hint_override: str = "auto",
    color_palette: str = "auto",
    visual_mode: str = "auto",
) -> dict:
    style_instructions = {
        "exact": "бережно сохраняй исходные мысли и формулировки, только упакуй их в слайды",
        "marketing": "сделай подачу сильнее и убедительнее, но без рекламной шелухи и клише",
        "educational": "объясняй структурно, как понятный мини-разбор по шагам",
        "concise": "пиши коротко, ясно и без воды",
    }
    style_instruction = style_instructions.get(rewrite_style, style_instructions["concise"])

    settings_block = _build_user_settings_block(
        layout_style_override=layout_style_override,
        theme_hint_override=theme_hint_override,
        color_palette=color_palette,
        visual_mode=visual_mode,
    )
    prompt = f"""Собери JSON-план карусели из {target_slides_count} слайдов:
{{"carousel": {{"goal": "instagram_carousel", "audience": "...", "tone": "clear_confident|bold_creator|premium_editorial", "theme_hint": "business_dark|minimal_light|creator_bold|editorial_premium|memory_archive|founder_brief|growth_black|research_mono", "cta": "save_and_follow|comment_and_dm|share_and_follow", "layout_style": "magazine|terminal|poster|carddeck"}}, "slides": [{{"index": 1, "role": "hook|context|point|proof|example|checklist|cta", "title": "...", "body": "...", "emphasis": ["..."], "supporting_cards": [{{"title": "1-2 слова", "body": "до 6 слов"}}], "density": "low|medium|high", "theme_hint": "...", "archetype": "hero_center|split_story|checklist_stack|stat_panel|quote_poster|timeline_steps|comparison_grid|soft_cta"}}]}}

Правила: hook первый, cta последний. {style_instruction}. supporting_cards — 0-3 микро-тезиса, не копировать body.
Выбери layout_style строго по контексту:
- magazine: аналитика, эссе, разборы, спокойный умный тон
- terminal: технические обзоры, benchmarks, AI-новости, инструменты
- poster: манифесты, анонсы, резкие тезисы, сильные заявления
- carddeck: списки, чеклисты, образовательный контент, how-to
Не выбирай случайно: layout_style должен помогать именно этому материалу.
Для каждого слайда выбери archetype:
- hero_center: мощный центральный hook
- split_story: верх/низ или левый/правый narrative split
- checklist_stack: список или ступени
- stat_panel: цифра + факт + подпорка
- quote_poster: короткий тезис с большим воздухом
- timeline_steps: 2-4 последовательных шага
- comparison_grid: сравнение или пример/антипример
- soft_cta: спокойный финальный CTA
{settings_block}

Текст:
{base_text}"""

    try:
        result = await _router_json_request(prompt)
        result = await _normalize_carousel_plan_language(base_text, result)
        return await attach_slide_html_to_plan(
            base_text,
            result,
            layout_style_override=layout_style_override,
            theme_hint_override=theme_hint_override,
            color_palette=color_palette,
            visual_mode=visual_mode,
        )
    except Exception as e:
        logging.error(f"Error in generate_instagram_carousel_plan: {e}")

    try:
        result = await _openai_json_request(prompt)
        result = await _normalize_carousel_plan_language(base_text, result)
        return await attach_slide_html_to_plan(
            base_text,
            result,
            layout_style_override=layout_style_override,
            theme_hint_override=theme_hint_override,
            color_palette=color_palette,
            visual_mode=visual_mode,
        )
    except Exception as fallback_error:
        logging.error(f"OpenAI fallback failed in generate_instagram_carousel_plan: {fallback_error}")
        return {}


async def attach_slide_html_to_plan(
    base_text: str,
    plan: dict,
    *,
    layout_style_override: str = "auto",
    theme_hint_override: str = "auto",
    color_palette: str = "auto",
    visual_mode: str = "auto",
) -> dict:
    if not isinstance(plan, dict) or not isinstance(plan.get("slides"), list):
        return plan

    slides = plan.get("slides", [])
    if not slides:
        return plan

    layout_style = str(plan.get("carousel", {}).get("layout_style", "magazine"))
    style_brief = LAYOUT_STYLE_PROMPTS.get(layout_style, LAYOUT_STYLE_PROMPTS["magazine"])
    texture_preset = _texture_preset_for_theme(str(plan.get("carousel", {}).get("theme_hint", "business_dark")))
    payload = {
        "carousel": deepcopy(plan.get("carousel", {})),
        "slides": [
            {
                "index": slide.get("index", idx + 1),
                "role": slide.get("role", "point"),
                "title": slide.get("title", ""),
                "body": slide.get("body", ""),
                "emphasis": slide.get("emphasis", []),
                "supporting_cards": slide.get("supporting_cards", []),
                "archetype": slide.get("archetype", ""),
            }
            for idx, slide in enumerate(slides)
        ],
    }
    settings_block = _build_user_settings_block(
        layout_style_override=layout_style_override,
        theme_hint_override=theme_hint_override,
        color_palette=color_palette,
        visual_mode=visual_mode,
    )
    prompt = f"""Ты — арт-директор Instagram-каруселей.
Верни JSON:
{{"slides":[{{"index":1,"html_body":"<section style='...'>...</section>"}}]}}

Нужно придумать уникальный body-level HTML для каждого слайда.
Стиль: {style_brief}
Texture layer: {texture_preset}

Требования:
- Только body-level HTML, без <html>, <head>, <body>
- Каждый слайд визуально отличается композицией, а не только цветом
- Размер холста 1080x1350, используй width:100%; height:100%
- Допустимы inline styles, <style>, gradients, shadows, flex, grid
- Не используй script, canvas, svg data uri, внешние картинки
- Можно использовать Google Fonts по family name: Inter, Playfair Display, JetBrains Mono, Unbounded, Manrope, Space Grotesk, DM Serif Display
- Текст бери только из данных слайда, не выдумывай новые факты
- Уважай archetype каждого слайда, это не подсказка, а композиционное требование
- Не складывай весь текст в верхние 25% холста
- Строй композицию по вертикали: верхний маркер/лейбл, главный блок в центре или средней зоне, поддержка/CTA внизу
- Оставляй заметный воздух: минимум 18% пустого пространства на слайде
- Длина строк должна быть читабельной: не делай длинные абзацы на всю ширину
- Для role=hook и role=cta главный текст размещай в центре или нижней трети
- Для role=checklist, role=proof, role=example используй 2-3 зоны, карточки или split-layout, чтобы взгляд шёл сверху вниз
{settings_block}

Исходный текст:
{base_text}

План карусели:
{json.dumps(payload, ensure_ascii=False)}"""

    mapping = await _request_slide_html_mapping(prompt)
    if not mapping:
        logging.warning(
            "Slide HTML generation returned no usable html_body values. layout_style=%s slides=%s",
            layout_style,
            len(slides),
        )
        return plan

    enriched = deepcopy(plan)
    for slide in enriched.get("slides", []):
        index = int(slide.get("index", 0) or 0)
        html_body = _clean_html_body(mapping.get(index, ""))
        if html_body:
            slide["html_body"] = html_body
    return enriched


async def generate_cover_html_body(base_text: str, style: str, format_key: str, cover_plan: dict) -> str:
    style_brief = {
        "orange_poster": "агрессивный плакат, крупный headline, теплый контраст",
        "acid_poster": "кислотный постер, панк-энергия, резкий ритм",
        "retro_polaroid": "film burn, архивная атмосфера, кинопленка",
        "blue_type": "огромная синяя типографика, минимум декора",
        "grid_steps": "сетка, шаги, модульная композиция",
        "blur_field": "типографика поверх размытого движения",
        "red_manifesto": "редакционный манифест, газетный контраст",
        "paper_brief": "деловой лист, заметки, underline и stamps",
        "quiet_editorial": "тихий журнал, serif, много воздуха",
        "chalk_notes": "маркерные заметки, ручной наклон, бумага",
    }.get(style, "типографическая обложка")
    texture_preset = _texture_preset_for_cover_style(style)
    prompt = f"""Верни JSON:
{{"html_body":"<section style='...'>...</section>"}}

Ты делаешь уникальную HTML-обложку.
Стиль: {style_brief}
Формат: {format_key}
Texture layer: {texture_preset}

Требования:
- Только body-level HTML, без <html>, <head>, <body>
- Холст должен занимать всю площадь через width:100%; height:100%
- Допустимы inline styles, <style>, gradients, texture-like blocks
- Не используй script и внешние изображения
- Если нужен шрифт, используй family name: Inter, Playfair Display, JetBrains Mono, Unbounded, Manrope, Space Grotesk, DM Serif Display
- Используй только эти поля: headline, subtitle, eyebrow_left, eyebrow_right, footer_left, cta_text
- Не ставь весь текст в самый верх; композиция должна держаться на 2-3 вертикальных зонах
- Главный headline должен сидеть в центре или чуть ниже центра, а служебные элементы поддерживать ритм сверху и снизу
- Держи сильную иерархию: один доминирующий элемент, один supporting block, один нижний anchor
- Оставляй воздух и безопасные поля, чтобы обложка читалась как viral cover, а не как плотный текстовый лист

Исходный текст:
{base_text}

План обложки:
{json.dumps(cover_plan, ensure_ascii=False)}"""

    try:
        result = await _router_json_request(prompt)
        raw_html = str(result.get("html_body", ""))
        cleaned = _clean_html_body(raw_html)
        if not cleaned:
            logging.warning(
                "Cover HTML generation returned unusable html_body via router. style=%s format=%s keys=%s preview=%s",
                style,
                format_key,
                sorted(result.keys()) if isinstance(result, dict) else [],
                _preview_text(raw_html),
            )
        return cleaned
    except Exception as e:
        logging.error(f"Error in generate_cover_html_body: {e}")

    try:
        result = await _openai_json_request(prompt)
        raw_html = str(result.get("html_body", ""))
        cleaned = _clean_html_body(raw_html)
        if not cleaned:
            logging.warning(
                "Cover HTML generation returned unusable html_body via fallback. style=%s format=%s keys=%s preview=%s",
                style,
                format_key,
                sorted(result.keys()) if isinstance(result, dict) else [],
                _preview_text(raw_html),
            )
        return cleaned
    except Exception as fallback_error:
        logging.error(f"OpenAI fallback failed in generate_cover_html_body: {fallback_error}")
        return ""


async def _router_json_request(prompt: str) -> dict:
    response = await llm_client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": "Return valid JSON only. No markdown fences, no explanation."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        max_tokens=4096,
    )
    content = response.choices[0].message.content or "{}"
    return json.loads(content)


async def _router_text_request(prompt: str) -> str:
    response = await llm_client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": "Write concise Russian editorial/social copy without marketing fluff."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=4096,
    )
    return (response.choices[0].message.content or "").strip()


async def _openai_json_request(prompt: str) -> dict:
    clients: list[tuple[str, AsyncOpenAI, str]] = []
    if openrouter_fallback_client:
        clients.append(("openrouter", openrouter_fallback_client, OPENROUTER_MODEL))
    if openai_fallback_client:
        clients.append(("openai", openai_fallback_client, OPENAI_FALLBACK_MODEL))
    if not clients:
        raise RuntimeError("No fallback LLM client configured.")

    last_error: Exception | None = None
    for name, client, model in clients:
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Return valid JSON only. No markdown fences, no explanation."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=4096,
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception as exc:
            logging.error("JSON fallback failed via %s: %s", name, exc)
            last_error = exc
    raise RuntimeError(f"All JSON fallback clients failed: {last_error}")


async def _openai_text_request(prompt: str) -> str:
    clients: list[tuple[str, AsyncOpenAI, str]] = []
    if openrouter_fallback_client:
        clients.append(("openrouter", openrouter_fallback_client, OPENROUTER_MODEL))
    if openai_fallback_client:
        clients.append(("openai", openai_fallback_client, OPENAI_FALLBACK_MODEL))
    if not clients:
        raise RuntimeError("No fallback LLM client configured.")

    last_error: Exception | None = None
    for name, client, model in clients:
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Write concise Russian editorial/social copy without marketing fluff."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=4096,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as exc:
            logging.error("Text fallback failed via %s: %s", name, exc)
            last_error = exc
    raise RuntimeError(f"All text fallback clients failed: {last_error}")


def _is_russian_source(text: str) -> bool:
    cyr = len(re.findall(r"[А-Яа-яЁё]", text))
    lat = len(re.findall(r"[A-Za-z]", text))
    return cyr > lat


def _looks_english_heavy(text: str) -> bool:
    cyr = len(re.findall(r"[А-Яа-яЁё]", text))
    lat = len(re.findall(r"[A-Za-z]", text))
    return lat > cyr * 2 and lat > 20


async def _normalize_slides_language(source_text: str, slides: list[dict]) -> list[dict]:
    if not _is_russian_source(source_text):
        return slides
    return [
        {
            **slide,
            "title": _normalize_russian_phrase(str(slide.get("title", ""))),
            "body": _normalize_russian_phrase(str(slide.get("body", ""))),
        }
        for slide in slides
    ]


async def _normalize_carousel_plan_language(source_text: str, plan: dict) -> dict:
    if not _is_russian_source(source_text):
        return plan
    carousel = plan.get("carousel", {})
    if "audience" in carousel:
        carousel["audience"] = _normalize_russian_phrase(str(carousel.get("audience", "")))
    plan["slides"] = [
        {
            **slide,
            "title": _normalize_russian_phrase(str(slide.get("title", ""))),
            "body": _normalize_russian_phrase(str(slide.get("body", ""))),
            "emphasis": [
                _normalize_russian_phrase(str(item)) for item in slide.get("emphasis", [])
            ],
            "supporting_cards": [
                {
                    "title": _normalize_russian_phrase(str(card.get("title", card.get("label", "")))),
                    "body": _normalize_russian_phrase(str(card.get("body", card.get("value", "")))),
                }
                for card in slide.get("supporting_cards", [])
                if isinstance(card, dict)
            ][:3],
        }
        for slide in plan.get("slides", [])
    ]
    return plan


async def _normalize_caption_language(source_text: str, caption: str) -> str:
    if not _is_russian_source(source_text):
        return caption
    return _normalize_russian_phrase(caption)


async def _request_slide_html_mapping(prompt: str) -> dict[int, str]:
    for requester in (_router_json_request, _openai_json_request):
        requester_name = requester.__name__
        try:
            result = await requester(prompt)
            mapping: dict[int, str] = {}
            slides = result.get("slides", []) if isinstance(result, dict) else []
            logging.info(
                "Slide HTML raw response via %s: slides=%s",
                requester_name,
                len(slides) if isinstance(slides, list) else "invalid",
            )
            for item in slides:
                try:
                    index = int(item.get("index", 0) or 0)
                except (TypeError, ValueError):
                    index = 0
                if index <= 0:
                    logging.warning("Slide HTML item without valid index via %s: %s", requester_name, item)
                    continue
                raw_html = str(item.get("html_body", ""))
                html_body = _clean_html_body(raw_html)
                if html_body:
                    mapping[index] = html_body
                else:
                    logging.warning(
                        "Slide HTML unusable via %s for index=%s preview=%s",
                        requester_name,
                        index,
                        _preview_text(raw_html),
                    )
            if mapping:
                return mapping
            logging.warning(
                "Slide HTML response via %s produced zero usable entries. raw_keys=%s",
                requester_name,
                sorted(result.keys()) if isinstance(result, dict) else [],
            )
        except Exception as exc:
            logging.error("Slide HTML generation failed via %s: %s", requester_name, exc)
    return {}


def _clean_html_body(value: str) -> str:
    html_body = (value or "").strip()
    if html_body.startswith("```"):
        html_body = re.sub(r"^```[a-zA-Z]*\n?", "", html_body)
        html_body = re.sub(r"\n?```$", "", html_body).strip()
    if "<script" in html_body.lower():
        return ""
    if not re.search(r"<[a-zA-Z][^>]*>", html_body):
        return ""
    return html_body


def _preview_text(value: str, limit: int = 180) -> str:
    normalized = re.sub(r"\s+", " ", (value or "")).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit] + "..."


def _build_user_settings_block(
    *,
    layout_style_override: str,
    theme_hint_override: str,
    color_palette: str,
    visual_mode: str,
) -> str:
    notes: list[str] = []
    if layout_style_override and layout_style_override != "auto":
        notes.append(f"- Пользователь зафиксировал layout_style = {layout_style_override}. Не меняй его.")
    if theme_hint_override and theme_hint_override != "auto":
        notes.append(f"- Пользователь зафиксировал theme_hint = {theme_hint_override}. Соблюдай эту палитру и настроение.")
    if color_palette and color_palette != "auto":
        notes.append(f"- Пользователь выбрал цветовой режим = {color_palette}. Не уходи в случайную палитру.")
    if visual_mode and visual_mode != "auto":
        notes.append(f"- Пользователь выбрал visual_mode = {visual_mode}. Подчини композицию этому режиму.")
    if not notes:
        return "- Пользовательские визуальные настройки не зафиксированы. Можешь выбирать сам."
    return "\n".join(notes)


def _texture_preset_for_theme(theme_hint: str) -> str:
    presets = {
        "growth_black": "midnight_noise_scanlines",
        "business_dark": "blueprint_grid_noise",
        "minimal_light": "soft_paper_grain",
        "founder_brief": "clean_paper_folds",
        "memory_archive": "editorial_film_grain",
        "creator_bold": "vibrant_halftone_glow",
        "editorial_premium": "premium_canvas_dust",
        "research_mono": "mono_terminal_scanlines",
    }
    return presets.get(theme_hint, "soft_paper_grain")


def _texture_preset_for_cover_style(style: str) -> str:
    presets = {
        "orange_poster": "poster_paper_noise",
        "acid_poster": "acid_halftone",
        "retro_polaroid": "film_dust_burn",
        "blue_type": "clean_ink_paper",
        "grid_steps": "blueprint_grid",
        "blur_field": "motion_blur_bloom",
        "red_manifesto": "newsprint_rough",
        "paper_brief": "office_paper_fold",
        "quiet_editorial": "editorial_grain",
        "chalk_notes": "marker_paper_texture",
    }
    return presets.get(style, "editorial_grain")


def _sanitize_threads_summary(text: str) -> str:
    text = re.sub(r"#\w+", "", text or "")
    text = re.sub(r"[*_`>#]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(
        r"\b(?:сохрани|листай|подпишись|подписывайся|share|follow|save)\b.*$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" ,.;:-")
    if len(text) <= 220:
        return text
    clipped = text[:219].rstrip()
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return clipped.rstrip(" ,.;:-") + "…"


def _normalize_russian_phrase(text: str) -> str:
    replacements = {
        "AI-ассистент": "ИИ-ассистент",
        "AI ассистент": "ИИ-ассистент",
        "AI assistant": "ИИ-ассистент",
        "link in bio": "",
        "Link in bio": "",
        "ссылка в описании профиля": "",
        "ссылка в профиле": "",
        "Ссылка в профиле": "",
        "check the link in bio": "",
        "open source": "опенсорс",
        "Open source": "Опенсорс",
        "open-source": "опенсорс",
        "Open-source": "Опенсорс",
    }
    normalized = text
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    normalized = re.sub(r"\bAI\b", "ИИ", normalized)
    normalized = re.sub(r"\s{2,}", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = re.sub(r"\s+([.,!?])", r"\1", normalized)
    return normalized.strip(" \n-")
