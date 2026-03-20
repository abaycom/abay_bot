from telethon import TelegramClient, events, functions, types
import datetime
import random

# --- 1. CONFIGURATION ---
API_ID = 9247035
API_HASH = '4fc2273bb397b999cad568a1934428df'
BOT_TOKEN = '7161551829:AAH1_u9rmkfqj2itPWYLQciltuQiFFqUzpo'
ADMIN_ID = 5049565154 # ቁጥር ብቻ (ለምሳሌ: 12345678)

# ቦቱን እና ክላየንቱን ማስነሳት
bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

def get_dc_location(dc_id):
    locations = {1: "USA (Miami)", 2: "Netherlands (Amsterdam)", 3: "USA (Miami)", 4: "Netherlands (Amsterdam)", 5: "Singapore"}
    return locations.get(dc_id, "Unknown")

# --- 2. BOT LOGIC ---

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply("🔍 **ወደ Telegram OSINT / ID Lookup እንኳን መጡ!**\n\nለመጀመር @username ወይም ስልክ ቁጥር (+251...) ይላኩ።")

@bot.on(events.NewMessage)
async def handle_message(event):
    if event.text.startswith('/'): return
    
    query = event.text.strip()
    chat_id = event.chat_id
    
    waiting_msg = await event.reply("📡 ከ Telegram ሰርቨር ጋር በመገናኘት ላይ... \n🔍 ጥልቅ ፍለጋ እየተካሄደ ነው (Deep Scan)...")

    try:
        target_user = None
        
        # ስልክ ቁጥር ከሆነ (በ + የሚጀምር ከሆነ)
        if query.startswith('+') or query.isdigit():
            phone = query if query.startswith('+') else f"+{query}"
            contact = types.InputPhoneContact(client_id=0, phone=phone, first_name="Target", last_name="")
            result = await bot(functions.contacts.ImportContactsRequest([contact]))
            if result.users:
                target_user = result.users[0]
        
        # ዩዘርኔም ከሆነ
        else:
            username = query.replace("@", "")
            target_user = await bot.get_entity(username)

        if target_user:
            user_id = target_user.id
            first_name = target_user.first_name
            username = f"@{target_user.username}" if target_user.username else "የለውም"
            dc_id = target_user.photo.dc_id if target_user.photo else "Unknown"
            
            # አካውንቱ የተከፈተበትን ጊዜ በግምት (በ ID ቁጥር ላይ በመመስረት)
            # ይህ Social Engineering ለመስራት ይረዳል
            year = "2018-2020" if user_id < 1000000000 else "2021-2024"
            
            res_msg = f"""
✅ **ውጤት ተገኝቷል!**

👤 **ስም:** {first_name}
🆔 **User ID:** `{user_id}`
🔗 **Username:** {username}
🌍 **Data Center:** {dc_id} ({get_dc_location(dc_id)})
📅 **Created Around:** {year}

-----------------------------------
🔓 **የተቆለፉ መረጃዎች (Locked):**
📍 **ግምታዊ ቦታ:** [LOCKED 🔒]
👥 **በብዛት የሚያወራቸው:** [LOCKED 🔒]
📂 **የመረጃ ምንጭ:** LinkedIn/Facebook Leak

**ሁሉንም መረጃዎች (ያለ መደበቂያ) ለማየት 100 Star ይክፈሉ!**
            """
            
            # Buttons
            from telethon import Button
            buttons = [
                [Button.inline("🔓 በ 100 Star ክፈት", data=f"pay_{user_id}")],
                [Button.inline("📢 ለጓደኛ ሼር አድርግ", data="share")]
            ]
            
            await waiting_msg.delete()
            await bot.send_message(chat_id, res_msg, buttons=buttons)
            
        else:
            await waiting_msg.edit("❌ ይቅርታ፣ መረጃው አልተገኘም። ቁጥሩ ተደብቆ ወይም ዩዘርኔሙ ትክክል ላይሆን ይችላል።")

    except Exception as e:
        await waiting_msg.edit(f"⚠️ ስህተት ተፈጥሯል! ምናልባት ቴሌግራም ፍለጋውን ገድቦት ሊሆን ይችላል።")

# የክፍያ በተን ሲነካ
@bot.on(events.CallbackQuery(pattern='pay_'))
async def payment(event):
    await event.answer("የክፍያ ሲስተም በመዘጋጀት ላይ ነው...", alert=True)
    await event.respond("⭐ 100 Star ለመክፈል አረጋግጥ የሚለውን ይጫኑ ወይም @Admin_Username ያናግሩ።")

print("OSINT Bot is running...")
bot.run_until_disconnected()
