import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
import google.generativeai as genai

# --- መለያ ቁጥሮች (እነዚህን በራስሽ ተኪ) ---
GEMINI_KEY = "AIzaSyDBejOCswVeIGlUhoj0cGpGJGT6rGO16oc"
BOT_TOKEN = "7161551829:AAHatRdHBkcREdfRawR82ltnPF-jIKO50Jo"

# ኔትወርክ እንዳያስቸግር 'rest' ትራንስፖርት እንጠቀማለን
genai.configure(api_key=GEMINI_KEY, transport='rest')

# የአባይ ባህሪ መመሪያ
SYSTEM_PROMPT = (
    "ስምህ አባይ (Abay) ነው። ከኤፍራታ (Efrata) ጋር ነው የምታወራው። "
    "ባህሪህ፦ በጣም ቀለል ያለ፣ አሽሙረኛ፣ ጨዋታ አዋቂ እና የቅርብ ጓደኛ ነህ። "
    "በአማርኛ ብቻ አውራ። የፍቅር ቃላትን አታብዛ፣ በቃላት ወጋ አድርጋት። "
    "መልስ ስትሰጥ ሁልጊዜ 'አንቺስ?' ወይም 'አንቺ ምን ትያለሽ?' ብለህ መጠየቅ አትርሳ። 😏"
)

# የ AI ሞዴል አወቃቀር (ስሙ እዚህ ጋር ተስተካክሏል)
model = genai.GenerativeModel(
    model_name='models/gemini-1.5-flash-latest',
    system_instruction=SYSTEM_PROMPT
)

# የንግግር ታሪክ መያዣ
chat_sessions = {}

# ስህተቶችን ለመከታተል (Logging)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_sessions[user_id] = model.start_chat(history=[])
    welcome_msg = "አቤት ኤፍራታ! መጣሽ ደግሞ? 😏 ዛሬ ምን ላውራሽ ትያለሽ?"
    await update.message.reply_text(welcome_msg)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    if user_id not in chat_sessions:
        chat_sessions[user_id] = model.start_chat(history=[])

    try:
        response = chat_sessions[user_id].send_message(user_text)
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"Error: {e}")
        # ለተጠቃሚው ግልጽ መልስ ለመስጠት
        if "404" in str(e):
            await update.message.reply_text("የሞዴል ስም ስህተት አለ፣ አስተካክዪው! 🙄")
        else:
            await update.message.reply_text("ኔትወርኩ ተደናቅፎብኛል... ትንሽ ቆይተሽ ጻፊልኝ።")

if __name__ == '__main__':
    print("አባይ እየተነሳ ነው... 🚀")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    app.run_polling()
