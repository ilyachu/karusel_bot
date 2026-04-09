# 🚀 Deployment Instructions

## Prerequisites
1.  **Server**: A VPS (Ubuntu/Debian recommended) with Docker and Docker Compose installed.
2.  **Files**: You need to upload the project files to the server.

## Step 1: Install Docker (if not installed)
```bash
# Update packages
sudo apt update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose (if not included in docker)
# Usually 'docker compose' (v2) is available now.
```

## Step 2: Upload Files
Upload the following files/folders to a folder on your server (e.g., `/opt/karusel_bot`):
- `main.py`
- `config.py`
- `requirements.txt`
- `Dockerfile`
- `docker-compose.yml`
- `handlers/`
- `services/`
- `utils/`
- `middlewares/`
- `assets/` (Make sure fonts are inside `assets/fonts/`)

**Do NOT upload `.env` or `bot_database.db` if you want a fresh start, but you DO need to create a `.env` file on the server.**

## Step 2.5: Prepare Data Directory
Before starting Docker, create the data directory to store the database and logs:
```bash
mkdir data
chmod 777 data
```

## Step 3: Configure Environment
Create a `.env` file on the server in the project folder:
```bash
nano .env
```
Paste your keys:
```env
TELEGRAM_BOT_TOKEN=your_token_here
GEMINI_API_KEY=your_key_here
FAL_KEY=your_key_here
OPENAI_API_KEY=your_key_here
ADMIN_ID=your_telegram_user_id
DATA_DIR=data
EXPORTS_DIR=data/exports
EXPORT_PUBLIC_BASE_URL=https://your-public-host.example/exports
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
Save and exit (`Ctrl+X`, `Y`, `Enter`).

## Step 4: Run the Bot
```bash
# Build and start in background
docker compose up -d --build

# Check logs
docker compose logs -f
```

The Docker image installs Chromium for the rich `Insta Auto` renderer during
build. If you run outside Docker, install it manually:
```bash
python -m playwright install chromium
```

## Maintenance
- **Restart**: `docker compose restart`
- **Stop**: `docker compose down`
- **Update**: Upload new files, then run `docker compose up -d --build` again.

## ⚡️ Docker Cheat Sheet

| Действие | Команда |
| :--- | :--- |
| **Посмотреть логи** (в реальном времени) | `docker compose logs -f` |
| **Посмотреть логи** (последние 100 строк) | `docker compose logs -f --tail=100` |
| **Остановить бота** | `docker compose down` |
| **Запустить/Перезапустить** | `docker compose up -d` |
| **Пересобрать и обновить** (после загрузки новых файлов) | `docker compose up -d --build` |
| **Проверить статус** (работает ли?) | `docker compose ps` |
| **Перезагрузить** (просто рестарт) | `docker compose restart` |
