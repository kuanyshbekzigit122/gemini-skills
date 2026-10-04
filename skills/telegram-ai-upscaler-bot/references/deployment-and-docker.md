# Production Deployment & Containerization Guide

This document provides deployment blueprints for hosting the AI Upscaler Telegram Bot on Docker, Hugging Face Spaces, or a standard Linux VPS.

---

## 1. Dockerfile Optimization

Super-resolution requires native system packages (`ffmpeg`, `libgl1`, `libgomp1` for OpenMP parallelism). Here is the optimized production `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Avoid prompts from debconf
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root app user
RUN useradd -m -u 1000 appuser
WORKDIR /app

# Install python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code and models
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 7860

CMD ["python", "main.py"]
```

---

## 2. Hugging Face Spaces Deployment

Hugging Face Spaces provides free or low-cost CPU/GPU hosting with Docker:
1. In `README.md`, specify frontmatter metadata:
   ```yaml
   ---
   title: Auphonic AI Upscaler Pro
   emoji: 🚀
   colorFrom: indigo
   colorTo: green
   sdk: docker
   app_port: 7860
   pinned: false
   ---
   ```
2. In `bot/webapp/server.py`, ensure an aiohttp/fastapi health server runs on `0.0.0.0:7860` alongside the Telegram polling loop.
3. Configure `TELEGRAM_BOT_TOKEN` in the Hugging Face Space Settings -> **Repository Secrets**.

---

## 3. Linux VPS (systemd Service)

To run the bot as a persistent daemon with automatic restart on a VPS:

Create `/etc/systemd/system/teleupscaler.service`:
```ini
[Unit]
Description=AI Upscaler Telegram Bot Daemon
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/teleupscaler
ExecStart=/home/ubuntu/teleupscaler/venv/bin/python main.py
Restart=always
RestartSec=5
EnvironmentFile=/home/ubuntu/teleupscaler/.env

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable teleupscaler
sudo systemctl start teleupscaler
sudo journalctl -u teleupscaler -f
```
