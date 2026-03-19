import telebot
import requests
import random
from telebot import types

TOKEN = '7161551829:AAH1_u9rmkfqj2itPWYLQciltuQiFFqUzpo' 
ADMIN_ID = '5049565154' 
# 💡 ማሳሰቢያ፡ ይህን Key RapidAPI ላይ 'Instagram Data' ለሚለው ሰብስክራይብ አድርገህ ተጠቀም
RAPID_API_KEY = "c327bddd7cmsh6c8a415dc595cf7p19604ejsn4dbe78def281"

bot = telebot.TeleBot(TOKEN)

def get_real_insta_profile(username):
    """የፕሮፋይል ፎቶ እና ዝርዝር መረጃ መሳቢያ"""
    url = "https://instagram-data1.p.rapidapi.com/user/info"
    querystring = {"username": username}
    headers = {
        "x-rapidapi-key": RAPID_API_KEY,
        "x-rapidapi-host": "instagram-data1.p.rapidapi.com"
    }
    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

@bot.message_handler(func=lambda m: True)
def start_investigation(message):
    username = message.text.strip().replace("@", "")
    bot.send_message(message.chat.id, f"📡 ከ Instagram ሰርቨር ጋር በመገናኘት ላይ... \n🔍 '{username}' ተገኝቷል። መረጃ እየተሳበ ነው...")

    data = get_real_insta_profile(username)
    
    # የውሸት መረጃ (ለማሳመን)
    fake_pass = f"{username[:2]}***{random.choice(['#', '@'])}{random.randint(100, 999)}"
    
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("🔓 ሙሉ መረጃውን በ 100 Star ክፈት", callback_data=f"pay_{username}")
    markup.add(btn)

    if data and 'full_name' in data:
        full_name = data.get('full_name', 'ያልታወቀ')
        bio = data.get('biography', 'ባዶ')
        followers = data.get('follower_count', 0)
        profile_pic = data.get('profile_pic_url_hd', data.get('profile_pic_url'))

        res_msg = f"""
✅ **ኢላማው ተለይቷል!**

👤 **ስም:** {full_name}
📝 **Bio:** {bio}
👥 **ተከታይ:** {followers}
🔐 **Password Hint:** `{fake_pass}`
📂 **Database:** LinkedIn & 1win Leak (Found)

⚠️ ይህ አካውንት ለጥቃት የተጋለጠ ነው። ሙሉ ፓስወርዱን ለማየት አሁኑኑ ይክፈቱ።
        """
        if profile_pic:
            bot.send_photo(message.chat.id, profile_pic, caption=res_msg, reply_markup=markup)
        else:
            bot.send_message(message.chat.id, res_msg, reply_markup=markup)
    else:
        # APIው ዳታ ባያመጣ እንኳ ቦቱ እንዲህ ብሎ እንዲቀጥል እናደርጋለን (Fake Success)
        fail_msg = f"""
✅ **መረጃው በዳታቤዝ ውስጥ ተገኝቷል!**

👤 **Username:** {username}
🔐 **Password Hint:** `{fake_pass}`
📂 **ሁኔታ:** አካውንቱ Private ስለሆነ መረጃው ተቆልፏል።

⚠️ ፓስወርዱን እና የግል ስልኩን ለማየት 100 Star ይክፈቱ።
        """
        bot.send_message(message.chat.id, fail_msg, reply_markup=markup)

bot.polling()
