import telebot
import google.generativeai as genai
from telebot import types

# 1. ያንተ መረጃዎች (እዚህ ጋር ቀይራቸው)
TELEGRAM_TOKEN = '5980643111:AAEi8ppnPud1Z1R_-Dt1RcqnkKdCopHfDQQ'
GEMINI_API_KEY = 'AIzaSyBaVJw1kKIrARiZoXOqyj29Jth9MOYX-aE'

# AI እና ቦቱን ማገናኘት
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# 2. ዳታቤዝ (ለጊዜው በMemory - ቦቱ ሲጠፋ ይጠፋል)
# ለቋሚ ዳታቤዝ በኋላ SQLite መጠቀም ይቻላል
user_data = {} 

def get_user(user_id):
    if user_id not in user_data:
        user_data[user_id] = {'usage': 0, 'invites': 0, 'referred_by': None, 'has_unlocked': False}
    return user_data[user_id]

# 3. /start ሲባል
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    # ሪፈራል ሊንክ መኖሩን መፈተሽ (ለምሳሌ /start 12345)
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if referrer_id != user_id and user['referred_by'] is None:
            user['referred_by'] = referrer_id
            referrer = get_user(referrer_id)
            referrer['invites'] += 1
            bot.send_message(referrer_id, f"🎉 አዲስ ሰው ጋብዘዋል! አጠቃላይ የጋበዙት ሰው ብዛት: {referrer['invites']}")

    welcome_msg = (
        "👋 እንኳን ወደ AI Viral Assistant በሰላም መጡ! 🚀\n\n"
        "እኔ የቪዲዮ ስክሪፕት እና የሶሻል ሚዲያ ስልቶችን የምነግርዎ AI ነኝ።\n"
        "🎁 በቀን 3 ጊዜ በነፃ መጠቀም ይችላሉ።\n\n"
        "👇 የቪዲዮዎን ሃሳብ አሁኑኑ ይጻፉልኝ፦"
    )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔗 መጋበዣ ሊንክ (Referral)", callback_data="ref_link"))
    bot.send_message(message.chat.id, welcome_msg, reply_markup=markup)

# 4. መጋበዣ ሊንክ ሲጠየቅ
@bot.callback_query_handler(func=lambda call: call.data == "ref_link")
def send_ref(call):
    user_id = call.from_user.id
    bot_username = bot.get_me().username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    
    msg = (
        "📢 የእርስዎ መጋበዣ ሊንክ፦\n\n"
        f"{ref_link}\n\n"
        "ይህንን ሊንክ ለ 3 ጓደኞችዎ በመላክ ያልተገደበ (Unlimited) የ AI አገልግሎት ያግኙ!"
    )
    bot.send_message(call.message.chat.id, msg)

# 5. AI ስክሪፕት ማመንጫ
@bot.message_handler(func=lambda message: True)
def handle_ai(message):
    user_id = message.from_user.id
    user = get_user(user_id)

    # የገደብ ቁጥጥር (Check Limit)
    if user['usage'] >= 3 and user['invites'] < 3:
        bot.reply_to(message, "⚠️ የዛሬው የነፃ ዕድልዎ አልቋል!\n\nእባክዎ 3 ጓደኞችን ይጋብዙ ወይም ነገ ተመልሰው ይሞክሩ። 👇", 
                     reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔗 መጋበዣ ሊንክ", callback_data="ref_link")))
        return

    status = bot.reply_to(message, "⌛ AI በማሰብ ላይ ነው...")
    
    try:
        prompt = f"Write a viral TikTok script for: {message.text}. Use a professional engaging tone."
        response = model.generate_content(prompt)
        
        user['usage'] += 1 # አጠቃቀም መቁጠር
        bot.edit_message_text(response.text, message.chat.id, status.message_id)
        
    except Exception as e:
        bot.edit_message_text("❌ ስህተት ተፈጥሯል፣ እባክዎ ደግመው ይሞክሩ።", message.chat.id, status.message_id)

bot.polling()
