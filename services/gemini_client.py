import google.generativeai as genai
import json
import os
import logging
from openai import AsyncOpenAI

from config import GEMINI_API_KEY, OPENAI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Use a model that supports JSON response if possible, or instruct it carefully.
# gemini-1.5-flash is faster and cheaper.
MODEL_NAME = "gemini-2.5-flash"
OPENAI_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")

async def analyze_text_and_propose_slides(text: str) -> dict:
    """
    Analyzes text and proposes a slide structure.
    Returns a dict with keys: recommended_slides (int), slides_plan (list of dicts).
    """
    model = genai.GenerativeModel(MODEL_NAME)
    
    prompt = f"""
    Ты — профессиональный контент-мейкер. Твоя задача — проанализировать текст на русском языке и предложить структуру для карусели (слайдов) в Instagram/Telegram.
    
    Входной текст:
    {text}
    
    Требования:
    1. Рекомендуемое количество слайдов: от 1 до 8.
    2. Не делай слишком длинные блоки.
    3. Первый слайд — цепляющий заголовок.
    4. Последний слайд — вывод или Call to Action.
    5. Верни ответ СТРОГО в формате JSON.
    
    Формат JSON:
    {{
      "recommended_slides": int,
      "slides_plan": [
        {{ "slide_index": 1, "title": "Заголовок слайда", "summary": "Краткое описание идеи слайда" }},
        ...
      ]
    }}
    """
    
    try:
        response = await model.generate_content_async(prompt, generation_config={"response_mime_type": "application/json"})
        text_response = response.text
        # Clean up markdown if present
        if text_response.startswith("```json"):
            text_response = text_response[7:]
        if text_response.startswith("```"):
            text_response = text_response[3:]
        if text_response.endswith("```"):
            text_response = text_response[:-3]
            
        return json.loads(text_response)
    except Exception as e:
        logging.error(f"Error in analyze_text_and_propose_slides: {e}")
        fallback_prompt = f"""
        Ты — профессиональный контент-мейкер. Проанализируй текст и предложи структуру карусели.

        Входной текст:
        {text}

        Верни строго JSON:
        {{
          "recommended_slides": int,
          "slides_plan": [
            {{ "slide_index": 1, "title": "Заголовок слайда", "summary": "Краткое описание идеи слайда" }}
          ]
        }}
        """
        try:
            result = await _openai_json_request(fallback_prompt)
            if "recommended_slides" in result and "slides_plan" in result:
                return result
        except Exception as fallback_error:
            logging.error(f"OpenAI fallback failed in analyze_text_and_propose_slides: {fallback_error}")
        return {
            "recommended_slides": 1,
            "slides_plan": [{"slide_index": 1, "title": "Ошибка анализа", "summary": "Не удалось проанализировать текст."}]
        }

async def generate_final_slides(base_text: str, target_slides_count: int, rewrite_style: str) -> list[dict]:
    """
    Generates final text for each slide based on the plan and user preferences.
    Returns a list of dicts: [{"title": "...", "body": "..."}, ...]
    """
    model = genai.GenerativeModel(MODEL_NAME)
    
    style_instructions = {
        "exact": """КРИТИЧЕСКИ ВАЖНО: Максимально сохраняй оригинальный текст!
        - Используй ТОЛЬКО фразы и формулировки из исходного текста
        - НЕ переписывай, НЕ перефразируй, НЕ добавляй своих слов
        - Просто логически разбей текст на части
        - Можешь лишь слегка сократить для формата слайда
        - Заголовки можешь взять из самого текста или сделать короткими (1-3 слова)""",
        
        "marketing": """Пиши продающим языком:
        - Используй триггеры и эмоциональную окраску
        - Добавляй призывы к действию
        - Делай акцент на выгодах
        - Используй цепляющие заголовки""",
        
        "educational": """Пиши в обучающем стиле:
        - Четко и структурировано
        - С полезными выводами
        - Логичное изложение от простого к сложному
        - Понятным языком""",
        
        "concise": """Пиши максимально кратко:
        - Убирай всё лишнее
        - Оставляй только суть
        - Короткие ёмкие фразы
        - Без "воды" """
    }
    
    instruction = style_instructions.get(rewrite_style, "Пиши интересно и понятно.")
    
    prompt = f"""Ты — редактор слайдов. Напиши финальный текст для карусели из {target_slides_count} слайдов.

Исходный текст:
{base_text}

Стиль: {instruction}

ТРЕБОВАНИЯ:
1. Язык: Русский
2. Объем 'body': 2-6 строк (максимум 300 символов), подходящий для формата 1080x1350
3. Каждый слайд — законченная мысль
4. Если выбран стиль "exact" - НЕ ПЕРЕПИСЫВАЙ текст, просто разбей его логически на {target_slides_count} частей
5. Формат JSON: массив объектов с полями "title" и "body"
6. НЕ используй markdown (```json)
7. ВАЖНО: Заголовок (title) НЕ должен дублироваться в тексте (body). Заголовок — это хук, а текст раскрывает мысль. Не повторяй одно и то же.

Формат ответа:
[
  {{ "title": "Заголовок слайда", "body": "Текст слайда..." }},
  ...
]
"""
    
    try:
        response = await model.generate_content_async(prompt, generation_config={"response_mime_type": "application/json"})
        text_response = response.text
        # Clean up markdown if present
        if text_response.startswith("```json"):
            text_response = text_response[7:]
        if text_response.startswith("```"):
            text_response = text_response[3:]
        if text_response.endswith("```"):
            text_response = text_response[:-3]
            
        return json.loads(text_response)
    except Exception as e:
        logging.error(f"Error in generate_final_slides: {e}")
        fallback_prompt = f"""Ты — редактор слайдов. Напиши финальный текст для карусели из {target_slides_count} слайдов.

Исходный текст:
{base_text}

Стиль: {instruction}

Верни строго JSON-объект:
{{
  "slides": [
    {{ "title": "Заголовок слайда", "body": "Текст слайда..." }}
  ]
}}
"""
        try:
            result = await _openai_json_request(fallback_prompt)
            slides = result.get("slides", [])
            if isinstance(slides, list):
                return slides
        except Exception as fallback_error:
            logging.error(f"OpenAI fallback failed in generate_final_slides: {fallback_error}")
        return []


async def generate_instagram_caption(base_text: str, slides_content: list[dict]) -> str:
    """
    Generate a concise Instagram caption that matches the final carousel.
    """
    model = genai.GenerativeModel(MODEL_NAME)

    slides_summary = "\n".join(
        f"- {slide.get('title', '').strip()}: {slide.get('body', '').strip()}"
        for slide in slides_content
    )

    prompt = f"""Ты — SMM-редактор. Напиши caption для Instagram-карусели.

Исходный текст:
{base_text}

Слайды карусели:
{slides_summary}

Требования:
1. Язык: русский.
2. Стиль: живой, уверенный, без воды.
3. Структура:
   - 1 короткий хук
   - 2-4 абзаца сути
   - 1 CTA в конце
4. Не больше 1200 символов.
5. Добавь 5-8 релевантных хэштегов в конце.
6. Не используй markdown.
"""

    try:
        response = await model.generate_content_async(prompt)
        return response.text.strip()
    except Exception as e:
        logging.error(f"Error in generate_instagram_caption: {e}")
        try:
            return await _openai_text_request(prompt)
        except Exception as fallback_error:
            logging.error(f"OpenAI fallback failed in generate_instagram_caption: {fallback_error}")
            return "Сохрани этот пост, чтобы вернуться к нему позже.\n\n#instagram #carousel #content #marketing #telegram"


async def generate_instagram_carousel_plan(base_text: str, target_slides_count: int) -> dict:
    """
    Generate a structured carousel plan with slide roles and theme hints for
    the Instagram auto mode.
    """
    model = genai.GenerativeModel(MODEL_NAME)

    prompt = f"""Ты — контент-стратег и арт-директор Instagram-каруселей.

На основе исходного текста собери JSON-план карусели из {target_slides_count} слайдов.

Исходный текст:
{base_text}

Верни строго JSON в формате:
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
      "emphasis": ["ключевой акцент", "ещё один акцент"],
      "density": "low | medium | high",
      "theme_hint": "business_dark | minimal_light | creator_bold | editorial_premium | memory_archive | founder_brief | growth_black | research_mono"
    }}
  ]
}}

Требования:
1. Язык — русский.
2. Первый слайд должен быть hook.
3. Последний слайд должен быть cta.
4. Основные слайды должны чередовать context / point / proof / example, если это уместно.
5. title не длиннее 90 символов.
6. body не длиннее 260 символов.
7. emphasis — только реальные смысловые акценты из этого слайда.
8. Не добавляй markdown, комментарии или пояснения.
9. Выбирай `theme_hint` осознанно по типу контента:
   - `founder_brief` для коротких founder / product / strategy постов
   - `growth_black` для growth, performance, marketing, revenue, ops
   - `research_mono` для research, frameworks, technical explainers
   - `memory_archive` для memory, knowledge, note-like editorial posts
"""

    try:
        response = await model.generate_content_async(
            prompt,
            generation_config={"response_mime_type": "application/json"},
        )
        text_response = response.text
        if text_response.startswith("```json"):
            text_response = text_response[7:]
        if text_response.startswith("```"):
            text_response = text_response[3:]
        if text_response.endswith("```"):
            text_response = text_response[:-3]
        return json.loads(text_response)
    except Exception as e:
        logging.error(f"Error in generate_instagram_carousel_plan: {e}")
        fallback_prompt = f"""Ты — контент-стратег Instagram-каруселей.

Собери строго JSON-план карусели из {target_slides_count} слайдов по исходному тексту:
{base_text}

Формат:
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
"""
        try:
            return await _openai_json_request(fallback_prompt)
        except Exception as fallback_error:
            logging.error(f"OpenAI fallback failed in generate_instagram_carousel_plan: {fallback_error}")
            return {}


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
            {"role": "system", "content": "Write concise, clean Russian marketing/editorial copy."},
            {"role": "user", "content": prompt},
        ],
    )
    return (response.choices[0].message.content or "").strip()
