import os
import logging
import asyncio
import tempfile
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from groq import Groq
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["8743537257:AAFwawE4QnJVCtTzz6DROruiS1NNU8vYhCw"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

groq_client = Groq(api_key=GROQ_API_KEY)


# ── Health check server (keeps Render alive) ──────────────────────────────────

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, *args):
        pass  # Silence access logs


def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Health server running on port {port}")
    server.serve_forever()


# ── Transcription ─────────────────────────────────────────────────────────────

def transcribe_sync(file_path: str) -> str:
    with open(file_path, "rb") as audio_file:
        transcription = groq_client.audio.transcriptions.create(
            file=(os.path.basename(file_path), audio_file),
            model="whisper-large-v3-turbo",
            response_format="text",
            language="ru",
        )
    return transcription.strip()


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

        text = await asyncio.get_event_loop().run_in_executor(
            None, lambda: transcribe_sync(tmp_path)
        )

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

def main():
    # Start health server in background thread
    thread = threading.Thread(target=run_health_server, daemon=True)
    thread.start()

    # Start Telegram bot
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_voice))

    logger.info("Bot started!")
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
