# Karusel Bot

Telegram-бот, который превращает текст в готовые карусели для Instagram, Threads и Telegram.

```text
текст → план слайдов → выбор стиля → PNG-слайды → export-пакет → публикация
```

## Возможности

- **🚀 Insta Auto** — быстрая генерация карусели с AI-планированием, выбором темы и HTML-рендером.
- **🆕 Карусель NEW** — экспериментальный детерминированный рендер с 3 визуальными стилями (Dark+Teal, Paper+Orange, White+Coral) и выбором подачи текста (Как есть / Короче / Подробнее / Ярче).
- **🖼 Обложка** — генерация обложки для карусели.
- **Голосовые сообщения** — распознавание через OpenAI Whisper.
- **Пересланные посты** — обработка forwarded сообщений.
- **Публикация в Threads** — через официальный API.
- **Подготовка Meta publish plan** — без реальной публикации.
- **Экспорт** — PNG-слайды, caption, metadata в `data/exports/`.

## Как это работает

### Insta Auto (production)

1. Пользователь отправляет текст, голосовое или пересланный пост.
2. Бот анализирует текст через OpenRouter / OpenAI.
3. Бот собирает план карусели (роли слайдов, заголовки, body).
4. Layout engine выбирает тему и структуру слайдов.
5. HTML renderer рендерит слайды в PNG через Playwright Chromium.
6. Бот отправляет слайды в Telegram и сохраняет export-пакет.

### 🆕 Карусель NEW (экспериментальный)

1. Нажмите «🆕 Карусель NEW» в главном меню.
2. Пришлите текст (или голосовое).
3. Выберите подачу текста: **Как есть / Короче / Подробнее / Ярче**.
4. Выберите визуальный стиль: **Dark+Teal / Paper+Orange / White+Coral**.
5. Получите PNG-слайды. Можно переключать стили без повторной генерации текста.

Экспериментальный рендер **не использует AI-сгенерированный HTML** — все слайды строятся по жёстким шаблонам. Это позволяет A/B-тестировать, насколько детерминированный рендер стабильнее AI-рендера.

## Визуальные стили (Карусель NEW)

| Стиль | Фон | Шрифт | Акцент | Декорация |
|-------|-----|-------|--------|-----------|
| **Dark+Teal** | `#0a0a0a` | Inter | teal `#2dd4bf` | radial glow |
| **Paper+Orange** | `#f4ede0` (cream) | Playfair Display | orange `#fb923c` | ruled lines |
| **White+Coral** | `#ffffff` | Unbounded | coral `#fb7185` | dot grid |

## Визуальные темы (Insta Auto)

- `memory_archive` — светлая редакционная тема.
- `research_mono` — светлая аналитическая тема.
- `founder_brief` — спокойная светлая тема.
- `growth_black` — тёмная контрастная тема.

## Быстрый старт

```bash
git clone https://github.com/ilyachu/karusel_bot.git
cd karusel_bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
```

Заполните `.env` (см. ниже), затем:

```bash
python main.py
```

### Через Docker

```bash
cp .env.example .env
# заполните .env
docker compose up -d --build
docker compose logs -f
```

## Переменные окружения

| Переменная | Обязательная | Описание |
|------------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | да | Токен бота из BotFather |
| `ADMIN_ID` | да | Telegram ID администратора |
| `OPENAI_API_KEY` | да | OpenAI API key (Whisper + fallback) |
| `OPENROUTER_API_KEY` | да | OpenRouter API key (генерация текста) |
| `FAL_KEY` | да | Fal.ai key (AI-фоны) |
| `OPENROUTER_MODEL` | нет | Модель для текста (по умолчанию `google/gemini-3.1-flash-lite-preview`) |
| `DATA_DIR` | нет | Папка для SQLite и логов (по умолчанию `data`) |
| `EXPORTS_DIR` | нет | Папка для export-пакетов |
| `EXPORT_PUBLIC_BASE_URL` | нет | Публичный URL для Meta publishing |
| `INSTAGRAM_ACCESS_TOKEN` | нет | Instagram long-lived access token |
| `INSTAGRAM_USER_ID` | нет | Instagram API user ID |
| `THREADS_ACCESS_TOKEN` | нет | Threads access token |
| `THREADS_USER_ID` | нет | Threads user ID |

Полный список — в `.env.example`.

## Админ-доступ

Бот закрыт через allowlist. Администратор задаётся через `ADMIN_ID` в `.env`.

Админ может добавлять/удалять пользователей через `/admin`.

Если пользователь не в allowlist, бот отвечает: «⛔️ У вас нет доступа к этому боту.»

## Структура проекта

```text
handlers/              Telegram-хендлеры (aiogram routers)
  carousel_flow.py     Insta Auto + 🆕 Карусель NEW FSM
  common.py            Главное меню, команды, настройки
  cover_flow.py        Генерация обложек
  admin.py             Админ-панель
services/              Бизнес-логика
  layout_engine.py     Планирование слайдов, темы, LayoutSpec
  html_renderer.py     Production HTML-рендер (Playwright + Pillow)
  experimental_carousel_renderer.py  Экспериментальный детерминированный рендер
  gemini_client.py     LLM-клиент (OpenRouter / OpenAI)
  instagram_package.py Экспорт PNG + caption + metadata
  meta_publish.py      Meta publish plan scaffold
  threads_publish.py   Threads publish plan
  cover_renderer.py    Рендер обложек
  background_registry.py  Пресеты фонов
utils/                 Вспомогательные модули
  database.py          SQLite (allowed_users, export_packages)
  states.py            FSM-состояния (CarouselFlow, TestRenderFlow)
  validation.py        Валидация текста
tests/                 Тесты (unittest)
  test_flow_structure.py  AST-тесты на структуру хендлеров
  test_experimental_carousel_renderer.py  Тесты экспериментального рендера
  test_html_renderer.py  Тесты production рендера
  test_layout_engine.py  Тесты layout engine
conductor/             Conductor-инфраструктура для AI-агентов
  tracks.md            Реестр треков
  tracks/              Треки (spec + plan + metadata)
data/                  Runtime-данные (не коммитится)
```

## Тестирование

```bash
# Все тесты
pytest tests/

# Только экспериментальный рендер
pytest tests/test_experimental_carousel_renderer.py -v

# Только flow-structure
pytest tests/test_flow_structure.py -v
```

## Инструкция для AI-агентов

Проект использует **Conductor-методологию** (см. `conductor/`). Если вы AI-агент, читайте:

1. `conductor/index.md` — оглавление.
2. `conductor/product.md` — что и зачем.
3. `conductor/tech-stack.md` — стек.
4. `conductor/workflow.md` — как работать с проектом (включая deploy).
5. `conductor/tracks.md` — какие треки есть и в каком статусе.

Ключевые правила:

- **Не коммить `.env`**, `data/`, `bot.log`, `bot_database.db`.
- **Deploy требует `docker compose down bot && docker compose up -d --build`** — `restart` не подхватывает изменения кода (см. `conductor/workflow.md`).
- **Не трогать `services/html_renderer.py` и `tests/test_html_renderer.py`** — там незакоммиченный readability-fix.
- **Новые рендеры** — в `services/`, синхронные, обёрнутые в `asyncio.to_thread(...)`.
- **Тесты** — `unittest`, AST-тесты в `test_flow_structure.py`.

## Безопасность

- `.env` в `.gitignore` — токены не коммитятся.
- `data/` в `.gitignore` — SQLite и export-пакеты не коммитятся.
- `bot.log` в `.gitignore`.
- Все секреты читаются из `os.getenv()` в `config.py`.
- В коде нет хардкоженных токенов.

## Лицензия

MIT. См. файл `LICENSE`.
