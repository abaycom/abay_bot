import os
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# --- 1. መለያ ቁጥሮች (እነዚህን በጥንቃቄ ተኪ) ---
# ማሳሰቢያ፡ ቁልፎቹን በ " " (Quotes) ውስጥ አድርጊያቸው
GEMINI_KEY = "AIzaSyD8tAH9it0rACqDRuIx5yyl387qmD8DVuU"
BOT_TOKEN = "5980643111:AAFWeKd2kRv-1t8NtBZycQYKvYBcwnf5G_s"

# --- 2. Gemini-ን ማስተካከል ---
genai.configure(api_key=GEMINI_KEY)

# ሞዴሉን መጥራት
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 3. ቦቱ መልስ የሚሰጥበት ተግባር ---
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text
    print(f"ኤፍራታ እንዲህ አለች: {user_msg}") # በ VS Code ኮንሶል ላይ ይታያል
    
    try:
        # AI መልስ እንዲሰጥ መጠየቅ
        prompt = f"አንተ አባይ (Abay) የተባልክ የኤፍራታ ጓደኛ ነህ። መልስ ስጥ: {user_msg}"
        response = model.generate_content(prompt)
        
        await update.message.reply_text(response.text)
        
    except Exception as e:
        print(f"ስህተት ተፈጠረ: {e}")
        await update.message.reply_text("አባይ ትንሽ ደክሞታል... 🙄")

# --- 4. ቦቱን ማስነሳት ---
if __name__ == '__main__':
    if GEMINI_KEY == "የአንቺ_API_KEY_እዚህ_ይግባ" or BOT_TOKEN == "የአንቺ_BOT_TOKEN_እዚህ_ይግባ":
        print("ስህተት: እባክሽ መጀመሪያ API Key እና Token አስገቢ!")
    else:
        print("አባይ በ Online VS Code ተነስቷል... 🚀")
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(MessageHandler(filters.TEXT, reply))
        app.run_polling()
