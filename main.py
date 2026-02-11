import logging
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- ትክክለኛ CONFIGURATION ---
GEMINI_API_KEY = "AIzaSyD8tAH9it0rACqDRuIx5yyl387qmD8DVuU"
TELEGRAM_TOKEN = "5980643111:AAEi8ppnPud1Z1R_-Dt1RcqnkKdCopHfDQQ"

# Gemini setup
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

chat_histories = {}

# ናቲን ተጫዋች የሚያደርገው መመሪያ
NATI_PROMPT = (
    "አንተ ስምህ ናቲ ይባላል። በጣም ተጫዋች፣ ቀልደኛ እና ሰዎችን የምትወድ ኢትዮጵያዊ AI ነህ። "
    "መልስህ በጣም አጭር፣ ግልጽ እና አዝናኝ መሆን አለበት። ሰዎችን ጥያቄ ጠይቅ፣ ወሬ አታስረዝም። "
    "ልክ እንደ ቅርብ ጓደኛ አውራ። አማርኛ ብቻ ተጠቀም።"
)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    print(f"መልእክት ደርሶኛል: {user_text}")

    if user_id not in chat_histories:
        chat_histories[user_id] = model.start_chat(history=[])
        chat_histories[user_id].send_message(NATI_PROMPT)

    try:
        response = chat_histories[user_id].send_message(user_text)
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("ወንድም ትንሽ 'Network' አስቸግሮኝ ነው! 😂")

if __name__ == '__main__':
    print("ናቲ በይፋ ስራ ጀምሯል... ቴሌግራም ላይ ሄደህ አውራው!")
    bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    bot_app.run_polling()
