import asyncio
import random
import time
import shutil
from pathlib import Path
import subprocess

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, ContextTypes, CommandHandler, CallbackQueryHandler, filters
from shazamio import Shazam
import yt_dlp

# توکن ربات
BOT_TOKEN = "8036840604:AAG1G6gErDt48JeBno1-aV0c57xxcLQLKqw"

# پوشه موقت دانلودها
TMP_DIR = Path("downloads")
TMP_DIR.mkdir(exist_ok=True)

# چنل‌ها برای بررسی عضویت
CHANNELS = ["@star_spotify", "@play_listnika"]

# استخراج صدا از ویدیو
def extract_audio(video_path: Path) -> Path:
    audio_path = TMP_DIR / f"clip_{int(time.time())}_{random.randint(1000,9999)}.wav"
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-t", "12",
        "-ac", "1",
        "-ar", "44100",
        str(audio_path)
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return audio_path

# دانلود MP3
def download_mp3(query: str) -> Path:
    TMP_DIR.mkdir(exist_ok=True)
    timestamp = int(time.time())
    rand = random.randint(1000, 9999)
    out_path = TMP_DIR / f"song_{timestamp}_{rand}.%(ext)s"

    if not query.startswith("http"):
        query = f"ytsearch1:{query}"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(out_path),
        "quiet": True,
        "noplaylist": True,
        "concurrent_fragment_downloads": 10,
        "fragment_retries": 3,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=True)
        filename = ydl.prepare_filename(info)
        mp3_file = Path(filename).with_suffix(".mp3")

    return mp3_file

# بررسی عضویت در همه چنل‌ها
async def is_member_all(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        for channel in CHANNELS:
            member = await context.bot.get_chat_member(channel, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        return True
    except Exception:
        return False

# هندل /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await is_member_all(user_id, context):
        keyboard = [[InlineKeyboardButton("🎵 شناسایی آهنگ", callback_data="identify")]]
        await update.message.reply_text(
            "✅ شما عضو چنل‌ها هستید! برای شناسایی آهنگ روی دکمه زیر بزنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        keyboard = [
            [InlineKeyboardButton("📌 عضویت در star_spotify", url="https://t.me/star_spotify")],
            [InlineKeyboardButton("📌 عضویت در play_listnika", url="https://t.me/play_listnika")]
        ]
        await update.message.reply_text(
            "👋 سلام! برای استفاده از ربات و شناسایی آهنگ‌ها، لطفاً ابتدا عضو هر دو چنل شوید 🎵",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# هندل دکمه‌ها
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "identify":
        await query.message.reply_text("🎬 لطفاً ویدیوی مورد نظر را ارسال کنید تا آهنگ شناسایی شود.")

# هندل ویدیو
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user_id = update.effective_user.id

    if not await is_member_all(user_id, context):
        keyboard = [
            [InlineKeyboardButton("📌 عضویت در star_spotify", url="https://t.me/star_spotify")],
            [InlineKeyboardButton("📌 عضویت در play_listnika", url="https://t.me/play_listnika")]
        ]
        await msg.reply_text(
            "⚠️ شما عضو چنل‌ها نیستید! لطفاً ابتدا روی دکمه‌ها بزن و وارد چنل‌ها شوید 👇",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    file = await msg.video.get_file()
    video_path = TMP_DIR / f"video_{msg.video.file_unique_id}.mp4"
    await file.download_to_drive(video_path)
    await msg.reply_text("✅ ویدیو دریافت شد!")

    # استخراج کوتاه صدا برای شناسایی
    audio_path = extract_audio(video_path)
    shazam = Shazam()
    result = await shazam.recognize(str(audio_path))

    if "track" in result:
        track = result["track"]
        title = track.get("title", "نامشخص")
        artist = track.get("subtitle", "نامشخص")

        try:
            progress_msg = await msg.reply_text("🎧 در حال دانلود آهنگ... 0%")
            # دانلود MP3 به صورت async با نمایش پیشرفت
            mp3_path = await asyncio.to_thread(download_mp3, f"{title} {artist}")

            await progress_msg.edit_text("🎧 در حال دانلود آهنگ... 100%")
            await msg.reply_audio(audio=open(mp3_path, "rb"), title=title, performer=artist)

            # پاکسازی پوشه دانلود
            shutil.rmtree(TMP_DIR)
            TMP_DIR.mkdir(exist_ok=True)

        except Exception as e:
            await msg.reply_text(f"❌ خطا در دانلود MP3: {e}")
    else:
        await msg.reply_text("❌ نتونستم آهنگ رو پیدا کنم.")

# اجرای ربات
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))

    print("🚀 ربات اجرا شد...")
    app.run_polling()

if __name__ == "__main__":
    main()
