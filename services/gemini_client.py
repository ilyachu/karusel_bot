import json
import logging
import os
import re

from openai import AsyncOpenAI

from config import (
    OPENAI_API_KEY,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
)

router_client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY or OPENAI_API_KEY,
    base_url=OPENROUTER_BASE_URL,
)
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
OPENAI_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")


async def analyze_text_and_propose_slides(text: str) -> dict:
    prompt = f"""
    Ты — редактор каруселей для Instagram и Telegram.

    Проанализируй текст и верни только JSON:
    {{
      "recommended_slides": int,
      "slides_plan": [
        {{ "slide_index": 1, "title": "Заголовок", "summary": "Короткая суть слайда" }}
      ]
    }}

    Требования:
    1. Язык: русский.
    2. Количество слайдов: 4-7, если текст не слишком короткий.
    3. Первый слайд — сильный хук, но без кликбейта.
    4. Не используй общие фразы вроде "откройте мир возможностей".
    5. Не перегружай техническими деталями, если они не главные.

    Исходный текст:
    {text}
    """

    try:
        result = await _router_json_request(prompt)
        if "recommended_slides" in result and "slides_plan" in result:
            return await _normalize_analysis_language(text, result)
    except Exception as e:
        logging.error(f"Error in analyze_text_and_propose_slides: {e}")

    try:
        result = await _openai_json_request(prompt)
        if "recommended_slides" in result and "slides_plan" in result:
            return await _normalize_analysis_language(text, result)
    except Exception as fallback_error:
        logging.error(f"OpenAI fallback failed in analyze_text_and_propose_slides: {fallback_error}")

    return {
        "recommended_slides": 4,
        "slides_plan": [
            {"slide_index": 1, "title": "Ошибка анализа", "summary": "Не удалось проанализировать текст."}
        ],
    }


async def generate_final_slides(base_text: str, target_slides_count: int, rewrite_style: str) -> list[dict]:
    style_instructions = {
        "exact": "Максимально сохраняй исходные формулировки, только аккуратно разбей на слайды.",
        "marketing": "Пиши живо, но без рекламной шелухи и банальных клише.",
        "educational": "Пиши ясно, структурно и по делу.",
        "concise": "Пиши коротко, без воды и повторов.",
    }
    instruction = style_instructions.get(rewrite_style, "Пиши ясно и по делу.")

    prompt = f"""Ты — редактор слайдов.

Собери карусель из {target_slides_count} слайдов и верни только JSON-объект:
{{
  "slides": [
    {{ "title": "Заголовок", "body": "Текст слайда" }}
  ]
}}

Требования:
1. Язык: русский.
2. Каждый слайд должен нести отдельную мысль.
3. Заголовки короткие, без кликбейта.
4. Body не длиннее 260 символов.
5. Не использовать пустые маркетинговые формулировки.
6. Не злоупотреблять лишней технической детализацией.
7. Не писать "подпишись", "поделись" и подобные CTA внутри обычных слайдов.
8. Стиль: {instruction}

Исходный текст:
{base_text}
"""

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

    prompt = f"""Ты — редактор Instagram-подписей.

Напиши caption на русском:
1. Короткий хук.
2. 2-4 коротких абзаца по сути.
3. Один мягкий CTA в конце.
4. Без воды и без штампов.
5. 4-6 релевантных хэштегов в конце.

Исходный текст:
{base_text}

Слайды:
{slides_summary}
"""

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


async def generate_instagram_carousel_plan(base_text: str, target_slides_count: int) -> dict:
    prompt = f"""Ты — контент-стратег Instagram-каруселей.

Собери JSON-план карусели из {target_slides_count} слайдов и верни только JSON:
{{
  "carousel": {{
    "goal": "instagram_carousel",
    "audience": "кто читатель",
    "tone": "clear_confident | bold_creator | premium_editorial",
    "theme_hint": "business_dark | minimal_light | creator_bold | editorial_premium | memory_archive | founder_brief | growth_black | research_mono",
    "cta": "save_and_follow | comment_and_dm | share_and_follow"
  }},
  "slides": [
    {{
      "index": 1,
      "role": "hook | context | point | proof | example | checklist | cta",
      "title": "короткий заголовок",
      "body": "текст слайда",
      "emphasis": ["ключевой акцент"],
      "density": "low | medium | high",
      "theme_hint": "business_dark | minimal_light | creator_bold | editorial_premium | memory_archive | founder_brief | growth_black | research_mono"
    }}
  ]
}}

Требования:
1. Первый слайд — hook, последний — cta.
2. Не использовать банальные marketing-фразы.
3. Упрощать лишнюю техническую информацию, если она не несёт главную мысль.
4. Если это новость/инструмент, делай акцент на сути, а не на hype.
5. Не добавляй кнопки "поделиться/подписаться" внутрь текста слайда.
6. Выбирай `theme_hint` осознанно.

Исходный текст:
{base_text}
"""

    try:
        result = await _router_json_request(prompt)
        return await _normalize_carousel_plan_language(base_text, result)
    except Exception as e:
        logging.error(f"Error in generate_instagram_carousel_plan: {e}")

    try:
        result = await _openai_json_request(prompt)
        return await _normalize_carousel_plan_language(base_text, result)
    except Exception as fallback_error:
        logging.error(f"OpenAI fallback failed in generate_instagram_carousel_plan: {fallback_error}")
        return {}


async def _router_json_request(prompt: str) -> dict:
    response = await router_client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[
            {"role": "system", "content": "Return valid JSON only. No markdown fences, no explanation."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    return json.loads(content)


async def _router_text_request(prompt: str) -> str:
    response = await router_client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[
            {"role": "system", "content": "Write concise Russian editorial/social copy without marketing fluff."},
            {"role": "user", "content": prompt},
        ],
    )
    return (response.choices[0].message.content or "").strip()


async def _openai_json_request(prompt: str) -> dict:
    response = await openai_client.chat.completions.create(
        model=OPENAI_TEXT_MODEL,
        messages=[
            {"role": "system", "content": "Return valid JSON only. No markdown fences, no explanation."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    return json.loads(content)


async def _openai_text_request(prompt: str) -> str:
    response = await openai_client.chat.completions.create(
        model=OPENAI_TEXT_MODEL,
        messages=[
            {"role": "system", "content": "Write concise Russian editorial/social copy without marketing fluff."},
            {"role": "user", "content": prompt},
        ],
    )
    return (response.choices[0].message.content or "").strip()


def _is_russian_source(text: str) -> bool:
    cyr = len(re.findall(r"[А-Яа-яЁё]", text))
    lat = len(re.findall(r"[A-Za-z]", text))
    return cyr > lat


def _looks_english_heavy(text: str) -> bool:
    cyr = len(re.findall(r"[А-Яа-яЁё]", text))
    lat = len(re.findall(r"[A-Za-z]", text))
    return lat > cyr * 2 and lat > 20


async def _normalize_analysis_language(source_text: str, result: dict) -> dict:
    if not _is_russian_source(source_text):
        return result
    joined = " ".join(
        f"{item.get('title', '')} {item.get('summary', '')}"
        for item in result.get("slides_plan", [])
    )
    if not _looks_english_heavy(joined):
        return result
    prompt = f"""Переведи и нормализуй этот JSON на русский язык. Верни только JSON.

{json.dumps(result, ensure_ascii=False)}
"""
    normalized = await _openai_json_request(prompt)
    return normalized if "slides_plan" in normalized else result


async def _normalize_slides_language(source_text: str, slides: list[dict]) -> list[dict]:
    if not _is_russian_source(source_text):
        return slides
    joined = " ".join(f"{slide.get('title','')} {slide.get('body','')}" for slide in slides)
    if not _looks_english_heavy(joined):
        return slides
    prompt = f"""Переведи и нормализуй этот JSON со слайдами на русский язык. Верни только JSON-объект.

{json.dumps({'slides': slides}, ensure_ascii=False)}
"""
    normalized = await _openai_json_request(prompt)
    result = normalized.get("slides", [])
    return result if isinstance(result, list) else slides


async def _normalize_carousel_plan_language(source_text: str, plan: dict) -> dict:
    if not _is_russian_source(source_text):
        return plan
    joined = " ".join(
        f"{slide.get('title','')} {slide.get('body','')}"
        for slide in plan.get("slides", [])
    )
    if not _looks_english_heavy(joined):
        return plan
    prompt = f"""Переведи и нормализуй этот JSON-план карусели на русский язык.
Не трогай системные поля role/theme_hint/tone/cta кроме текстовых значений title/body/emphasis/audience при необходимости.
Верни только JSON.

{json.dumps(plan, ensure_ascii=False)}
"""
    normalized = await _openai_json_request(prompt)
    return normalized if "slides" in normalized else plan


async def _normalize_caption_language(source_text: str, caption: str) -> str:
    if not _is_russian_source(source_text):
        return caption
    if not _looks_english_heavy(caption):
        return caption
    prompt = f"""Перепиши этот caption полностью на русском языке, коротко и естественно:

{caption}
"""
    return await _openai_text_request(prompt)
