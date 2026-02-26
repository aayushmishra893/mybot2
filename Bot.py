import os
import random
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ================= CONFIG =================

TOKEN = os.getenv("bot_token")
OWNER_ID = 6020796284  # Your Telegram ID

# ================= DATABASE =================

conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS videos (file_id TEXT PRIMARY KEY)")
conn.commit()

cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (OWNER_ID,))
conn.commit()

user_last_message = {}

# ================= UTIL =================

def is_admin(user_id):
    cursor.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

def add_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

def get_random_video():
    cursor.execute("SELECT file_id FROM videos")
    videos = cursor.fetchall()
    if not videos:
        return None
    return random.choice(videos)[0]

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)

    keyboard = [
        [InlineKeyboardButton("🎬 Watch Videos", callback_data="watch")],
        [InlineKeyboardButton("ℹ️ About", callback_data="about")],
        [InlineKeyboardButton("📞 Support", callback_data="support")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(
            "Welcome to Professional Video Bot 🚀",
            reply_markup=reply_markup
        )
    else:
        await update.callback_query.message.reply_text(
            "Welcome Back 🚀",
            reply_markup=reply_markup
        )

# ================= ADMIN PANEL =================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    keyboard = [
        [InlineKeyboardButton("➕ Add Video", callback_data="add_video")],
        [InlineKeyboardButton("📂 Total Videos", callback_data="total_videos")],
        [InlineKeyboardButton("👥 Total Users", callback_data="total_users")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("➕ Add Admin", callback_data="add_admin")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👑 Admin Panel", reply_markup=reply_markup)

# ================= VIDEO SENDER =================

async def send_video(chat_id, user_id, context):
    video = get_random_video()

    if not video:
        await context.bot.send_message(chat_id, "No videos available.")
        return

    if user_id in user_last_message:
        try:
            await context.bot.delete_message(chat_id, user_last_message[user_id])
        except:
            pass

    sent = await context.bot.send_video(
        chat_id=chat_id,
        video=video,
        caption="Enjoy 🎬",
        protect_content=True,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏭ Next", callback_data="next")],
            [InlineKeyboardButton("🏠 Home", callback_data="home")]
        ])
    )

    user_last_message[user_id] = sent.message_id

# ================= BUTTON HANDLER =================

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    chat_id = query.message.chat.id

    if query.data == "watch":
        await send_video(chat_id, user_id, context)

    elif query.data == "next":
        await send_video(chat_id, user_id, context)

    elif query.data == "home":
        await start(update, context)

    elif query.data == "about":
        await context.bot.send_message(chat_id, "This is a professional video bot framework.")

    elif query.data == "support":
        await context.bot.send_message(chat_id, "Contact: @yourusername")

    elif query.data == "add_video":
        await context.bot.send_message(chat_id, "Send MP4 video to upload.")

    elif query.data == "total_videos":
        cursor.execute("SELECT COUNT(*) FROM videos")
        count = cursor.fetchone()[0]
        await context.bot.send_message(chat_id, f"Total Videos: {count}")

    elif query.data == "total_users":
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        await context.bot.send_message(chat_id, f"Total Users: {count}")

    elif query.data == "broadcast":
        context.user_data["broadcast"] = True
        await context.bot.send_message(chat_id, "Send message to broadcast.")

    elif query.data == "add_admin":
        context.user_data["add_admin"] = True
        await context.bot.send_message(chat_id, "Send User ID to add as admin.")

# ================= RECEIVE VIDEO =================

async def receive_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        file_id = update.message.video.file_id
        cursor.execute("INSERT OR IGNORE INTO videos (file_id) VALUES (?)", (file_id,))
        conn.commit()
        await update.message.reply_text("Video Added Permanently ✅")

# ================= RECEIVE TEXT =================

async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if context.user_data.get("broadcast") and is_admin(user_id):
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        for u in users:
            try:
                await context.bot.send_message(u[0], update.message.text)
            except:
                pass
        context.user_data["broadcast"] = False
        await update.message.reply_text("Broadcast Sent ✅")

    elif context.user_data.get("add_admin") and user_id == OWNER_ID:
        try:
            new_admin = int(update.message.text)
            cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (new_admin,))
            conn.commit()
            await update.message.reply_text("Admin Added ✅")
        except:
            await update.message.reply_text("Invalid User ID")
        context.user_data["add_admin"] = False

# ================= MAIN =================

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.VIDEO, receive_video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text))

    print("Bot is running...")
    app.run_polling()
