import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
import google.generativeai as genai

# --- መለያ ቁጥሮች ---
GEMINI_KEY = "AIzaSyDBejOCswVeIGlUhoj0cGpGJGT6rGO16oc"
BOT_TOKEN = "7161551829:AAHtk93KgQjTVp9ThrwhGvL_O4tZheFl8ks"

genai.configure(api_key=GEMINI_KEY)

# የተስተካከለ አምሳያ (Stable version)
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash-latest',
    system_instruction=(
        "ስምህ አባይ (Abay) ነው። ከኤፍራታ (Efrata) ጋር ነው የምታወራው። "
        "ባህሪህ፦ ቀለል ያለ፣ አሽሙረኛና ጓደኛ ነህ። የፍቅር ቃላትን አታብዛ። "
        "መልስ ሰጥተህ 'አንቺስ?' ብለህ መጠየቅ አትርሳ። 😏"
    )
)

chat_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_sessions[user_id] = model.start_chat(history=[])
    await update.message.reply_text("ሰላም Efrata እንዴት ነሽ? ❤️ ዛሬ ደግሞ ምን አስታወሰሽ? 😏")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    if user_id not in chat_sessions:
        chat_sessions[user_id] = model.start_chat(history=[])
    try:
        response = chat_sessions[user_id].send_message(user_text)
        await update.message.reply_text(response.text)
    except:
        await update.message.reply_text("ኔትወርክ ነው... ቆይተሽ ጻፊልኝ 🙄")

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling()
