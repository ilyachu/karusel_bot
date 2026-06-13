FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m playwright install --with-deps chromium

RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
COPY --chown=botuser:botuser . .

USER botuser

CMD ["python", "main.py"]
