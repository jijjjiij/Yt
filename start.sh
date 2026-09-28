#!/bin/bash
set -e

echo "🚀 Starting..."

# Python packages
pip install --no-cache-dir -U \
    aiogram \
    yt-dlp

# FFmpeg
apt-get update
apt-get install -y ffmpeg

# Запускаем Local Bot API Server
docker run \
    --rm \
    --name telegram-bot-api \
    -p 8081:8081 \
    aiogram/telegram-bot-api:latest &

echo "⏳ Waiting for Local Bot API..."

sleep 5

echo "🤖 Starting bot..."

python bot.py
