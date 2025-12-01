# Telegram Carousel Bot

This bot generates image carousels for Telegram/Instagram from text, voice, or forwarded messages.
It uses Gemini for text analysis, OpenAI Whisper for speech recognition, and Fal.ai for background generation.

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

3.  **Fonts**:
    Optionally place a `.ttf` font at `assets/fonts/font.ttf`.

## Run

```bash
python main.py
```
