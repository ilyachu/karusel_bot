# Karusel Bot

Telegram-бот для генерации каруселей из текста, голосовых сообщений и пересланных постов.

Идея проекта: отправить мысль в бот и получить готовую карусель для Telegram / Instagram:

```text
текст -> план слайдов -> тема -> HTML-рендер -> PNG -> caption -> export package
```

Проект сейчас больше похож на рабочий прототип / личный контент-конвейер, чем на законченный SaaS.  
Он уже умеет генерировать карусели, выбирать визуальную тему, рендерить карточки через Playwright и готовить export-пакет под будущую публикацию в Instagram.

## Возможности

- Генерация карусели из обычного текста.
- Генерация карусели из голосового сообщения через OpenAI Whisper.
- Обработка пересланных Telegram-постов.
- Режим `Insta Auto` для быстрого создания Instagram-ready карусели.
- Автовыбор визуальной темы через локальную policy-логику.
- Ручная фиксация темы перед генерацией.
- HTML/CSS-рендер карточек через Playwright.
- Экспорт PNG-слайдов, caption и metadata.
- Подготовка Meta publishing plan без реальной публикации.
- Публикация готовой карусели в Threads через официальный API.
- Админский список разрешённых пользователей.

## Как это работает

В обычном сценарии:

1. Пользователь отправляет текст, голосовое или пересланный пост.
2. Бот анализирует текст через OpenRouter.
3. Бот собирает план карусели.
4. Локальный layout engine выбирает тему и структуру слайдов.
5. HTML renderer рендерит слайды в PNG.
6. Бот отправляет слайды в Telegram.
7. Бот сохраняет export package в `EXPORTS_DIR`.

В `Insta Auto`:

1. Нажмите `🚀 Insta Auto`.
2. Оставьте тему в `Auto` или зафиксируйте вручную.
3. Отправьте текст.
4. Получите карусель, caption и export package.

## Визуальные темы

Сейчас в проекте есть несколько тем:

- `memory_archive` — светлая редакционная тема для памяти, заметок, knowledge posts.
- `research_mono` — светлая аналитическая тема для research/tool/framework posts.
- `founder_brief` — спокойная светлая тема для founder/product/strategy posts.
- `growth_black` — тёмная контрастная тема для growth/marketing/performance posts.

Важно: `creator_bold` не используется в Auto-режиме, потому что для новостных и инструментальных постов он часто выглядел слишком шумно. Его можно вернуть только как явный ручной режим, если понадобится.

## Что нужно для работы

Минимально:

- Python 3.12+
- Telegram Bot Token
- OpenRouter API key
- OpenAI API key
- Fal.ai key
- Playwright Chromium

OpenAI нужен для:

- Whisper transcription
- fallback текстовой генерации

OpenRouter нужен для:

- планирования карусели
- генерации слайдов
- генерации caption

Fal.ai сейчас используется для AI-фонов в ручных режимах.

## Установка локально

```bash
git clone https://github.com/ilyachu/karusel_bot.git
cd karusel_bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
```

Заполните `.env`.

```bash
python main.py
```

## Установка через Docker

```bash
git clone https://github.com/ilyachu/karusel_bot.git
cd karusel_bot
cp .env.example .env
```

Заполните `.env`, затем:

```bash
docker compose up -d --build
```

Логи:

```bash
docker compose logs -f
```

Остановка:

```bash
docker compose down
```

## Переменные окружения

Пример находится в `.env.example`.

```env
TELEGRAM_BOT_TOKEN=
OPENAI_API_KEY=
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=google/gemini-3.1-flash-lite-preview
FAL_KEY=
ADMIN_ID=
DATA_DIR=data
EXPORTS_DIR=data/exports
EXPORT_PUBLIC_BASE_URL=
INSTAGRAM_ACCESS_TOKEN=
INSTAGRAM_USER_ID=
INSTAGRAM_API_BASE=https://graph.instagram.com/v22.0
INSTAGRAM_MEDIA_PROXY_BASE_URL=https://meta.chuchuchu.online
INSTAGRAM_MEDIA_PROXY_SECRET=
INSTAGRAM_MEDIA_PROXY_TTL_SECONDS=300
INSTAGRAM_MEDIA_PROXY_BOT_ALIAS=KARUSEL
META_APP_ID=
META_APP_SECRET=
META_REDIRECT_URI=
META_GRAPH_HOST=graph.instagram.com
META_GRAPH_API_VERSION=v24.0
META_WEBHOOK_CALLBACK_URL=
META_WEBHOOK_VERIFY_TOKEN=
META_DEAUTH_CALLBACK_URL=
META_DATA_DELETION_REQUEST_URL=
```

### Основные переменные

- `TELEGRAM_BOT_TOKEN` — токен бота из BotFather.
- `ADMIN_ID` — Telegram ID администратора.
- `OPENROUTER_API_KEY` — ключ OpenRouter.
- `OPENROUTER_MODEL` — модель для текста.
- `OPENAI_API_KEY` — ключ OpenAI для Whisper и fallback.
- `FAL_KEY` — ключ Fal.ai для генерации фонов.
- `DATA_DIR` — папка для SQLite и логов.
- `EXPORTS_DIR` — папка для export-пакетов.
- `EXPORT_PUBLIC_BASE_URL` — публичный URL, по которому будут доступны export-файлы для Meta.
- `INSTAGRAM_ACCESS_TOKEN` — long-lived Instagram access token для аккаунта публикации.
- `INSTAGRAM_USER_ID` — Instagram API user ID аккаунта публикации.
- `INSTAGRAM_API_BASE` — версия Instagram Graph API.
- `INSTAGRAM_MEDIA_PROXY_*` — публичная signed-ссылка на Telegram media proxy для передачи слайдов в Instagram API.

### Meta-переменные

Meta-переменные нужны для подготовки publish plan и app review. Реальная публикация каруселей выполняется через `INSTAGRAM_*` переменные.

- `META_APP_ID`
- `META_APP_SECRET`
- `META_REDIRECT_URI`
- `META_GRAPH_HOST`
- `META_GRAPH_API_VERSION`
- `META_WEBHOOK_CALLBACK_URL`
- `META_WEBHOOK_VERIFY_TOKEN`
- `META_DEAUTH_CALLBACK_URL`
- `META_DATA_DELETION_REQUEST_URL`

Подробнее: `docs/meta-publishing.md`.

## Админ-доступ

Бот закрыт через allowlist.

Администратор задаётся через:

```env
ADMIN_ID=123456789
```

Админ может добавлять пользователей через `/admin`.

Если пользователь не в allowlist, бот ответит:

```text
У вас нет доступа к этому боту.
```

## Экспорт каруселей

`Insta Auto` создаёт export package:

```text
data/exports/<timestamp>-<chat_id>-<slug>/
  slide_01.png
  slide_02.png
  ...
  caption.txt
  metadata.json
```

`metadata.json` содержит:

- `export_id`
- `slides`
- `carousel_plan`
- `layout_specs`
- `theme_decision`
- `render_mode`

Этот export package — граница между генерацией и будущей публикацией.

Из того же export package можно сразу собрать `Threads`-ready export plan и отдать его в отдельный OAuth/publisher сервис.

## Подготовка к Instagram / Meta publishing

Meta требует публичные URL для картинок.

Поэтому перед реальной публикацией нужно:

1. Поднять public hosting для `EXPORTS_DIR`.
2. Задать `EXPORT_PUBLIC_BASE_URL`.
3. Подключить Instagram professional account через Meta.
4. Получить `ig_user_id` и access token.
5. Выполнить publish flow.

Текущий код уже умеет готовить request plan:

- child media containers
- parent carousel container
- media publish request
- polling plan

Файл: `services/meta_publish.py`.

## Структура проекта

```text
handlers/              Telegram flow
services/              генерация, рендер, export, Meta scaffold
utils/                 БД, состояния, сообщения, валидация
assets/                пресеты и шрифты
docs/                  заметки по архитектуре и деплою
tests/                 тесты
data/                  runtime-данные, не коммитится
```

## Полезные команды

Запуск тестов:

```bash
PYTHONPATH=. python -m unittest \
  tests.test_layout_engine \
  tests.test_html_renderer \
  tests.test_renderer \
  tests.test_instagram_package \
  tests.test_export_hosting \
  tests.test_meta_publish \
  test_admin_logic
```

Проверка синтаксиса:

```bash
python -m compileall main.py handlers services utils tests test_admin_logic.py
```

Docker rebuild:

```bash
docker compose up -d --build
```

## Инструкция для Codex / Claude

Если вы хотите попросить Codex или Claude настроить этот проект, можно дать такой промпт:

```text
Ты работаешь с репозиторием karusel_bot.

Задача:
1. Проверить README.md, .env.example, docker-compose.yml и Dockerfile.
2. Создать .env на основе .env.example.
3. Объяснить, какие ключи нужны и где их получить.
4. Установить зависимости.
5. Установить Playwright Chromium.
6. Запустить тесты.
7. Запустить бота локально или через Docker.
8. Проверить, что data/ и .env не попадают в git.

Ограничения:
- не печатай реальные токены в ответах
- не коммить .env
- не трогай data/
- не меняй архитектуру без необходимости
```

Если нужна настройка сервера:

```text
Настрой деплой karusel_bot на сервере.

Требования:
1. Код должен лежать в отдельной папке проекта.
2. .env должен храниться только на сервере.
3. data/ должен быть volume и не перетираться при обновлениях.
4. Бот должен запускаться через docker compose.
5. После деплоя проверь docker compose logs и статус контейнера.
6. Не используй password-based GitHub Actions workflow в публичном репозитории.
7. Если нужен автодеплой, предложи SSH-key based private CI workflow.
```

Если нужна доработка `Insta Auto`:

```text
Доработай режим Insta Auto.

Контекст:
- текстовая генерация идёт через OpenRouter
- fallback через OpenAI
- layout строится через services/layout_engine.py
- HTML-рендер через services/html_renderer.py
- export package создаётся через services/instagram_package.py

Требования:
1. Не добавляй технические подписи на слайды.
2. Не добавляй fake UI-кнопки внутрь картинок.
3. Последний слайд должен быть CTA.
4. Русский исходный текст должен давать русские слайды.
5. Сохраняй export package contract.
6. Покрой изменения тестами.
```

## Текущий статус

Работает:

- генерация каруселей
- `Insta Auto`
- выбор темы
- HTML rendering
- export packages
- Meta publish scaffold

Не завершено:

- реальный Instagram OAuth
- реальный Meta publish execution
- public hosting для export-файлов
- полноценная визуальная QA разных тем

## Безопасность

Не коммитьте:

- `.env`
- токены
- базы SQLite
- логи
- export output

В `.gitignore` уже добавлены:

- `.env`
- `data/`
- `output/`
- `bot.log`
- `bot_database.db`
- `voice_*.ogg`

## Лицензия

Пока лицензия явно не задана. Если планируется публичное использование, добавьте `LICENSE`.
