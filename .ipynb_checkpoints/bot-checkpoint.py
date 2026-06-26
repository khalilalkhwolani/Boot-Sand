from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "8745464463:AAHBkzZ2weBtrOnvBkNOZS_AwJDv02CbB3Q"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك! البوت يعمل بنجاح ✅")

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))

app.run_polling()