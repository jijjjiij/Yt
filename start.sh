#!/bin/bash
set -e

echo "🚀 Starting bot..."

# Устанавливаем FFmpeg
apt-get update
apt-get install -y ffmpeg

# Python зависимости
pip install --no-cache-dir -U \
    aiogram \
    yt-dlp \
    aiohttp \
    python-dotenv

echo "✅ Dependencies installed"

# Запускаем бота
python bot.py
