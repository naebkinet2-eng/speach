import os
import logging
import asyncio
import tempfile
import threading
import httpx
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


# ── Health check server ───────────────────────────────────────────────────────

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, *args):
        pass


def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Health server running on port {port}")
    server.serve_forever()


# ── Transcription via raw HTTP (no Groq SDK) ──────────────────────────────────

def transcribe_sync(file_path: str) -> str:
    with open(file_path, "rb") as f:
        data = f.read()

    filename = os.path.basename(file_path)

    with httpx.Client(timeout=60) as client:
        response = client.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            files={"file": (filename, data)},
            data={
                "model": "whisper-large-v3-turbo",
                "response_format": "text",
                "language": "ru",
            },
        )

    response.raise_for_status()
    return response.text.strip()


# ── Telegram handlers ─────────────────────────────────────────────────────────

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if message.voice:
        file = await message.voice.get_file()
        suffix = ".ogg"
        label = "🎤 Голосовое"
    elif message.video_note:
        file = await message.video_note.get_file()
        suffix = ".mp4"
        label = "🔵 Кружок"
    else:
        return

    await context.bot.send_chat_action(
        chat_id=message.chat_id,
        action=ChatAction.TYPING
    )

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name

        await file.download_to_drive(tmp_path)

        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, transcribe_sync, tmp_path)

        if text:
            await message.reply_text(
                f"{label}:\n\n{text}",
                reply_to_message_id=message.message_id
            )
        else:
            await message.reply_text("❌ Не удалось распознать речь.")

    except Exception as e:
        logger.error(f"Transcription error: {e}")
        await message.reply_text("⚠️ Ошибка при распознавании. Попробуй ещё раз.")
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


# ── Entry point ───────────────────────────────────────────────────────────────

async def run_bot():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_voice))

    logger.info("Bot started!")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=["message"])

    await asyncio.Event().wait()


def main():
    thread = threading.Thread(target=run_health_server, daemon=True)
    thread.start()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_bot())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
