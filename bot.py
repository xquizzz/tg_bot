import json
import os
from datetime import datetime, timedelta
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, Location
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio

# === Константы ===
TOKEN = "7764142089:AAHWDwtR2SJiCevefbuUeYcDhcl9P44EWt8"
SESSIONS_DIR = "sessions"
PHONE_NUMBER = "+998 90 123 45 67"  # заменишь на свой номер
LOCATION = (41.318036, 69.338983)  # координаты салона

# === Инициализация ===
if not os.path.exists(SESSIONS_DIR):
    os.makedirs(SESSIONS_DIR)

scheduler = BackgroundScheduler()
scheduler.start()

# === Отправка напоминания клиенту ===
async def notify_user(chat_id: int, message: str):
    app = ApplicationBuilder().token(TOKEN).build()
    try:
        await app.bot.send_message(chat_id=chat_id, text=message)
        await app.bot.send_location(chat_id=chat_id, latitude=LOCATION[0], longitude=LOCATION[1])
    except Exception as e:
        print(f"Ошибка отправки клиенту {chat_id}: {e}")

# === Команда /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("📞 Связаться"), KeyboardButton("❌ Отменить сеанс")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Добро пожаловать! Используйте /addsession для записи на сеанс.",
        reply_markup=reply_markup
    )

# === Команда /addsession ===
async def addsession(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args) < 4:
            await update.message.reply_text(
                "❗ Формат: /addsession YYYY-MM-DD HH:MM chat_id Сообщение"
            )
            return

        date_str, time_str, chat_id_str = args[0], args[1], args[2]
        message = " ".join(args[3:])
        chat_id = int(chat_id_str)

        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        notify_time = dt - timedelta(hours=1)

        # Сохранение сеанса
        session_data = {
            "chat_id": chat_id,
            "datetime": dt.strftime("%Y-%m-%d %H:%M"),
            "message": message,
        }

        session_filename = os.path.join(
            SESSIONS_DIR,
            f"session_{dt.strftime('%Y%m%d_%H%M%S')}_{chat_id}.json"
        )
        with open(session_filename, "w") as f:
            json.dump(session_data, f)

        # Планирование напоминания
        scheduler.add_job(
            lambda: asyncio.run(notify_user(chat_id, f"🔔 Напоминание: {message}")),
            trigger="date",
            run_date=notify_time
        )

        await update.message.reply_text(
            f"✅ Сеанс записан. Напоминание придёт за 1 час ({notify_time.strftime('%H:%M')})"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

# === Кнопка "Связаться" ===
async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📞 Наш номер: {PHONE_NUMBER}")

# === Кнопка "Отменить сеанс" ===
async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    removed = 0

    for filename in os.listdir(SESSIONS_DIR):
        path = os.path.join(SESSIONS_DIR, filename)
        with open(path, "r") as f:
            data = json.load(f)
            if data.get("chat_id") == chat_id:
                os.remove(path)
                removed += 1

    if removed > 0:
        await update.message.reply_text("❌ Ваш сеанс(ы) отменён.")
    else:
        await update.message.reply_text("❗ У вас нет активных сеансов.")

# === Запуск бота ===
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addsession", addsession))
    app.add_handler(MessageHandler(filters.Regex("📞 Связаться"), contact_handler))
    app.add_handler(MessageHandler(filters.Regex("❌ Отменить сеанс"), cancel_handler))

    print("Бот запущен ✅")
    app.run_polling()
