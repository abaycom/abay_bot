import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import google.generativeai as genai

# --- ቁልፎች ---
# Replit ላይ ከሆንክ 'Secrets' (🔒 icon) ውስጥ አስገባቸው
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', 'የእርስዎ_ቶከን')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'የእርስዎ_API_ቁልፍ')

# Gemini ኮንፊገሬሽን
genai.configure(api_key=GEMINI_API_KEY)

# 404ን ለማስወገድ ሞዴሉን በዚህ መልኩ እንጥራው
model = genai.GenerativeModel(
    model_name="models/gemini-1.5-flash"  # 'models/' የሚለውን መጨመር 404ን ይከላከላል
)

# የአባይ ጠባይ
SYSTEM_PROMPT = (
    "አንተ ስምህ አባይ ነው። በጣም ቀልደኛ እና እንደ ሰው የምታወራ ኢትዮጵያዊ ነህ። "
    "ስለ efrata ካልተጠየቅክም በወሬህ መሃል እሷን እያነሳህ አወድሳት። "
    "አነጋገርህ 'ኧረ ተው'፣ 'እንዴ'፣ 'ምነው በናትህ' የሚሉ ቃላትን ይጨምር።"
)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    try:
        # ጥያቄውን ማዘጋጀት
        prompt = f"{SYSTEM_PROMPT}\n\nተጠቃሚው እንዲህ ይላል፦ {user_text}"
        
        # መልስ ማመንጨት
        response = model.generate_content(prompt)
        
        if response.text:
            await update.message.reply_text(response.text)
        else:
            await update.message.reply_text("አባይ ወሬው ጠፋበት! በድጋሚ ጠይቀኝ።")
            
    except Exception as e:
        error_msg = str(e)
        print(f"Error Detail: {error_msg}")
        
        if "404" in error_msg:
            await update.message.reply_text("404 Error: አባይ መኖሪያ ቤቱ አልታወቅ አለ! (Model Not Found)")
        elif "429" in error_msg:
            await update.message.reply_text("አባይ ደከመው፤ ብዙ አወራን። ትንሽ ቆይተን እንቀጥል።")
        else:
            await update.message.reply_text(f"አባይ ችግር ገጠመው፦ {error_msg[:50]}")

if __name__ == '__main__':
    # ሎግ ለማየት
    logging.basicConfig(level=logging.INFO)
    
    try:
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        
        print("አባይ Replit ላይ ስራ ጀምሯል...")
        app.run_polling()
    except Exception as e:
        print(f"Bot failed to start: {e}")
