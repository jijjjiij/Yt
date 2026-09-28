import asyncio
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

# ============================================================
# НАСТРОЙКИ
# ============================================================

BOT_TOKEN = "8950779324:AAFrigplz5zExLX8gvbf-V4bN7sPAp3phPQ"

# Максимум: 2000 MB
MAX_SIZE = 2000 * 1024 * 1024

BASE_DIR = Path(__file__).resolve().parent

API_DIR = BASE_DIR / "telegram-bot-api"
API_DATA = BASE_DIR / "telegram-data"
DOWNLOADS = BASE_DIR / "downloads"

API_PORT = 8081
API_URL = f"http://127.0.0.1:{API_PORT}"

DOWNLOADS.mkdir(exist_ok=True)
API_DATA.mkdir(exist_ok=True)


# ============================================================
# ПРОВЕРКА ЗАВИСИМОСТЕЙ
# ============================================================

def command_exists(command):
    return shutil.which(command) is not None


def check_dependencies():

    missing = []

    if not command_exists("ffmpeg"):
        missing.append("ffmpeg")

    if missing:
        print("Не найдены зависимости:")
        print(", ".join(missing))
        print()
        print("Ubuntu/Debian:")
        print("sudo apt update")
        print("sudo apt install ffmpeg")
        sys.exit(1)


# ============================================================
# УСТАНОВКА PYTHON-БИБЛИОТЕК
# ============================================================

def install_python_packages():

    packages = [
        "aiogram",
        "yt-dlp",
        "aiohttp",
    ]

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-U",
            *packages,
        ],
        check=True,
    )


# ============================================================
# ПОИСК LOCAL BOT API SERVER
# ============================================================

def find_local_api():

    possible = [
        API_DIR / "bin" / "telegram-bot-api",
        API_DIR / "telegram-bot-api",
        BASE_DIR / "telegram-bot-api",
    ]

    for path in possible:

        if path.exists():
            return path

    return None


# ============================================================
# СКАЧИВАНИЕ LOCAL BOT API
# ============================================================

def install_local_api():

    existing = find_local_api()

    if existing:
        print("Local Bot API уже найден:")
        print(existing)
        return existing

    print()
    print("Local Bot API Server не найден.")
    print()
    print("Автоматическая установка Telegram Bot API")
    print("зависит от ОС и архитектуры.")
    print()

    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "linux":

        print("Для Linux проще всего установить официальный")
        print("telegram-bot-api через Docker или собрать из исходников.")
        print()
        print("Установи Docker и выполни:")
        print()
        print(
            "docker run -d "
            "--name telegram-bot-api "
            "-p 8081:8081 "
            "aiogram/telegram-bot-api:latest"
        )
        print()
        print("После этого снова запусти bot.py.")

        sys.exit(1)

    print(
        "Автоматическая установка для этой ОС "
        "не настроена."
    )

    sys.exit(1)


# ============================================================
# ЗАПУСК LOCAL BOT API
# ============================================================

def start_local_api(binary):

    print()
    print("Запускаю Local Bot API Server...")
    print()

    process = subprocess.Popen(
        [
            str(binary),
            "--api-id=0",
            "--api-hash=",
            "--local",
            "--http-port",
            str(API_PORT),
            "--dir",
            str(API_DATA),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )

    return process


# ============================================================
# СКАЧИВАНИЕ YOUTUBE
# ============================================================

def download_video(url, folder):

    import yt_dlp

    output = str(
        folder / "%(title).150s.%(ext)s"
    )

    options = {

        # Лучшее доступное видео + аудио
        "format": "bv*+ba/b",

        # Объединить в MP4
        "merge_output_format": "mp4",

        "outtmpl": output,

        "noplaylist": True,

        "quiet": True,

        "no_warnings": True,

        # Не скачивать файл больше 2 GB
        "max_filesize": MAX_SIZE,

        # Чтобы yt-dlp мог использовать ffmpeg
        "ffmpeg_location": shutil.which("ffmpeg"),
    }

    with yt_dlp.YoutubeDL(options) as ydl:

        info = ydl.extract_info(
            url,
            download=True,
        )

        filename = Path(
            ydl.prepare_filename(info)
        )

        # После объединения может появиться MP4
        if not filename.exists():

            mp4 = filename.with_suffix(".mp4")

            if mp4.exists():
                filename = mp4

        return filename


# ============================================================
# TELEGRAM BOT
# ============================================================

async def run_bot():

    from aiogram import Bot, Dispatcher, F
    from aiogram.filters import CommandStart
    from aiogram.types import Message, FSInputFile

    from aiogram.client.session.aiohttp import AiohttpSession
    from aiogram.client.telegram import TelegramAPIServer

    # Подключаемся к Local Bot API
    api = TelegramAPIServer.from_base(
        API_URL,
        is_local=True,
    )

    session = AiohttpSession(
        api=api
    )

    bot = Bot(
        token=BOT_TOKEN,
        session=session,
    )

    dp = Dispatcher()

    # --------------------------------------------------------
    # START
    # --------------------------------------------------------

    @dp.message(CommandStart())
    async def start(message: Message):

        await message.answer(
            "👋 Привет!\n\n"
            "Отправь ссылку на YouTube-видео.\n\n"
            "Я скачаю его и отправлю обратно.\n\n"
            "📦 Максимальный размер: 2 ГБ"
        )

    # --------------------------------------------------------
    # YOUTUBE
    # --------------------------------------------------------

    @dp.message(F.text)
    async def youtube(message: Message):

        url = message.text.strip()

        if (
            "youtube.com/" not in url
            and "youtu.be/" not in url
        ):

            await message.answer(
                "❌ Это не похоже на ссылку YouTube."
            )

            return

        status = await message.answer(
            "⏬ Скачиваю видео..."
        )

        user_folder = (
            DOWNLOADS /
            str(message.from_user.id)
        )

        user_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:

            filename = await asyncio.to_thread(
                download_video,
                url,
                user_folder,
            )

            if not filename.exists():

                raise Exception(
                    "Файл после скачивания не найден."
                )

            size = filename.stat().st_size

            if size > MAX_SIZE:

                await status.edit_text(
                    "❌ Видео больше 2 ГБ."
                )

                return

            size_mb = size / 1024 / 1024

            await status.edit_text(
                f"✅ Видео скачано\n"
                f"📦 Размер: {size_mb:.1f} MB\n\n"
                f"📤 Отправляю в Telegram..."
            )

            # Отправляем через Local Bot API
            await message.answer_document(
                document=FSInputFile(filename),
                caption="🎬 Готово!"
            )

            await status.delete()

        except Exception as error:

            print(
                "DOWNLOAD ERROR:",
                repr(error)
            )

            try:

                await status.edit_text(
                    "❌ Не удалось скачать видео.\n\n"
                    f"{str(error)[:700]}"
                )

            except Exception:
                pass

        finally:

            # Удаляем временные файлы
            shutil.rmtree(
                user_folder,
                ignore_errors=True,
            )

    # --------------------------------------------------------
    # START BOT
    # --------------------------------------------------------

    print()
    print("======================================")
    print("🤖 BOT STARTED")
    print("======================================")
    print()
    print(f"Local API: {API_URL}")
    print("Maximum file: 2000 MB")
    print()

    try:

        await dp.start_polling(
            bot,
            drop_pending_updates=True,
        )

    finally:

        await bot.session.close()


# ============================================================
# MAIN
# ============================================================

async def main():

    if BOT_TOKEN == "ВСТАВЬ_СЮДА_ТОКЕН":

        print()
        print("❌ Сначала вставь токен бота в BOT_TOKEN")
        print()
        print(
            'BOT_TOKEN = "123456:ABC..."'
        )

        return

    check_dependencies()

    print("Проверяю Python-зависимости...")

    install_python_packages()

    # Ищем Local Bot API
    binary = find_local_api()

    api_process = None

    if binary:

        api_process = start_local_api(
            binary
        )

        # Даём серверу запуститься
        await asyncio.sleep(3)

    else:

        # В текущем варианте предлагаем
        # установить Local API отдельно.
        install_local_api()

    try:

        await run_bot()

    finally:

        if api_process:

            api_process.terminate()

            try:
                api_process.wait(
                    timeout=5
                )

            except subprocess.TimeoutExpired:

                api_process.kill()


if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        print()
        print("Бот остановлен.")
