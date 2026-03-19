import telebot
import requests
import random
import time
from telebot import types

# --- 1. CONFIGURATION ---
TOKEN = '7161551829:AAH1_u9rmkfqj2itPWYLQciltuQiFFqUzpo' # ከ @BotFather ያገኘኸው
ADMIN_ID = '5049565154' # ያንተ የቴሌግራም ID ቁጥር
RAPID_API_KEY = "c327bddd7cmsh6c8a415dc595cf7p19604ejsn4dbe78def281" # የሰጠኸኝ Key

bot = telebot.TeleBot(TOKEN)

# --- 2. FUNCTIONS ---

def get_insta_data(username):
    """ከ RapidAPI የኢንስታግራም መረጃ መሳቢያ"""
    url = "https://instagram120.p.rapidapi.com/api/instagram/posts"
    payload = {"username": username, "maxId": ""}
    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": "instagram120.p.rapidapi.com",
        "x-rapidapi-key": RAPID_API_KEY
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def check_breach_status(target):
    """የመረጃ ስርቆት ምንጮችን በዘፈቀደ ማሳያ (Social Engineering)"""
    sources = ["1win Leak", "LinkedIn DB", "Facebook 2024 Combo", "Telegram Logs"]
    return random.sample(sources, k=2)

# --- 3. BOT HANDLERS ---

@bot.message_handler(commands=['start'])
def welcome(message):
    msg = """
🔍 **እንኳን ወደ Ultimate OSINT Finder በሰላም መጡ!**

ይህ ቦት የተራቀቁ የ API እና የዳታቤዝ ፍለጋዎችን በመጠቀም የሚከተሉትን ያወጣል፦
✅ የ Instagram ሚስጥራዊ መረጃዎች
✅ የተሰረቁ ፓስወርዶች (Email/Phone)
✅ የቆዩ ስልኮች እና የዲጂታል አሻራዎች

**ለመጀመር Username፣ Email ወይም ስልክ ቁጥር ያስገቡ፦**
    """
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def handle_all_requests(message):
    query = message.text.strip()
    bot.send_message(message.chat.id, "📡 ግንኙነት በመፍጠር ላይ... \n🔍 ጥልቅ ፍለጋ እየተካሄደ ነው (Deep Scan)...")

    # 1. Instagram ፍለጋ (Username ከሆነ)
    is_social = not ("@" in query or query.startswith("+") or query.isdigit())
    
    masked_pass = f"{query[:2]}****{random.randint(10, 99)}"
    leaks = check_breach_status(query)
    
    result_text = f"""
🚨 **ውጤት ተገኝቷል!**

👤 **ዒላማ:** {query}
📂 **የመረጃ ምንጭ:** {", ".join(leaks)}
🔐 **Password:** `{masked_pass}`
📞 **Phone:** 09{random.randint(10, 45)}****{random.randint(10, 99)}
📅 **Last Breach:** 2024-03-12

⚠️ **ሙሉውን መረጃ (ያለ መደበቂያ) ለማየት 100 Star መክፈል አለብዎት።**
    """

    # Buttons
    markup = types.InlineKeyboardMarkup()
    btn_star = types.InlineKeyboardButton("🔓 በ 100 Star ክፈት", callback_data=f"pay_star_{query}")
    btn_telebirr = types.InlineKeyboardButton("💳 በቴሌብር (Manual)", callback_data=f"pay_manual_{query}")
    markup.add(btn_star)
    markup.add(btn_telebirr)

    if is_social:
        insta_data = get_insta_data(query)
        if insta_data and 'edges' in insta_data:
            # የመጀመሪያውን ፖስት ፎቶ ለማሳየት
            try:
                img_url = insta_data['edges'][0]['node']['display_url']
                bot.send_photo(message.chat.id, img_url, caption=result_text, reply_markup=markup, parse_mode="Markdown")
            except:
                bot.send_message(message.chat.id, result_text, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, result_text, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, result_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def handle_payment_click(call):
    pay_type = call.data.split("_")[1]
    target = call.data.split("_")[2]
    
    if pay_type == "star":
        bot.answer_callback_query(call.id, "የ Star ክፍያ በመጠባበቅ ላይ...")
        bot.send_message(call.message.chat.id, "⭐ 100 Star መክፈልዎን ሲያጠናቅቁ መረጃው ይላክለታል።")
    else:
        bot.answer_callback_query(call.id, "የቴሌብር መረጃ እየተላከ ነው...")
        bot.send_message(call.message.chat.id, "💳 በቴሌብር ለመክፈል @Your_Admin_User ላይ Screenshot ይላኩ።")

    # ለአንተ የሚመጣ መልዕክት (Notification)
    bot.send_message(ADMIN_ID, f"🔔 **የክፍያ ሙከራ!**\n\nተጠቃሚ: @{call.from_user.username}\nዒላማ: {target}\nአይነት: {pay_type}")

bot.polling()
