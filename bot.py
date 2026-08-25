import asyncio
import logging
import json
import random
import os
from datetime import datetime, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, MenuButtonWebApp
from aiogram.enums import ParseMode

# ==================== CONFIGURATION ====================
# ቦት ቶከንዎን እና የዌብ አፕ ሊንክዎን እዚህ ይተኩ ወይም በ Railway Environment Variables ውስጥ ያስገቡ
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://web-telegram-api.up.railway.app/")
PORT = int(os.getenv("PORT", 8080))
ADMIN_IDS = [5049565154]

# ==================== LOGGING ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== DATA STORAGE ====================
users_db = {}
stats = {
    "total_users": 0,
    "online_users": 0,
    "total_plays": 0,
    "total_ad_views": 0,
    "referrals": {},
    "ad_config": {
        "video_ad_enabled": False,
        "banner_ad_enabled": False,
        "bot_ad_enabled": False,
        "video_ad_duration": 5,
        "video_ad_text": "Watch New Movies for Free!",
        "banner_ad_text": "New Releases Every Day!",
        "bot_ad_text": "Check out the latest movies on Cinema Hub! Watch for free now!",
        "video_ad_views": 0,
        "video_ad_skips": 0,
        "banner_ad_views": 0,
        "banner_ad_clicks": 0,
        "bot_ad_sent": 0,
        "bot_ad_clicks": 0
    }
}

BOT_ADS = [
    "🎬 *New Movies Added!*\n\nWatch them now for free on Cinema Hub!",
    "🔥 *TOP 10 Movies*\n\nCheck out this week's trending movies!",
    "📺 *New TV Series*\n\nLatest TV shows available for free!",
    "⭐ *Highest Rated Movies*\n\nIMDb Top Rated Movies for free!",
]

# ==================== INITIALIZE BOT ====================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==================== WEB SERVER (SERVES INDEX.HTML) ====================
async def handle_index(request):
    if os.path.exists("index.html"):
        return web.FileResponse("index.html")
    return web.Response(text="index.html not found", status=404)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/index.html", handle_index)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Web server running on http://0.0.0.0:{PORT}")

# ==================== COMMANDS ====================

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """Handle /start command"""
    user = message.from_user
    user_id = user.id

    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].startswith("ref_"):
        referrer_id = int(args[1].replace("ref_", ""))

    if user_id not in users_db:
        users_db[user_id] = {
            "id": user_id,
            "first_name": user.first_name,
            "username": user.username,
            "joined": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "plays": 0,
            "referrals": [],
            "is_premium": False,
            "ad_views": 0
        }
        stats["total_users"] += 1

        if referrer_id and referrer_id in users_db and referrer_id != user_id:
            users_db[referrer_id]["referrals"].append(user_id)
            stats["referrals"][str(referrer_id)] = stats["referrals"].get(str(referrer_id), 0) + 1

            try:
                await bot.send_message(
                    referrer_id,
                    f"🎉 *Congratulations!*\n\n"
                    f"{user.first_name} joined using your link!\n"
                    f"You now have {len(users_db[referrer_id]['referrals'])} referrals.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Failed to notify referrer: {e}")

    users_db[user_id]["last_active"] = datetime.now().isoformat()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🎬 Open Cinema Hub",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )],
        [InlineKeyboardButton(
            text="👥 Invite Friends",
            callback_data="invite"
        )],
        [InlineKeyboardButton(
            text="📊 My Statistics",
            callback_data="my_stats"
        )]
    ])

    welcome_text = f"""🎬 *Welcome to Cinema Hub!*

Hello {user.first_name}! 👋

Watch movies, TV series, and your favorites for free!

✨ *Features:*
• 🎥 10,000+ Movies
• 📺 TV Series
• ❤️ Favorites List
• 🔄 Screen Rotation
• 🌐 English Language

👇 Tap the button below to start!"""

    await message.answer(welcome_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    if stats["ad_config"]["bot_ad_enabled"]:
        await asyncio.sleep(2)
        ad = random.choice(BOT_ADS)
        await message.answer(ad, parse_mode=ParseMode.MARKDOWN)
        stats["ad_config"]["bot_ad_sent"] += 1


@dp.callback_query(F.data == "invite")
async def callback_invite(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    bot_username = (await bot.get_me()).username
    invite_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Copy Link", url=f"https://t.me/share/url?url={invite_link}&text=🎬 Cinema Hub - Watch Movies & TV Shows for Free!")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_menu")]
    ])

    referral_count = len(users_db.get(user_id, {}).get("referrals", []))

    text = f"""👥 *Invite Friends*

Your unique referral link:
`{invite_link}`

📊 *Statistics:*
• Total Invited: {referral_count} people
• Reward: Invite 5 people to get Premium!

🔗 Copy the link and share with your friends!"""

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()


@dp.callback_query(F.data == "my_stats")
async def callback_stats(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = users_db.get(user_id, {})

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_menu")]
    ])

    text = f"""📊 *My Statistics*

👤 Name: {user.get('first_name', 'Unknown')}
📅 Joined: {user.get('joined', 'N/A')[:10]}
🎬 Total Plays: {user.get('plays', 0)}
👁️ Ad Views: {user.get('ad_views', 0)}
👥 Invited: {len(user.get('referrals', []))} people
⭐ Premium: {'Yes' if user.get('is_premium') else 'No'}

🏆 *Rank:* {get_user_rank(user_id)}"""

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()


@dp.callback_query(F.data == "back_to_menu")
async def callback_back(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🎬 Open Cinema Hub",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )],
        [InlineKeyboardButton(
            text="👥 Invite Friends",
            callback_data="invite"
        )],
        [InlineKeyboardButton(
            text="📊 My Statistics",
            callback_data="my_stats"
        )]
    ])

    await callback.message.edit_text(
        "🎬 *Cinema Hub*\n\nWatch movies for free! 👇",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()


# ==================== ADMIN COMMANDS ====================

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ You are not an admin!")
        return

    active_users = sum(1 for u in users_db.values() 
                      if datetime.fromisoformat(u["last_active"]) > datetime.now() - timedelta(hours=24))

    ad_cfg = stats["ad_config"]

    text = f"""📊 *Bot Statistics*

👥 Total Users: {stats['total_users']}
🟢 24h Active: {active_users}
🎬 Total Plays: {stats['total_plays']}
👁️ Total Ad Views: {stats['total_ad_views']}
🔗 Total Referrals: {sum(stats['referrals'].values())}

📢 *Ad Configuration:*
• Video Ads: {'✅ ON' if ad_cfg['video_ad_enabled'] else '❌ OFF'}
• Banner Ads: {'✅ ON' if ad_cfg['banner_ad_enabled'] else '❌ OFF'}
• Bot Ads: {'✅ ON' if ad_cfg['bot_ad_enabled'] else '❌ OFF'}

📈 *Ad Performance:*
• Video Ad Views: {ad_cfg['video_ad_views']}
• Video Ad Skips: {ad_cfg['video_ad_skips']}
• Banner Impressions: {ad_cfg['banner_ad_views']}
• Banner Clicks: {ad_cfg['banner_ad_clicks']}
• Bot Ads Sent: {ad_cfg['bot_ad_sent']}
• Bot Ad Clicks: {ad_cfg['bot_ad_clicks']}"""

    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


@dp.message(Command("users"))
async def cmd_users(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    if not users_db:
        await message.answer("No registered users yet.")
        return

    user_list = []
    for uid, user in list(users_db.items())[:20]:
        status = "🟢" if datetime.fromisoformat(user["last_active"]) > datetime.now() - timedelta(minutes=5) else "⚪"
        user_list.append(f"{status} {user.get('first_name', 'Unknown')} (@{user.get('username', 'N/A')}) - Plays: {user.get('plays', 0)}")

    text = "👥 *Registered Users*\n\n" + "\n".join(user_list)
    if len(users_db) > 20:
        text += f"\n\n...and {len(users_db) - 20} more"

    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


@dp.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    broadcast_text = message.text.replace("/broadcast", "").strip()
    if not broadcast_text:
        await message.answer("❌ Usage: /broadcast <message>")
        return

    sent = 0
    failed = 0

    for user_id in users_db:
        try:
            await bot.send_message(user_id, f"📢 *Announcement*\n\n{broadcast_text}", parse_mode=ParseMode.MARKDOWN)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed += 1
            logger.error(f"Failed to send to {user_id}: {e}")

    await message.answer(f"✅ Sent: {sent}\n❌ Failed: {failed}")


@dp.message(Command("ad_config"))
async def cmd_ad_config(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    args = message.text.split()
    if len(args) < 2:
        text = """⚙️ *Ad Configuration*

Usage:
/ad_config video on/off
/ad_config banner on/off
/ad_config bot on/off
/ad_config video_duration <seconds>
/ad_config video_text <text>
/ad_config banner_text <text>
/ad_config bot_text <text>

Current Status:"""

        cfg = stats["ad_config"]
        text += f"""
• Video Ads: {'✅ ON' if cfg['video_ad_enabled'] else '❌ OFF'}
• Banner Ads: {'✅ ON' if cfg['banner_ad_enabled'] else '❌ OFF'}
• Bot Ads: {'✅ ON' if cfg['bot_ad_enabled'] else '❌ OFF'}
• Video Duration: {cfg['video_ad_duration']}s"""

        await message.answer(text, parse_mode=ParseMode.MARKDOWN)
        return

    setting = args[1].lower()
    cfg = stats["ad_config"]

    if setting == "video":
        cfg["video_ad_enabled"] = args[2].lower() == "on"
        await message.answer(f"✅ Video ads: {'ON' if cfg['video_ad_enabled'] else 'OFF'}")

    elif setting == "banner":
        cfg["banner_ad_enabled"] = args[2].lower() == "on"
        await message.answer(f"✅ Banner ads: {'ON' if cfg['banner_ad_enabled'] else 'OFF'}")

    elif setting == "bot":
        cfg["bot_ad_enabled"] = args[2].lower() == "on"
        await message.answer(f"✅ Bot ads: {'ON' if cfg['bot_ad_enabled'] else 'OFF'}")

    elif setting == "video_duration":
        cfg["video_ad_duration"] = int(args[2])
        await message.answer(f"✅ Video ad duration: {args[2]} seconds")

    elif setting == "video_text":
        cfg["video_ad_text"] = " ".join(args[2:])
        await message.answer("✅ Video ad text updated!")

    elif setting == "banner_text":
        cfg["banner_ad_text"] = " ".join(args[2:])
        await message.answer("✅ Banner ad text updated!")

    elif setting == "bot_text":
        cfg["bot_ad_text"] = " ".join(args[2:])
        await message.answer("✅ Bot ad text updated!")


@dp.message(Command("send_ad"))
async def cmd_send_ad(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    ad_text = message.text.replace("/send_ad", "").strip()
    if not ad_text:
        ad_text = stats["ad_config"]["bot_ad_text"]

    sent = 0
    failed = 0

    for user_id in users_db:
        try:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🎬 Open Cinema Hub",
                    web_app=WebAppInfo(url=WEBAPP_URL)
                )]
            ])
            await bot.send_message(
                user_id, 
                f"📢 *Sponsored*\n\n{ad_text}", 
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed += 1
            logger.error(f"Failed to send to {user_id}: {e}")

    stats["ad_config"]["bot_ad_sent"] += sent
    await message.answer(f"✅ Ad sent to {sent} users!\n❌ Failed: {failed}")


# ==================== WEB APP DATA HANDLER ====================

@dp.message(F.web_app_data)
async def handle_web_app_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        action = data.get("action")
        user_id = message.from_user.id

        if action == "play":
            if user_id in users_db:
                users_db[user_id]["plays"] += 1
                stats["total_plays"] += 1

        elif action == "ad_view":
            ad_type = data.get("ad_type", "video")
            if user_id in users_db:
                users_db[user_id]["ad_views"] = users_db[user_id].get("ad_views", 0) + 1
            stats["total_ad_views"] += 1

            if ad_type == "video":
                stats["ad_config"]["video_ad_views"] += 1
            elif ad_type == "banner":
                stats["ad_config"]["banner_ad_views"] += 1

        elif action == "ad_skip":
            stats["ad_config"]["video_ad_skips"] += 1

        elif action == "banner_click":
            stats["ad_config"]["banner_ad_clicks"] += 1

        elif action == "get_stats":
            await message.answer(json.dumps({
                "total_users": stats["total_users"],
                "online_users": stats["online_users"],
                "total_plays": stats["total_plays"],
                "total_ad_views": stats["total_ad_views"],
                "ad_config": stats["ad_config"]
            }))

    except Exception as e:
        logger.error(f"WebApp data error: {e}")


# ==================== HELPER FUNCTIONS ====================

def get_user_rank(user_id):
    referral_count = len(users_db.get(user_id, {}).get("referrals", []))
    if referral_count >= 50: return "👑 Legend"
    elif referral_count >= 20: return "💎 Diamond"
    elif referral_count >= 10: return "🥇 Gold"
    elif referral_count >= 5: return "🥈 Silver"
    elif referral_count >= 1: return "🥉 Bronze"
    return "🆕 Newbie"


async def set_menu_button():
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="🎬 Cinema Hub",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        )
        logger.info("Menu button set successfully")
    except Exception as e:
        logger.error(f"Failed to set menu button: {e}")


# ==================== MAIN ====================

async def main():
    # 1. Start the HTTP Web Server for index.html
    await start_web_server()
    
    # 2. Set Bot Menu Button
    await set_menu_button()
    
    # 3. Start Bot Polling
    logger.info("Bot started!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
