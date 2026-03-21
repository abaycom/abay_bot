import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from pymongo import MongoClient

# Railway ላይ ስትጭን እነዚህን መረጃዎች በ Variables ውስጥ ማስቀመጥ ይሻላል
# ካልሆነ ግን በቀጥታ እዚህ ጋር መጻፍ ትችላለህ
MONGO_URI = "mongodb+srv://Abaynehgedef_db_user:na3h6U4opccdIfkH@cluster0.mongodb.net/?retryWrites=true&w=majority"
TOKEN = "5980643111:AAEi8ppnPud1Z1R_-Dt1RcqnkKdCopHfDQQ"

# MongoDB Setup
client = MongoClient(MONGO_URI)
db = client['Abaynehgedef_db']
users_collection = db['registered_users']

NAME, AGE, PHONE = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # ዳታው ክላውድ ላይ ስለሆነ ቦቱ ቢጠፋም እዚህ ጋር ያገኘዋል
    if users_collection.find_one({"user_id": user_id}):
        await update.message.reply_text("አንዴ ተመዝግበዋል! መረጃዎ በክላውድ ላይ በሰላም ተቀምጧል። ✅")
        return ConversationHandler.END
    
    await update.message.reply_text("እንኳን ደህና መጡ! ስምዎን ያስገቡ፦")
    return NAME

# ... ሌሎቹ function-ዎች (get_name, get_age, get_phone) ቀጥለው ይገባሉ ...

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = {
        "user_id": update.effective_user.id,
        "name": context.user_data['name'],
        "age": context.user_data['age'],
        "phone": update.message.contact.phone_number
    }
    users_collection.insert_one(user_data)
    await update.message.reply_text("ምዝገባው በክላውድ ዳታቤዝ ላይ ተቀምጧል! ☁️", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    # Railway ላይ ቦቱ በቋሚነት እንዲሰራ (Polling mode)
    app = Application.builder().token(TOKEN).build()
    # Handler-ዎችን እዚህ ጋር ጨምር (ቀደም ብለን የሰራናቸው)
    # ...
    app.run_polling()

if __name__ == '__main__':
    main()
