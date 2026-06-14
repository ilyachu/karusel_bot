FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including Chromium deps
RUN apt-get update && apt-get install -y \
    curl \
    libnss3 libnspr4 libatk1.0-0t64 libatk-bridge2.0-0t64 libcups2t64 \
    libdrm2 libdbus-1-3 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create botuser and install Chromium in its home
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app && \
    su botuser -c "python -m playwright install chromium 2>/dev/null"

ENV HOME=/home/botuser
ENV PLAYWRIGHT_BROWSERS_PATH=/home/botuser/.cache/ms-playwright

USER botuser

CMD ["python", "main.py"]
