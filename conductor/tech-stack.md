# Tech Stack — karusel_bot

## Language & Runtime

- **Python 3.12** (Dockerfile: `FROM python:3.12-slim`)

## Web / Bot Framework

- **aiogram 3.27.0** — Telegram bot framework, async, FSM-based handlers
- Router-based handler organization under `handlers/`
- Middlewares under `middlewares/`

## Persistence

- **SQLite** via stdlib `sqlite3` — used by `utils/database.py` for export packages, users, allowed-list
- File system export packages under `EXPORTS_DIR` (PNG slides + caption.txt + metadata.json)

## Image Rendering

- **Pillow 12.2.0** — primary fallback renderer and image utility
- **playwright 1.58.0** — Chromium-based HTML→PNG rendering, used by `services/html_renderer.py`
- Chromium is pre-installed in Docker image (`/home/botuser/.cache/ms-playwright`)

## External Services

- **OpenAI API** (OpenAI 2.32.0 SDK) — text/voice generation
- **fal-client 0.13.2** — image generation provider
- Telegram Bot API via aiogram
- Instagram Graph API — publishing
- Threads API — publishing

## Architecture Patterns

- Layered:
  - `handlers/` — Telegram interaction (aiogram routers)
  - `services/` — business logic and external integrations
  - `utils/` — cross-cutting helpers (DB, states, middleware helpers)
- Async handlers; sync rendering wrapped in `asyncio.to_thread(...)`
- Production text-planning pipeline uses LLM (`services/gemini_client.py`); layout specs are deterministic (`services/layout_engine.py`)

## Testing

- **unittest** framework (run via `pytest tests/`)
- Tests live in `tests/test_*.py` and are AST-based or behavior-based
- No Playwright required for unit tests — HTML is asserted as string

## Deployment

- Docker Compose (see `docker-compose.yml`)
- Production: `root@<SERVER_IP>` at `/root/karusel_bot_v2`
- Container: `karusel_bot_new`
- All shell commands in this repo use the `rtk` prefix
