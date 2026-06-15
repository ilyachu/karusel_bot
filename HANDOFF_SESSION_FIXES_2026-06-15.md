# HANDOFF — сессия фиксов кастомного фона и русского языка в обложке

**Дата:** 2026-06-15
**Бот:** `@karusel_new_bot` (id 8918241849), контейнер `karusel_bot_new` на `root@5.253.188.164`
**Локальный репо:** `/Users/ilyachumachenkov/Documents/контент мопед/karusel_bot`
**Ветка:** `main`, коммиты за сессию: `a2bc1b4` (фон), `fa95483` (русский язык)

---

## TL;DR для следующего агента

Сделано **3 бага, 1 feature, 1 deploy**:

1. **Кастомный фон не показывался** в 4 стилях карусели (magazine / terminal / poster / carddeck) — починено в `services/html_renderer.py`.
2. **Обложка генерировалась на английском**, игнорируя русский текст пользователя — починено в `services/gemini_client.py` (двойная защита: system prompt + retranslation fallback).
3. **Кнопка «📬 Обратная связь»** (feature) — отправляет сообщение пользователя админу `ADMIN_ID=252202`. Реализована в `handlers/common.py` + bypass в `middlewares/access.py`.
4. **Pipeline-статусы карусели** стали детальными (5 шагов вместо 3 строк).
5. **Деплой через `cat | ssh`** — без rsync (rsync нестабилен).

Всё задеплоено, бот работает, тесты 90/90 зелёные.

---

## Подробный разбор

### Что было ДО этой сессии

В чате с пользователем (id 252202) `@karusel_new_bot`:

- Бот работал, генерировал карусели, но **кастомный фон не показывался** — картинка либо была полностью перекрыта, либо не видна вообще.
- В режиме "Обложка" (`🖼 Обложка`) текст генерировался **на английском**, даже когда пользователь писал по-русски.
- Кнопки "📬 Обратная связь" не было — пользователь не мог отправить баг-репорт.
- В чате крутилась фраза «⚠️ Рендер в упрощённом формате» даже когда рендер успешно работал с custom bg.

### Что сделано

#### 1. Кастомный фон: 4 стиля в `services/html_renderer.py`

**Корень проблемы:** стили накладывали непрозрачные заливки поверх пользовательской картинки:
- `magazine`: `body { background: #09070f }` + `custom-bg { opacity: 0.64 }` + `::after overlay rgba(0,0,0,0.10→0.44)` — фон виден на 36%.
- `terminal`: `body { background: #0a0e0a }` + `custom-bg { filter: grayscale(1); opacity: 0.64 }` — фон **полностью обесцвечен**.
- `poster`: `.block { background: #d63921 }` — **сплошной цветной прямоугольник** поверх изображения.
- `carddeck`: `.canvas { padding: 48px }` (белые поля по краям) + `.card { background: rgba(255,255,255,0.04); backdrop-filter: blur(16px) }` — карточка **запудривает** фон.

**Бонус-баг:** в `carddeck` `custom_bg_div` стоял **внутри `<style>` блока**, поэтому браузер игнорировал `<div>` (это CSS, а не HTML) — фон не показывался вообще.

**Фикс (для всех 4 стилей):**
- Когда `safe_bg` есть (custom_bg): `body { background: transparent }`.
- `custom-bg` рендерится на `opacity: 1.0` без `grayscale`, без агрессивных overlay.
- Поверх фона — **полупрозрачный overlay** (`linear-gradient(180deg, rgba(0,0,0,0.15) 0%, rgba(0,0,0,0.35) 100%)`) для контраста с текстом.
- Весь текст получает `text-shadow: 0 1px 10px rgba(0,0,0,0.85)` для читаемости на любой фотке.
- В `carddeck` `custom_bg_div` перенесён в `<body>`.
- В `poster` `.block` стал `rgba(0,0,0,0.45)` вместо сплошной заливки.
- В `carddeck` отключён `backdrop-filter`, карточка `rgba(15,15,26,0.55)`.

**Тесты:** обновлён `test_build_slide_html_supports_stronger_background_treatment` — теперь проверяет, что фон виден (нет `grayscale` в HTML), а не конкретное значение `opacity: 0.64`.

**Результат:** 90/90 passed. Локально отрендерил 4 тестовых PNG с загруженным фоном — все 4 стиля показывают фон.

#### 2. Обложка на английском: `services/gemini_client.py`

**Корень проблемы:** `generate_cover_plan` (отдельный LLM-функционал для обложек) не имел защиты от английского, в отличие от `generate_instagram_carousel_plan` для каруселей (там есть `_normalize_carousel_plan_language`).

System prompt у `_router_json_request` и `_openai_json_request` был:
```
"Return valid JSON only. No markdown fences, no explanation."
```

**Без инструкции про русский язык.** LLM получала только user-prompt, где правило "Русский." стояло в самом конце — игнорировала.

**Фикс (3 уровня защиты):**

1. **System prompt** обновлён:
   ```
   "Return valid JSON only. No markdown fences, no explanation. ВАЖНО: все
    текстовые значения (headline, subtitle, body, и т.д.) должны быть
    написаны на русском языке, если в prompt не указан другой язык."
   ```
   Изменены оба: `_router_json_request` (NeuralDeep) и `_openai_json_request` (OpenRouter fallback).

2. **User prompt** в `generate_cover_plan` усилен — правило про русский вынесено в самое начало, добавлены примеры разрешённых латинских токенов (`HTML`, `AI`).

3. **Защитный слой (retranslatoin):** новые функции:
   - `_cover_plan_looks_english(plan)` — детектит английский результат (соотношение `lat > cyr * 2 and lat > 20`).
   - `_retranslate_cover_plan_to_russian(plan, base_text, style, format_key)` — если план на английском, вызывает LLM с явной командой "переведи JSON на русский" и мержит перевод.

**Тесты:** добавлены 3 новых в `tests/test_gemini_client.py`:
- `test_is_russian_source_detects_cyrillic_text`
- `test_looks_english_heavy_detects_english_dominant`
- `test_cover_plan_looks_english_flags_english_plan`

**Результат:** 90/90 passed. В Telegram после деплоя обложка должна быть на русском.

#### 3. Кнопка «📬 Обратная связь» (feature)

**Реализация:**
- `handlers/common.py`:
  - Новый `StatesGroup Feedback(waiting_for_message)`.
  - Хендлер `cmd_feedback_start` — по кнопке «📬 Обратная связь» ставит FSM-состояние.
  - Хендлер `cmd_feedback_receive` — отправляет `bot.send_message(ADMIN_ID, admin_text)` админу и подтверждает пользователю.
  - `ADMIN_ID` импортируется из `config.py` (= 252202).
- `middlewares/access.py`: bypass в AccessMiddleware — если `state == Feedback.waiting_for_message`, пропускает всех пользователей (не только whitelist / admin).
- Главное меню в `handlers/common.py` (reply keyboard) уже имеет кнопку «📬 Обратная связь».

**Результат:** пользователь жмёт кнопку → пишет сообщение → бот пересылает админу, пользователь получает «✅ Спасибо!».

#### 4. Pipeline-статусы карусели: детализация (5 шагов)

`run_insta_auto_pipeline` в `handlers/carousel_flow.py` теперь показывает пользователю **прогресс по 5 шагам** через `_build_pipeline_status(step, total_steps, title, detail)`:

1. «Собираю структуру» — `Планирую N слайдов[ со своим фоном].`
2. «Генерирую тексты» — `Собираю план карусели и раскладываю материал по слайдам.`
3. «Генерирую подпись» — `Подготавливаю caption для публикации.`
4. «Рендерю слайды» — `Собираю финальные изображения 1080×1350.`
5. «Готовлю выдачу» — `Сохраняю экспорт и отправляю карусель в чат.`

Также добавлена функция `resolve_target_slide_count(text, slide_count_setting)` в `handlers/common.py` — раньше `target_slides` жёстко вычислялся из `word_count // 15 + 2`, теперь уважает пользовательскую настройку `insta_slide_count` ("auto" / "4" / "5" / "6" / "7").

Также в финальной подписи к карусели появилась отдельная строка `Фон: свой загруженный / авто-пресеты бота / без отдельного фонового изображения` (раньше был только суффикс `+ свой фон` в строке Визуала).

#### 5. Подавление ложного warning при custom bg

В `handlers/carousel_flow.py`:
```python
# БЫЛО:
if render_mode != "html":
    ... # показать warning "HTML-рендер недоступен"
# СТАЛО:
if render_mode != "html" and not custom_bg_bytes:
    ... # показать warning только если custom_bg НЕ используется
```

Логика: если мы УЖЕ отрендерили custom-bg через html-custom-bg — warning бессмысленный.

---

## Деплой

**Процедура** (без rsync, чисто `cat | ssh`):

```bash
# 1. Коммит
git add -A
git commit -m "..."

# 2. Пуш
git push origin main

# 3. Копирование файлов на сервер
cat services/html_renderer.py | ssh root@5.253.188.164 'cat > /root/karusel_bot_v2/services/html_renderer.py'
cat services/gemini_client.py | ssh root@5.253.188.164 'cat > /root/karusel_bot_v2/services/gemini_client.py'
# (по аналогии для tests, handlers и т.д.)

# 4. Пересборка и перезапуск контейнера
ssh root@5.253.188.164 'cd /root/karusel_bot_v2 && docker compose down bot && docker compose up -d --build bot'
```

**Проверка:**
```bash
ssh root@5.253.188.164 'docker logs karusel_bot_new --tail 30'
```

Ожидаемые строки:
- `Database initialized successfully.`
- `Bot started...`
- `Start polling`
- `Run polling for bot @karusel_new_bot id=8918241849 - 'karusel_new'`

---

## Структура репо (для контекста)

```
/Users/ilyachumachenkov/Documents/контент мопед/karusel_bot/
├── handlers/
│   ├── common.py              # Кнопки меню, /start, /help, Feedback, Insta Auto setup
│   ├── carousel_flow.py       # Pipeline карусели (5 шагов), Insta Auto
│   └── cover_flow.py          # Pipeline обложки (отдельный, с generate_cover_plan)
├── middlewares/
│   └── access.py              # AccessMiddleware + bypass для Feedback
├── services/
│   ├── html_renderer.py       # build_slide_html + 4 стиля (magazine/terminal/poster/carddeck)
│   ├── gemini_client.py       # LLM: generate_cover_plan, generate_instagram_carousel_plan, _router_json_request
│   ├── cover_renderer.py      # COVER_STYLES, render_cover_html
│   ├── layout_engine.py       # LayoutSpec, build_instagram_layout_specs
│   ├── background_registry.py # Авто-выбор пресетного фона
│   ├── cover_renderer.py      # Обложки (HTML)
│   ├── image_renderer.py      # Pillow fallback рендер
│   └── ... (gemini, openai, threads, etc.)
├── tests/                     # 90 тестов, 100% зелёных
├── config.py                  # BOT_TOKEN, ADMIN_ID=252202, OpenRouter/OpenAI/NeuralDeep ключи
├── .env                       # Реальные ключи (НЕ в git)
├── .env.example               # Шаблон (в git)
└── .gitignore                 # Игнорирует .env, exports/, кэши
```

**`config.py`** хранит `ADMIN_ID=252202` (user id владельца).

---

## Серверная инфраструктура

- **Хост:** `root@5.253.188.164`
- **Путь к проекту:** `/root/karusel_bot_v2/`
- **Контейнер:** `karusel_bot_new` (Docker Compose)
- **Docker Compose:** `karusel_bot_v2` сеть
- **Логи:** `docker logs karusel_bot_new --tail 100`

**Внутри контейнера:**
- `/app/` — код
- `/app/.env` — переменные окружения (реальные ключи)
- Playwright + Chromium установлены

---

## Известные проблемы / Что НЕ сделано

1. **NeuralDeep иногда возвращает `Unterminated string starting at...`** — JSON парсинг падает. Видно в логах. Есть fallback на OpenAI, но не всегда спасает. **Не починено в этой сессии** — обойти это можно перезапросом.

2. **Опция «🛰 Advanced Meta plan» и публикация в Instagram/Threads** — кнопка показывается только админу (id 252202). Реально ли работает — неизвестно (не тестировалось в этой сессии).

3. **OpenAI fallback иногда возвращает 401 Unauthorized** (видно в логах). Если NeuralDeep упал И OpenAI упал — `html_body` пустой, и рендер уходит в Pillow fallback (для пресетов). Для custom_bg — `render_layout_spec` тоже fallback, и это может выглядеть не идеально. **Не починено.**

4. **Локальный .env НЕ в git, но история `.env` была очищена**. Если ты вносишь изменения в `.env` — никогда не коммить. Используй `.env.example` как шаблон.

5. **HANDOFF_NEXT_AGENT.md** удалён в текущих uncommitted changes — это нормально, я создаю новый файл `HANDOFF_SESSION_FIXES_2026-06-15.md` (этот).

---

## Тесты

**Запуск:**
```bash
cd /Users/ilyachumachenkov/Documents/контент\ мопед/karusel_bot
source .venv/bin/activate
python3 -m pytest tests/ -x --tb=short
```

**Результат сессии:** `90 passed in 17.13s` (87 → 90: добавлены 3 теста в `test_gemini_client.py`).

**Покрытие тестами, относящимися к фиксам этой сессии:**
- `tests/test_html_renderer.py` — обновлён `test_build_slide_html_supports_stronger_background_treatment`
- `tests/test_gemini_client.py` — 3 новых теста на детектор языка и обложку

---

## Коммиты этой сессии

1. `a2bc1b4` — **fix: keep custom background fully visible across all layout styles**
   - `services/html_renderer.py` (4 стиля: magazine/terminal/poster/carddeck)
   - `tests/test_html_renderer.py` (обновлены тесты)

2. `fa95483` — **fix: force Russian output in cover plan and JSON LLM requests**
   - `services/gemini_client.py` (system prompts + retranslation fallback)
   - `tests/test_gemini_client.py` (3 новых теста)

---

## Uncommitted changes (третья сессия?)

**ВАЖНО:** В `git status` есть **uncommitted changes** в 4 файлах:

```
D  HANDOFF_NEXT_AGENT.md
M  handlers/carousel_flow.py
M  handlers/common.py
M  middlewares/access.py
M  tests/test_flow_structure.py
```

Это **.diff 498 строк**, включающий:
- Хендлер `Feedback` (кнопка "📬 Обратная связь") и FSM — реализовано, но **не закоммичено**.
- Bypass в `AccessMiddleware` для Feedback — реализовано, но **не закоммичено**.
- 5-шаговый pipeline-статус в `run_insta_auto_pipeline` — реализовано, но **не закоммичено**.
- `resolve_target_slide_count` в `handlers/common.py` — реализовано, но **не закоммичено**.

**Эти изменения ЗАДЕПЛОЕНЫ** через `cat | ssh` и **работают в проде**, но **не в git**. Если следующий агент хочет чистую историю — нужно закоммитить.

**Предлагаемое сообщение коммита:**
```
feat: feedback flow, 5-step pipeline status, slide count setting

- Add Feedback FSM + button, with AccessMiddleware bypass so all users
  can send feedback to ADMIN_ID=252202.
- Replace 3-line ad-hoc pipeline messages with 5-step status via
  _build_pipeline_status() helper.
- Add resolve_target_slide_count() helper in handlers/common.py to
  respect user's insta_slide_count setting ("auto" / "4" / "5" / "6" / "7").
- Add INSTA_SLIDE_COUNT_LABELS and insta_slide_count_selected handler.
- Update tests/test_flow_structure.py to cover the new helpers.
```

---

## Быстрая команда для следующего агента

Если нужно проверить, что бот жив:
```bash
ssh root@5.253.188.164 'docker logs karusel_bot_new --tail 30'
```

Если нужно отправить тестовое сообщение в Telegram-бот (как я делал в этой сессии через MCP `telegram_send_message`):
```python
# Chat id владельца: 8918241849 (karusel_new)
# User id: 252202
telegram_send_message(chat_id="8918241849", text="🚀 Insta Auto")
```

Если нужно перерендерить PNG локально для проверки CSS-фиксов:
```bash
cd /Users/ilyachumachenkov/Documents/контент\ мопед/karusel_bot
source .venv/bin/activate
python3 -c "
from services.html_renderer import build_slide_html
from services.layout_engine import LayoutSpec
from services.cover_renderer import image_bytes_to_data_url
from playwright.sync_api import sync_playwright

with open('assets/background_presets/bg_03.jpeg', 'rb') as f:
    bg_bytes = f.read()
custom_url = image_bytes_to_data_url(bg_bytes, 'image/jpeg')

spec = LayoutSpec(
    slide_index=1, total_slides=3, theme='business_dark', visual_mode='editorial',
    font_style='prosto', variant='center', text_position='center',
    badge_text='TEST', footer_tags=['test'],
    highlight_words=[], density='medium', show_progress=True,
    supporting_cards=[], role='cover', archetype='hook',
    title='Test', body='Test', layout_style='magazine',  # меняй на terminal/poster/carddeck
)
html = build_slide_html(spec, 'chu ai', custom_url, 'strong')

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1080, 'height': 1350}, device_scale_factor=1)
    page.set_content(html, wait_until='load')
    page.wait_for_timeout(500)
    page.screenshot(path='/tmp/test.png', clip={'x': 0, 'y': 0, 'width': 1080, 'height': 1350})
    browser.close()
print('OK → /tmp/test.png')
"
```

---

## Контекст разговора с пользователем

Пользователь (Илья, user_id=252202) попросил:
1. Добавить кнопку «📬 Обратная связь» → пересылать админу.
2. Задеплоить бота (через cat|ssh, не rsync).
3. Провести аудит продакшен-готовности.
4. Починить баг с кастомными/пресетными фонами.
5. Исправить проблему: обложка генерируется на английском.

Все 5 пунктов сделаны и задеплоены. Бот работает в `@karusel_new_bot`.

**Следующий агент:** посмотри uncommitted changes, закоммить, если они нужны. Если есть баги — изучи `services/html_renderer.py` (4 стиля) и `services/gemini_client.py` (LLM layer).
