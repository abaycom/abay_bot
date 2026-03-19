import telebot
import requests
import random
from telebot import types

# --- 1. መለያዎችህን እዚህ አስገባ ---
TOKEN = '7161551829:AAH1_u9rmkfqj2itPWYLQciltuQiFFqUzpo' 
ADMIN_ID = '5049565154' 
RAPID_API_KEY = "c327bddd7cmsh6c8a415dc595cf7p19604ejsn4dbe78def281"

bot = telebot.TeleBot(TOKEN)

# --- 2. የኢንስታግራም መረጃ መሳቢያ ተግባር ---
def get_insta_info(username):
    url = "https://instagram120.p.rapidapi.com/api/instagram/posts"
    payload = {"username": username, "maxId": ""}
    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": "instagram120.p.rapidapi.com",
        "x-rapidapi-key": RAPID_API_KEY
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

# --- 3. የቦት ትዕዛዞች ---

@bot.message_handler(commands=['start'])
def start(message):
    msg = """
🌟 **እንኳን ወደ Instagram Info Hacker በሰላም መጡ!** 🌟

የማንኛውንም ሰው Instagram Username በመጠቀም የሚከተሉትን ማግኘት ይችላሉ፦
✅ ሚስጥራዊ የሆኑ የቆዩ ፖስቶች
✅ የተደበቁ የኢሜይል ፍንጮች
✅ የመለያው ደህንነት ሁኔታ (Breach Status)

**ለመጀመር የሰውየውን Username ብቻ ይላኩ፦**
    """
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def handle_insta(message):
    username = message.text.strip().replace("@", "") # @ ካለው ለማጥፋት
    bot.send_message(message.chat.id, f"🔍 '{username}' በኢንስታግራም ሰርቨር ላይ በመፈለግ ላይ... እባክዎ ይጠብቁ።")

    # መረጃውን ከ API መሳብ
    data = get_insta_info(username)
    
    # የውሸት/የተደበቀ መረጃ ለ Social Engineering
    masked_pass = f"{username[:2]}****{random.randint(10, 99)}"
    
    if data and 'edges' in data:
        try:
            # የመጀመሪያውን ፖስት ፎቶ ማግኘት
            img_url = data['edges'][0]['node']['display_url']
            post_count = len(data['edges'])
            
            result_text = f"""
✅ **መረጃው ተገኝቷል!**

👤 **Username:** {username}
📸 **ጠቅላላ ፖስት:** {post_count}
🔐 **Password Hint:** `{masked_pass}`
📂 **Status:** Vulnerable (LinkedIn & 1win Breach)

⚠️ **ሙሉውን መረጃ ለማየት እና ፓስወርዱን ለመክፈት 100 Star ይክፈሉ።**
            """
            
            markup = types.InlineKeyboardMarkup()
            btn = types.InlineKeyboardButton("🔓 በ 100 Star ክፈት", callback_data=f"pay_{username}")
            markup.add(btn)
            
            bot.send_photo(message.chat.id, img_url, caption=result_text, reply_markup=markup, parse_mode="Markdown")
            
        except Exception as e:
            bot.send_message(message.chat.id, "❌ መረጃው ተገኝቷል ነገር ግን ፎቶውን መጫን አልተቻለም። ሙሉ መረጃውን ለማየት ይክፈሉ።")
    else:
        # APIው መረጃ ካላመጣ (ለምሳሌ አካውንቱ ዝግ ከሆነ)
        fallback_msg = f"🔍 መረጃው በዳታቤዝ ውስጥ ተገኝቷል ነገር ግን አካውንቱ Private ነው። \n\n🔐 ፓስወርድ: {masked_pass} \n⚠️ ለመክፈት 100 Star ይክፈሉ።"
        bot.send_message(message.chat.id, fallback_msg)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def admin_alert(call):
    target = call.data.split("_")[1]
    bot.answer_callback_query(call.id, "የክፍያ ጥያቄ ተልኳል")
    bot.send_message(call.message.chat.id, "⭐ ክፍያዎን ሲያጠናቅቁ መረጃው ይላክለታል። \nጥያቄ ካለዎት @Admin_User ያናግሩ።")
    
    # ለአንተ የሚመጣ መልዕክት
    bot.send_message(ADMIN_ID, f"🔔 **አዲስ ተጠቃሚ ሊከፍል ነው!**\n\nTarget: {target}\nUser: @{call.from_user.username}")

bot.polling()
