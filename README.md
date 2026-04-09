# Telegram Carousel Bot

This bot generates image carousels for Telegram/Instagram from text, voice, or forwarded messages.
It uses Gemini for text analysis, OpenAI Whisper for speech recognition, and Fal.ai for background generation.
It also includes an `Insta Auto` mode that generates an Instagram-ready carousel, caption, and export package with minimal interaction.

## Setup

1.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
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
