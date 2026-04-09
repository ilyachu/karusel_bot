# Telegram Carousel Bot

This bot generates image carousels for Telegram/Instagram from text, voice, or forwarded messages.
It uses Gemini for text analysis, OpenAI Whisper for speech recognition, and Fal.ai for background generation.
It also includes an `Insta Auto` mode that generates an Instagram-ready carousel, caption, and export package with minimal interaction.

## Setup

1.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    Install Chromium for the rich Insta Auto renderer:
    ```bash
    python -m playwright install chromium
    ```

2.  **Environment Variables**:
    Copy `.env.example` to `.env` and fill in your keys:
    ```bash
    cp .env.example .env
    ```
    - `TELEGRAM_BOT_TOKEN`: From @BotFather
    - `GEMINI_API_KEY`: From Google AI Studio
    - `OPENAI_API_KEY`: From OpenAI Platform
    - `FAL_KEY`: From Fal.ai
    - `ADMIN_ID`: Telegram user ID with admin access
    - `DATA_DIR`: optional, defaults to `data`
    - `EXPORTS_DIR`: optional, defaults to `data/exports`
    - `EXPORT_PUBLIC_BASE_URL`: public base URL that serves the export packages
    - `META_*`: optional for now, used to prepare the future Instagram publish layer

3.  **Fonts**:
    Optionally place a `.ttf` font at `assets/fonts/font.ttf`.

## Run

```bash
python main.py
```

The bot stores logs and SQLite data in `DATA_DIR` so runtime artifacts stay out
of the repository.

## Insta Auto

Use the `🚀 Insta Auto` button in Telegram, send source text, and the bot will:
- generate an Instagram-focused carousel automatically
- prepare a caption
- save an export package in `EXPORTS_DIR`
- persist the `carousel plan` and `layout specs` in `metadata.json`
- let you keep `Auto` theme selection or lock the theme before generation

When Playwright/Chromium is available, `Insta Auto` uses the richer HTML/CSS
renderer. If not, it falls back to the Pillow renderer and tells you what to
install.

Theme selection is also filtered through a local policy layer, so the bot does
not rely only on the LLM to decide whether a post should render as
`growth_black`, `research_mono`, `founder_brief`, or `memory_archive`.

## Meta Publishing Prep

The repo now reserves env placeholders for the future Instagram publishing
layer. No real keys are required yet, but the expected config contract is:
- `EXPORT_PUBLIC_BASE_URL`
- `META_APP_ID`
- `META_APP_SECRET`
- `META_REDIRECT_URI`
- `META_GRAPH_HOST`
- `META_GRAPH_API_VERSION`
- `META_WEBHOOK_CALLBACK_URL`
- `META_WEBHOOK_VERIFY_TOKEN`
- `META_DEAUTH_CALLBACK_URL`
- `META_DATA_DELETION_REQUEST_URL`
