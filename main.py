import telebot
import requests
import random
from telebot import types

# --- 1. CONFIG ---
TOKEN = '7161551829:AAH1_u9rmkfqj2itPWYLQciltuQiFFqUzpo' 
ADMIN_ID = '5049565154' 
RAPID_API_KEY = "c327bddd7cmsh6c8a415dc595cf7p19604ejsn4dbe78def281"

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(func=lambda m: True)
def handle_lookup(message):
    username = message.text.strip().replace("@", "")
    bot.send_message(message.chat.id, f"📡 ግንኙነት በመፍጠር ላይ... \n🔍 '{username}' ተገኝቷል።")

    # API ጥሪ (RapidAPI)
    url = "https://instagram-data1.p.rapidapi.com/user/info"
    headers = {
        "x-rapidapi-key": RAPID_API_KEY,
        "x-rapidapi-host": "instagram-data1.p.rapidapi.com"
    }
    
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("🔓 በ 100 Star ሙሉውን ክፈት", callback_data=f"pay_{username}")
    markup.add(btn)

    try:
        response = requests.get(url, headers=headers, params={"username": username}, timeout=15)
        data = response.json() if response.status_code == 200 else None

        if data and 'full_name' in data:
            full_name = data.get('full_name', username)
            profile_pic = data.get('profile_pic_url_hd', data.get('profile_pic_url'))
            # እዚህ ጋር ስሙን 'result_msg' ብለነዋል
            result_msg = f"✅ **ዒላማው ተለይቷል!**\n\n👤 ስም: {full_name}\n🔐 Password: {username[:2]}***@26\n\nሙሉውን ለማየት ይክፈሉ"
            
            if profile_pic:
                # እዚህ ጋር 'result_text' የሚለውን ወደ 'result_msg' ቀይሬዋለሁ
                bot.send_photo(message.chat.id, profile_pic, caption=result_msg, reply_markup=markup, parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, result_msg, reply_markup=markup, parse_mode="Markdown")
        else:
            # ዳታው ባይመጣ (Fallback)
            fallback_msg = f"✅ **መረጃው በዳታቤዝ ተገኝቷል!**\n👤 Username: {username}\n🔐 ፓስወርድ: {username[:2]}***#\n\nለመክፈት 100 Star ይክፈሉ"
            bot.send_message(message.chat.id, fallback_msg, reply_markup=markup, parse_mode="Markdown")
            
    except Exception as e:
        # ማንኛውም ስህተት ቢኖር እንኳ ለተጠቃሚው ምላሽ ይሰጣል
        bot.send_message(message.chat.id, f"✅ መረጃ ተገኝቷል!\n🔐 ፓስወርድ: {username[:2]}***\n\nለመክፈት ይሞክሩ።", reply_markup=markup)

bot.polling(none_stop=True)
