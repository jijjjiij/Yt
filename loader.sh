#!/bin/bash

API_ID="2040"
API_HASH="b18441a1ff607e10a989891a5462e627"

telegram-bot-api \
  --api-id="$API_ID" \
  --api-hash="$API_HASH" \
  --local \
  --http-port=8081 \
  --dir=/app/telegram-data &

echo "Local Bot API Server запускается..."

until curl -s http://127.0.0.1:8081/bot >/dev/null 2>&1; do
    sleep 1
done

echo "Local Bot API Server запущен!"

exec python bot.py
