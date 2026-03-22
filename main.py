import os
import telebot
import time
from groq import Groq
from telebot import types

# 1. Configuration (Railway ላይ ከሆኑ በ Environment Variables ይተኩ)
TELEGRAM_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
GROQ_API_KEY = 'YOUR_GROQ_API_KEY'

client = Groq(api_key=GROQ_API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ጊዜያዊ ዳታቤዝ (ለቋሚነት SQLite ይመከራል)
user_stats = {}

def get_user(user_id):
    if user_id not in user_stats:
        user_stats[user_id] = {'usage': 0, 'invites': 0, 'referred_by': None}
    return user_stats[user_id]

# 2. Start Command
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    # Referral Logic
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if referrer_id != user_id and user['referred_by'] is None:
            user['referred_by'] = referrer_id
            referrer = get_user(referrer_id)
            referrer['invites'] += 1
            bot.send_message(referrer_id, f"🎊 **አዲስ ሰው ተቀላቅሏል!**\nአጠቃላይ የጋበዙት ሰው ብዛት: `{referrer['invites']}`")

    welcome_text = (
        f"👋 **ሰላም {message.from_user.first_name}!**\n\n"
        "ወደ **AI Viral Assistant 🚀** እንኳን በደህና መጡ!\n\n"
        "እኔ የእርስዎን የሶሻል ሚዲያ ቪዲዮዎች **Viral** እንዲሆኑ የምረዳ AI ነኝ።\n\n"
        "✨ **ምን መስራት እችላለሁ?**\n"
        "• 🎥 የቲቶክ እና የሪልስ ስክሪፕቶች\n"
        "• ✍️ የሚስቡ ካፕሽኖች (Captions)\n"
        "• 🔥 ትሬንድ የሆኑ ሀሽታጎች\n\n"
        "🎁 **ዕድል:** በቀን 3 ጊዜ በነፃ ይጠቀሙ።\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "👇 **አሁኑኑ የቪዲዮዎን ሃሳብ ይላኩ ማንኛውንም ቋንቋ እረዳለሁ!**"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("🔗 ጓደኛ ጋብዝ (Invite)", callback_data="ref_link")
    btn2 = types.InlineKeyboardButton("📊 የእኔ ሁኔታ (Stats)", callback_data="my_stats")
    markup.add(btn1, btn2)
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

# 3. Callback Handlers (Buttons)
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    user = get_user(user_id)
    bot_username = bot.get_me().username

    if call.data == "ref_link":
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        bot.send_message(call.message.chat.id, 
            f"📢 **የእርስዎ መጋበዣ ሊንክ**\n\n`{ref_link}`\n\n"
            "ይህንን ሊንክ ለ 3 ጓደኞችዎ በመላክ **ያልተገደበ (Unlimited)** አገልግሎት ያግኙ! 🚀", 
            parse_mode="Markdown")
            
    elif call.data == "my_stats":
        status = "✅ Unlimited" if user['invites'] >= 3 else f"{3 - user['usage']} ቀርቶዎታል"
        stats_text = (
            "📊 **የእርስዎ መረጃ**\n"
            "━━━━━━━━━━━━━\n"
            f"👤 የጋበዙት ሰው: `{user['invites']}`\n"
            f"🔄 የዛሬ አጠቃቀም: `{user['usage']}/3`\n"
            f"💡 ሁኔታ: `{status}`"
        )
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, stats_text, parse_mode="Markdown")

# 4. AI Logic with "Typing" Action
@bot.message_handler(func=lambda message: True)
def handle_ai(message):
    user_id = message.from_user.id
    user = get_user(user_id)

    # Limit Check
    if user['usage'] >= 3 and user['invites'] < 3:
        bot.reply_to(message, "⚠️ **የዛሬው ነፃ ዕድልዎ አልቋል!**\n\nእባክዎ 3 ጓደኞችን በመጋበዝ ያልተገደበ አገልግሎት ይክፈቱ።", 
                     parse_mode="Markdown")
        return

    # Typing Action
    bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        # Prompt Optimization
        prompt = (
            f"Context: You are a professional social media manager. "
            f"Task: Create a viral video script for this idea: '{message.text}'. "
            f"Structure: Hook (First 3 seconds), Body (Value/Story), CTA (Follow/Share). "
            f"Tone: Energetic and modern. Format: Use bullet points and clear sections."
        )

        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",
        )
        
        ai_response = chat_completion.choices[0].message.content
        user['usage'] += 1
        
        # ስክሪፕቱን በሚያምር ሁኔታ መላክ
        final_msg = f"✨ **የተዘጋጀ የ AI ስክሪፕት** ✨\n\n{ai_response}\n\n━━━━━━━━━━━━━\n📱 *በ AI Viral Assistant የተዘጋጀ*"
        bot.reply_to(message, final_msg, parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, "❌ ይቅርታ፣ ሲስተሙ በትንሹ ተጨናንቋል። እባክዎ ደግመው ይሞክሩ።")

print("💎 AI Viral Assistant is Online and Polished!")
bot.polling()
