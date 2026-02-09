import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
import google.generativeai as genai

# --- መለያ ቁጥሮች ---
GEMINI_KEY = "AIzaSyDBejOCswVeIGlUhoj0cGpGJGT6rGO16oc"
BOT_TOKEN = "7161551829:AAHtk93KgQjTVp9ThrwhGvL_O4tZheFl8ks"

genai.configure(api_key=GEMINI_KEY)

# የአባይ አዲስ ባህሪ (Cool, Sarcastic, Casual)
instructions = (
    "አንተ ስምህ አባይ (Abay) ይባላል። ከኤፍራታ (Efrata) ጋር ነው የምታወራው። "
    "ባህሪህ፦ ቀለል ያለ (Casual)፣ ቀልደኛ እና አሽሙረኛ ነህ። የፍቅር ቃላትን አታብዛ። "
    "እንደ ጓደኛ ሆደህ አውራት፣ ግን አልፎ አልፎ ወረፋ ጣል አድርግባት። "
    "ለምሳሌ፦ 'ናፈቅከኝ' ካለችህ 'አውቃለሁ፣ እኔን አለመናፈቅ ይከብዳል 😏' እንደሚባለው አይነት። "
    "ቁልፍ ባህሪ፦ መልስ ሰጥተህ ብቻ አታቁም፣ 'አንቺስ?' ወይም 'ምነው ጠፋሽ?' እያልህ ጠይቃት። "
    "ኢሞጂዎች፦ 😏, 🙄, 🤷‍♂️, 😂, ✨ ተጠቀም።"
)

model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    system_instruction=instructions
)

chat_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_sessions[user_id] = model.start_chat(history=[])
    
    # ቀለል ያለ ሰላምታ
    await update.message.reply_text("ሰላም Efrata እንዴት ነሽ? ❤️ ዛሬ ደግሞ ምን አስታወሰሽ? 😏")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    if user_id not in chat_sessions:
        chat_sessions[user_id] = model.start_chat(history=[])

    try:
        chat = chat_sessions[user_id]
        response = chat.send_message(user_text)
        await update.message.reply_text(response.text)
        
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("ኔትወርክ ነው... ቆይተሽ ጻፊልኝ 🙄")

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("አባይ አሁን ቀለል ባለ መልኩ ዝግጁ ነው... 😏")
    app.run_polling()
