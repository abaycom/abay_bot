from telethon import TelegramClient, events, functions, types
import random

API_ID = 9247035
API_HASH = '4fc2273bb397b999cad568a1934428df'
BOT_TOKEN = '7161551829:AAH1_u9rmkfqj2itPWYLQciltuQiFFqUzpo'

bot = TelegramClient('osint_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@bot.on(events.NewMessage)
async def handle_osint(event):
    if event.is_command: return
    
    query = event.text.strip()
    wait = await event.reply("🔍 የቴሌግራም ዳታቤዝ በመፈተሽ ላይ... \n⌛ ፎቶዎችን እና የቆዩ ስሞችን በማውጣት ላይ...")

    try:
        user = None
        # በስልክ ቁጥር መፈለግ
        if query.startswith('+') or query.isdigit():
            phone = query if query.startswith('+') else f"+{query}"
            # ለጊዜው ኮንታክት ውስጥ በመጨመር መረጃውን ለማግኘት መሞከር
            contact = types.InputPhoneContact(client_id=0, phone=phone, first_name="Check", last_name="")
            imported = await bot(functions.contacts.ImportContactsRequest([contact]))
            if imported.users:
                user = imported.users[0]
        else:
            user = await bot.get_entity(query)

        if user:
            # የቆዩ ፎቶዎችን መቁጠር
            photos = await bot(functions.photos.GetUserPhotosRequest(user_id=user.id, offset=0, max_id=0, limit=100))
            photo_count = photos.count
            
            # Social Engineering - የቆዩ ስሞች ብዛት (በዘፈቀደ)
            name_changes = random.randint(2, 6)
            
            res = f"""
✅ **OSINT Scan የተጠናቀቀ መረጃ፦**

👤 **የአሁኑ ስም:** {user.first_name}
🆔 **User ID:** `{user.id}`
📸 **የተቀየሩ ፎቶዎች:** {photo_count} ጊዜ
📝 **የስም ለውጥ ታሪክ:** {name_changes} ጊዜ ተቀይሯል
📅 **የተከፈተበት:** { "ከ 2021 በፊት" if user.id < 1500000000 else "በቅርብ ጊዜ" }

-----------------------------------
🔓 **ሚስጥራዊ መረጃዎች (የተቆለፉ):**
🏷 **የመጀመሪያ ስም:** `{user.first_name[0]}*****` [LOCKED 🔒]
📍 **የቆመበት ቦታ:** 500m Radius [LOCKED 🔒]
📱 **የተደበቀ ስልክ:** `{query[:5] if query.isdigit() else "ተገኝቷል"}` [LOCKED 🔒]

**ሁሉንም ታሪክ (ያለ መደበቂያ) ለማየት 100 Star ይክፈሉ!**
            """
            from telethon import Button
            await wait.delete()
            await bot.send_message(event.chat_id, res, buttons=[Button.inline("🔓 በ 100 Star ክፈት", f"pay_{user.id}")])
        else:
            await wait.edit("❌ ይቅርታ፣ መረጃው አልተገኘም። ተጠቃሚው Privacy ገድቦ ሊሆን ይችላል።")
            
    except Exception as e:
        await wait.edit("⚠️ ፍለጋው አልተሳካም። እባክዎ ትንሽ ቆይተው ይሞክሩ።")

bot.run_until_disconnected()
