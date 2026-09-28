FROM python:3.13-slim AS builder

RUN apt-get update && apt-get install -y \
    git \
    cmake \
    g++ \
    make \
    openssl \
    libssl-dev \
    zlib1g-dev \
    gperf \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

RUN git clone --recursive --depth 1 \
    https://github.com/tdlib/telegram-bot-api.git

WORKDIR /build/telegram-bot-api

RUN mkdir build \
    && cd build \
    && cmake -DCMAKE_BUILD_TYPE=Release .. \
    && cmake --build . --target telegram-bot-api -j2


FROM python:3.13-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder \
    /build/telegram-bot-api/build/telegram-bot-api \
    /usr/local/bin/telegram-bot-api

COPY bot.py .
COPY loader.sh .
COPY start.sh .

RUN chmod +x start.sh loader.sh

RUN pip install --no-cache-dir \
    aiogram \
    yt-dlp \
    aiohttp

RUN mkdir -p /app/telegram-data /app/downloads

CMD ["./start.sh"]
