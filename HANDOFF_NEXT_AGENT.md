# HANDOFF: Karusel Bot — AI-generated HTML Carousels

## Рабочая директория
```
/Users/ilyachumachenkov/Documents/контент мопед/karusel_bot
```

## Текущий статус (что работает)

### UI (handlers/common.py)
3 понятных параметра при настройке:
- **📰 СТИЛЬ СЛАЙДОВ**: Авто, 📰 Журнал, 💻 Терминал, 🎯 Плакат, 📇 Карточки
- **🌈 ЦВЕТОВАЯ ПАЛИТРА**: Авто, 🌙 Тёмная, ☀️ Светлая, 🟤 Тёплая, 💥 Яркая
- **✍️ ПОДАЧА ТЕКСТА**: 📝 Как есть, ✂️ Короче, 📚 Подробнее, 🔥 Ярче

Кнопка «Обложка в этом стиле» — удалена. Кнопка «Создать карусель» — удалена.
Кнопки публикации (Instagram/Threads) — видны только ADMIN_ID.

### Боты на сервере (SSH: root@5.253.188.164 / <REDACTED>)
- **@karusel_new_bot** (токен в .env новый) — `/root/karusel_bot_v2/`
- **@karusel_chu_bot** (старый токен) — `/root/my_bot_project/`
- Docker: `karusel_bot_new` и `karusel_bot_old`, оба Up
- Chromium работает, рендер через Playwright
- AI: neuraldeep.ru (gemma-4-31b), fallback OpenAI

### Тесты
```
cd karusel_bot && source .venv/bin/activate && python3 -m pytest tests/ -v
```
Все 68 тестов проходят.

---

## КЛЮЧЕВАЯ ПРОБЛЕМА: карусели выглядят одинаково

### Текущая архитектура (плохо)
```
1. AI генерирует ТОЛЬКО ТЕКСТ (заголовки + body)
2. Layout engine выбирает ШАБЛОН (4 шаблона × 8 тем)
3. HTML-рендер вставляет текст в шаблон
```
→ 4 шаблона, AI не может повлиять на вёрстку → все карусели похожи

### Нужная архитектура (как open-carrusel)
```
1. AI получает выбранный стиль (magazine/terminal/poster/carddeck)
2. AI генерирует УНИКАЛЬНЫЙ HTML/CSS для КАЖДОГО СЛАЙДА
3. Рендер просто скриншотит то, что AI написал
```

---

## Референс: open-carrusel (319 ⭐)

**URL:** https://github.com/Hainrixz/open-carrusel
**Лицензия:** MIT
**Стек:** Next.js 16, React 19, TypeScript, Puppeteer

### Как он работает
1. Claude пишет body-level HTML для каждого слайда через curl POST
2. Функция `wrapSlideHtml()` оборачивает body в полноценный HTML-документ
3. Puppeteer скриншотит HTML → PNG
4. **Каждый слайд — уникальный HTML, придуманный AI с нуля**

### Ключевой файл для изучения
```typescript
// open-carrusel/src/lib/slide-html.ts
export function wrapSlideHtml(slideHtml: string, aspectRatio): string {
  // Добавляет Google Fonts, viewport, размеры
  // То же самое, что наш build_slide_html()
}
```

### Системный промпт Claude (ключевое)
```typescript
// open-carrusel/src/lib/chat-system-prompt.ts
```
Claude получает: brand colors, fonts, style keywords, reference images
Claude пишет: уникальный HTML/CSS для каждого слайда
→ Никаких шаблонов, каждый слайд уникален

### Что можно взять
1. **Концепция AI-generated HTML** — вместо шаблонов AI пишет HTML
2. **Google Fonts авто-подгрузка** — парсит font-family из HTML, подтягивает с CDN
3. **Reference images** — Claude смотрит картинки и копирует стиль

---

## Что нужно сделать

### Приоритет 1: AI-генерация HTML для слайдов

**Где менять:**
- `services/gemini_client.py` — добавить `generate_slide_html()`
- `services/html_renderer.py` — упростить, убрать шаблоны
- `handlers/carousel_flow.py` — вставить AI-генерацию HTML в пайплайн

**Как должно работать:**
1. AI уже сгенерировал `carousel_plan` (текст + layout_style)
2. Для каждого слайда AI генерирует **уникальный HTML/CSS** в рамках выбранного стиля
3. `build_slide_html()` проверяет: если AI вернул HTML — используй его, иначе — текущий шаблон
4. Playwright/Pillow рендерит в PNG

**Новый промпт** (в `generate_instagram_carousel_plan` или новый метод):
```
Ты — CSS-дизайнер каруселей в стиле {layout_style}.
Для каждого слайда верни body-level HTML:
<div style="...">...</div>

Стиль {layout_style}: 
- magazine: Playfair Display, serif, элегантно, воздух
- terminal: JetBrains Mono, monospace, зелёный на чёрном
- poster: Unbounded, огромная типографика, цветовые блоки
- carddeck: Inter, скругления, glassmorphism, dot-прогресс

Требования:
- body-level HTML (без <html>/<head>/<body>)
- Inline-стили или <style> внутри
- 1080×1350 px
- Google Fonts: font-family укажи, система подгрузит
- Градиенты, тени, flexbox
- Каждый слайд должен выглядеть уникально
```

### Приоритет 2: Починить визуальное разнообразие обложек

- `services/cover_renderer.py` — 10 стилей, 4 HTML-шаблона (`_poster_markup`, `_retro_markup`, `_magazine_markup`, `_terminal_markup`)
- Нужно убедиться что стили в группах «Типографика» (blue_type, grid_steps, paper_brief) и «Атмосфера» (retro_polaroid, quiet_editorial, chalk_notes) выглядят по-настоящему по-разному, а не только цветами
- Google Fonts уже подключены через `@import`

### Приоритет 3: Улучшить AI-промпт для выбора стиля

Сейчас AI редко выбирает layout_style осознанно. Нужно усилить промпт в `generate_instagram_carousel_plan()`:
```
Выбери layout_style строго по контексту:
- magazine: аналитика, эссе, разборы
- terminal: технические обзоры, бенчмарки, AI-новости
- poster: манифесты, анонсы, сильные утверждения
- carddeck: списки, чеклисты, образовательный контент
```

---

## Ключевые файлы

| Файл | Строк | Назначение |
|------|-------|-----------|
| `handlers/common.py` | 361 | UI настроек (3 параметра) |
| `handlers/carousel_flow.py` | 620 | Главный пайплайн генерации |
| `services/gemini_client.py` | 339 | **AI-запросы (тут менять промпты)** |
| `services/html_renderer.py` | 582 | 4 HTML-шаблона (magazine, terminal, poster, carddeck) |
| `services/layout_engine.py` | 992 | Layout-спеки, темы, visual modes |
| `services/cover_renderer.py` | 1275 | 10 стилей обложек, 4 шаблона |
| `utils/states.py` | 13 | FSM-состояния |
| `config.py` | 41 | Конфиги (neuraldeep, OpenAI) |
| `Dockerfile` | 21 | Сборка (Python 3.12, Chromium) |

---

## Структура пайплайна

```
Пользователь → текст
  1. generate_instagram_carousel_plan(text) → JSON-план (текст + layout_style)
  2. parse_carousel_plan(JSON) → CarouselPlan
  3. apply_theme_override / apply_theme_selection_policy → выбор темы
  4. build_instagram_layout_specs(plan, layout_style) → [LayoutSpec, ...]
  5. render_layout_spec_html(spec) → PNG
  6. build_instagram_export → сохранение
  7. caption + кнопки публикации
```

### HL: Что менять в п.5

Сейчас `render_layout_spec_html` → `build_slide_html` → выбирает шаблон по `spec.layout_style`.
Надо: AI генерирует HTML для каждого слайда в п.1 или между п.3 и п.4.

---

## Как деплоить

```bash
# Локально -> сервер
rsync -avz handlers/common.py root@5.253.188.164:/root/karusel_bot_v2/
rsync -avz services/gemini_client.py root@5.253.188.164:/root/karusel_bot_v2/

# Пересобрать на сервере
ssh root@5.253.188.164 'cd /root/karusel_bot_v2 && docker compose down bot && docker compose up -d --build bot'

# Проверить
ssh root@5.253.188.164 'docker logs karusel_bot_new --tail 10'
```

---

## Ссылки

- **open-carrusel** (319 ⭐): https://github.com/Hainrixz/open-carrusel — AI генерирует уникальный HTML под каждый слайд
- **viraloop** (60 ⭐): https://github.com/mutonby/viraloop — Hook-система (SHOCK/CURIOSITY/CONTRADICTION)
- **instagram-thread-carousel** (18 ⭐): https://github.com/Samin12/instagram-thread-carousel — Twitter screenshot style