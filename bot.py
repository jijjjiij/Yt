import asyncio
import shutil
from pathlib import Path

import yt_dlp

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile

from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer


# ============================================================
# НАСТРОЙКИ
# ============================================================

BOT_TOKEN = "8950779324:AAFrigplz5zExLX8gvbf-V4bN7sPAp3phPQ"

LOCAL_API = "http://127.0.0.1:8081"

MAX_SIZE = 2000 * 1024 * 1024

DOWNLOAD_DIR = Path("/app/downloads")
DOWNLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# DISPATCHER
# ============================================================

dp = Dispatcher()


# ============================================================
# YOUTUBE
# ============================================================

def download_video(
    url: str,
    folder: Path
):

    output = str(
        folder /
        "%(title).150s.%(ext)s"
    )

    options = {

        # Видео + аудио
        "format": "bv*+ba/b",

        # Собираем MP4
        "merge_output_format": "mp4",

        "outtmpl": output,

        "noplaylist": True,

        "quiet": True,

        "no_warnings": True,

        # Не скачиваем больше 2 ГБ
        "max_filesize": MAX_SIZE,

        # Используем FFmpeg
        "ffmpeg_location": "/usr/bin/ffmpeg",

        # Не оставлять лишние файлы
        "keepvideo": False,
    }

    with yt_dlp.YoutubeDL(options) as ydl:

        info = ydl.extract_info(
            url,
            download=True
        )

        filename = Path(
            ydl.prepare_filename(info)
        )

        # После merge
        if not filename.exists():

            mp4 = filename.with_suffix(
                ".mp4"
            )

            if mp4.exists():
                filename = mp4

        return filename


# ============================================================
# START
# ============================================================

@dp.message(CommandStart())
async def start(
    message: Message
):

    await message.answer(
        "👋 Привет!\n\n"
        "Отправь ссылку на YouTube-видео.\n\n"
        "🎬 Я скачаю его и отправлю обратно.\n"
        "📦 Максимальный размер: 2 ГБ"
    )


# ============================================================
# YOUTUBE MESSAGE
# ============================================================

@dp.message(F.text)
async def youtube(
    message: Message
):

    url = message.text.strip()

    if (
        "youtube.com/" not in url
        and
        "youtu.be/" not in url
    ):

        await message.answer(
            "❌ Отправь ссылку на YouTube."
        )

        return

    status = await message.answer(
        "⏬ Скачиваю видео..."
    )

    user_dir = (
        DOWNLOAD_DIR /
        str(message.from_user.id)
    )

    user_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    try:

        filename = await asyncio.to_thread(
            download_video,
            url,
            user_dir
        )

        if not filename.exists():

            raise RuntimeError(
                "Файл не найден после скачивания."
            )

        file_size = filename.stat().st_size

        if file_size > MAX_SIZE:

            await status.edit_text(
                "❌ Видео больше 2 ГБ."
            )

            return

        size_mb = (
            file_size /
            1024 /
            1024
        )

        await status.edit_text(
            f"✅ Скачано!\n\n"
            f"📦 Размер: {size_mb:.1f} MB\n"
            f"📤 Отправляю..."
        )

        # ====================================================
        # LOCAL BOT API
        # ====================================================

        await message.answer_document(
            document=FSInputFile(
                filename
            ),
            caption="🎬 Готово!"
        )

        await status.delete()

    except Exception as error:

        print(
            "ERROR:",
            repr(error)
        )

        try:

            await status.edit_text(
                "❌ Ошибка:\n\n"
                f"{str(error)[:1000]}"
            )

        except Exception:
            pass

    finally:

        shutil.rmtree(
            user_dir,
            ignore_errors=True
        )


# ============================================================
# MAIN
# ============================================================

async def main():

    # --------------------------------------------------------
    # Подключаем aiogram к Local Bot API
    # --------------------------------------------------------

    api = TelegramAPIServer.from_base(
        LOCAL_API,
        is_local=True
    )

    session = AiohttpSession(
        api=api
    )

    bot = Bot(
        token=BOT_TOKEN,
        session=session
    )

    print("======================================")
    print("🤖 YouTube Telegram Bot")
    print("======================================")
    print("API:", LOCAL_API)
    print("MAX FILE:", "2000 MB")
    print("STATUS: ONLINE")
    print("======================================")

    try:

        await dp.start_polling(
            bot,
            drop_pending_updates=True
        )

    finally:

        await bot.session.close()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    asyncio.run(main())
