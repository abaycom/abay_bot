import asyncio
import logging
import json
import os
import hmac
import hashlib
from urllib.parse import parse_qsl
from datetime import datetime, timedelta, timezone

import aiohttp
from aiohttp import web
from motor.motor_asyncio import AsyncIOMotorClient

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, MenuButtonWebApp,
    InlineQuery, InlineQueryResultPhoto, InlineQueryResultArticle, InputTextMessageContent
)
from aiogram.enums import ParseMode, ChatMemberStatus, ChatType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://web-telegram-api.up.railway.app/")
PORT = int(os.getenv("PORT", 8080))
MONGO_URI = os.getenv("MONGO_URI", "")          # e.g. mongodb+srv://user:pass@cluster.mongodb.net
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "nilo_cinema")
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
AUTO_POST_INTERVAL_HOURS = float(os.getenv("AUTO_POST_INTERVAL_HOURS", "6"))
AUTO_POST_MAX_PER_RUN = int(os.getenv("AUTO_POST_MAX_PER_RUN", "3"))

# Comma-separated admin IDs in env, e.g. "5049565154,123456789"
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "5049565154").split(",") if x.strip()]

ONLINE_WINDOW_MINUTES = 5
ACTIVE_WINDOW_HOURS = 24

# ==================== LOGGING ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== MONGODB ====================
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client[MONGO_DB_NAME]
users_col = db["users"]
settings_col = db["settings"]
groups_col = db["groups"]            # groups/channels the bot has been added to
posted_movies_col = db["posted_movies"]  # de-dup log for auto-posted movies

DEFAULT_AD_CONFIG = {
    "video_ad_enabled": False,
    "banner_ad_enabled": False,
    "bot_ad_enabled": False,
    "video_ad_duration": 5,
    "video_ad_text": "Watch New Movies for Free!",
    "banner_ad_text": "New Releases Every Day!",
    "bot_ad_text": "Check out the latest movies on Nilo Cinema! Watch for free now!",
}

DEFAULT_FORCE_JOIN = {
    "enabled": False,
    "channel_username": "",   # e.g. "nilo_cinema_channel" (no @)
    "youtube_url": "",        # optional, unverified "also follow us" link
    "tiktok_url": "",         # optional, unverified "also follow us" link
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


async def ensure_settings():
    doc = await settings_col.find_one({"_id": "global"})
    if not doc:
        await settings_col.insert_one({
            "_id": "global",
            "total_plays": 0,
            "total_ad_views": 0,
            "ad_config": DEFAULT_AD_CONFIG,
            "force_join": DEFAULT_FORCE_JOIN,
        })
    elif "force_join" not in doc:
        await settings_col.update_one({"_id": "global"}, {"$set": {"force_join": DEFAULT_FORCE_JOIN}})


async def get_settings():
    doc = await settings_col.find_one({"_id": "global"})
    if not doc:
        await ensure_settings()
        doc = await settings_col.find_one({"_id": "global"})
    return doc


async def update_ad_config(patch: dict):
    await settings_col.update_one(
        {"_id": "global"},
        {"$set": {f"ad_config.{k}": v for k, v in patch.items()}},
        upsert=True,
    )


async def inc_stat(field: str, amount: int = 1):
    await settings_col.update_one({"_id": "global"}, {"$inc": {field: amount}}, upsert=True)


async def upsert_user(user: types.User, referrer_id: int | None):
    existing = await users_col.find_one({"_id": user.id})
    if existing:
        await users_col.update_one(
            {"_id": user.id},
            {"$set": {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "username": user.username,
                "last_active": now_iso(),
            }},
        )
        return existing, False

    new_doc = {
        "_id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "joined": now_iso(),
        "last_active": now_iso(),
        "plays": 0,
        "ad_views": 0,
        "referrals": [],
        "referred_by": referrer_id,
        "is_premium": False,
    }
    await users_col.insert_one(new_doc)

    if referrer_id and referrer_id != user.id:
        referrer = await users_col.find_one({"_id": referrer_id})
        if referrer:
            await users_col.update_one({"_id": referrer_id}, {"$push": {"referrals": user.id}})

    return new_doc, True


async def touch_user(user_id: int):
    await users_col.update_one({"_id": user_id}, {"$set": {"last_active": now_iso()}})


def display_name(u: dict) -> str:
    name = u.get("first_name") or "Unknown"
    if u.get("last_name"):
        name += f" {u['last_name']}"
    return name


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def count_users() -> int:
    return await users_col.count_documents({})


async def count_online() -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=ONLINE_WINDOW_MINUTES)).isoformat()
    return await users_col.count_documents({"last_active": {"$gte": cutoff}})


async def count_active_24h() -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=ACTIVE_WINDOW_HOURS)).isoformat()
    return await users_col.count_documents({"last_active": {"$gte": cutoff}})


async def total_referrals() -> int:
    pipeline = [{"$project": {"count": {"$size": "$referrals"}}}, {"$group": {"_id": None, "total": {"$sum": "$count"}}}]
    result = await users_col.aggregate(pipeline).to_list(length=1)
    return result[0]["total"] if result else 0


# ==================== MULTI-MEDIA MESSAGE COPYING ====================

async def copy_message_to_chat(source: types.Message, chat_id: int, prefix: str = "", reply_markup=None):
    """Sends whatever the admin sent (text, photo, video, document, audio, voice, animation)
    to a single chat, preserving the media and adding an optional caption prefix and button(s)."""
    caption = ((source.caption or "") if source.caption else (source.text or ""))
    full_caption = f"{prefix}{caption}" if prefix else caption

    if source.photo:
        await bot.send_photo(chat_id, photo=source.photo[-1].file_id, caption=full_caption or None, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    elif source.video:
        await bot.send_video(chat_id, video=source.video.file_id, caption=full_caption or None, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    elif source.animation:
        await bot.send_animation(chat_id, animation=source.animation.file_id, caption=full_caption or None, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    elif source.document:
        await bot.send_document(chat_id, document=source.document.file_id, caption=full_caption or None, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    elif source.audio:
        await bot.send_audio(chat_id, audio=source.audio.file_id, caption=full_caption or None, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    elif source.voice:
        await bot.send_voice(chat_id, voice=source.voice.file_id, caption=full_caption or None, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    else:
        text = full_caption or "(empty message)"
        await bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)


def has_sendable_content(message: types.Message) -> bool:
    return bool(
        message.text or message.photo or message.video or message.animation
        or message.document or message.audio or message.voice
    )


# ==================== GROUPS / CHANNELS ====================

async def upsert_group(chat: types.Chat):
    await groups_col.update_one(
        {"_id": chat.id},
        {"$set": {
            "type": chat.type,          # "group" | "supergroup" | "channel"
            "title": chat.title,
            "username": chat.username,
            "updated_at": now_iso(),
        }, "$setOnInsert": {"added_at": now_iso()}},
        upsert=True,
    )


async def remove_group(chat_id: int):
    await groups_col.delete_one({"_id": chat_id})


async def count_groups() -> int:
    return await groups_col.count_documents({})


# ==================== FORCE-JOIN CHANNEL ====================

async def get_force_join() -> dict:
    settings = await get_settings()
    return settings.get("force_join", DEFAULT_FORCE_JOIN)


async def update_force_join(patch: dict):
    await settings_col.update_one(
        {"_id": "global"},
        {"$set": {f"force_join.{k}": v for k, v in patch.items()}},
        upsert=True,
    )


async def user_has_joined_channel(user_id: int, channel_username: str) -> bool:
    if not channel_username:
        return True
    try:
        member = await bot.get_chat_member(f"@{channel_username}", user_id)
        return member.status not in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED)
    except Exception as e:
        logger.error(f"Force-join check failed: {e}")
        # ቻናሉ ላይ bot admin ካልሆነ ወይም ስህተት ካለ፣ ተጠቃሚውን አናግድም
        return True


def force_join_keyboard(fj: dict) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="📢 Join Channel", url=f"https://t.me/{fj['channel_username']}")]]
    # YouTube/TikTok ማረጋገጫ ለ Telegram bot ፈጽሞ የማይቻል ስለሆነ (bot API ላይ
    # የለም)፣ እነዚህ ኦፕሽናል honor-system ቁልፎች ብቻ ናቸው - access አይገድቡም።
    extra = []
    if fj.get("youtube_url"):
        extra.append(InlineKeyboardButton(text="🔴 YouTube", url=fj["youtube_url"]))
    if fj.get("tiktok_url"):
        extra.append(InlineKeyboardButton(text="🎵 TikTok", url=fj["tiktok_url"]))
    if extra:
        rows.append(extra)
    rows.append([InlineKeyboardButton(text="✅ I've Joined", callback_data="check_join")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ==================== INITIALIZE BOT ====================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
BOT_USERNAME = ""  # main() ውስጥ በ startup ይሞላል


class AdminStates(StatesGroup):
    waiting_broadcast = State()
    waiting_group_post = State()
    waiting_force_join_channel = State()
    waiting_youtube_url = State()
    waiting_tiktok_url = State()
    waiting_button_choice = State()      # ማስታወቂያ ከላከ በኋላ Play/link ቁልፍ ይጠይቃል
    waiting_button_url = State()         # custom URL/movie-ID ግቤት


# ==================== WEB SERVER (SERVES INDEX.HTML) ====================
def validate_init_data(init_data: str) -> dict | None:
    """Mini App ከላከው tg.initData ውስጥ ትክክለኛ Telegram signature መሆኑን ያረጋግጣል
    (HMAC-SHA256 ከ bot token ጋር) - ይህ ከሌለ ማንም user_id ፈብርኮ heartbeat/play
    data መላክ ስለሚችል (fake stats) ግድግዳ ነው።"""
    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed_hash, received_hash):
            return None
        user_json = parsed.get("user")
        if not user_json:
            return None
        return json.loads(user_json)
    except Exception as e:
        logger.error(f"initData validation error: {e}")
        return None


async def heartbeat_upsert_user(tg_user: dict):
    """Mini App ውስጥ ብቻ የገባ (ጨርሶ /start ያላደረገ) ተጠቃሚ ካለ እንኳ እንመዘግበዋለን።"""
    user_id = tg_user["id"]
    await users_col.update_one(
        {"_id": user_id},
        {
            "$set": {
                "first_name": tg_user.get("first_name"),
                "last_name": tg_user.get("last_name"),
                "username": tg_user.get("username"),
                "last_active": now_iso(),
            },
            "$setOnInsert": {
                "joined": now_iso(),
                "plays": 0,
                "ad_views": 0,
                "referrals": [],
                "referred_by": None,
                "is_premium": False,
            },
        },
        upsert=True,
    )


def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }


async def handle_options(request):
    return web.Response(headers=cors_headers())


async def handle_heartbeat(request):
    """Mini App ውስጥ ገብቶ ተጠቃሚ ገፆችን እያገላበጠ (ፊልም ሳይጫወት እንኳ) ገባሁ ብሎ
    በየተወሰነ ጊዜ የሚጠራው endpoint - 'last_active' ን ስለሚያዘምን online-count
    ትክክለኛ ይሆናል (ከ /start ውጭም)."""
    try:
        body = await request.json()
        user = validate_init_data(body.get("initData", ""))
        if not user:
            return web.json_response({"ok": False, "error": "invalid initData"}, status=401, headers=cors_headers())
        await heartbeat_upsert_user(user)
        return web.json_response({"ok": True}, headers=cors_headers())
    except Exception as e:
        logger.error(f"heartbeat error: {e}")
        return web.json_response({"ok": False}, status=500, headers=cors_headers())


async def handle_track_play(request):
    """ፊልም/episode ማጫወት ሲጀምር Mini App ከሚጠራው - per-user plays እና
    total_plays ን ያዘምናል፣ ስለዚህ admin ለ user ስንት ፊልም እንዳየ ማየት ይችላል።"""
    try:
        body = await request.json()
        user = validate_init_data(body.get("initData", ""))
        if not user:
            return web.json_response({"ok": False, "error": "invalid initData"}, status=401, headers=cors_headers())

        await heartbeat_upsert_user(user)
        user_id = user["id"]
        await users_col.update_one({"_id": user_id}, {"$inc": {"plays": 1}})
        await inc_stat("total_plays", 1)
        return web.json_response({"ok": True}, headers=cors_headers())
    except Exception as e:
        logger.error(f"track-play error: {e}")
        return web.json_response({"ok": False}, status=500, headers=cors_headers())


async def handle_index(request):
    if os.path.exists("index.html"):
        return web.FileResponse("index.html")
    return web.Response(text="index.html not found", status=404)


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/index.html", handle_index)
    app.router.add_post("/api/heartbeat", handle_heartbeat)
    app.router.add_post("/api/track-play", handle_track_play)
    app.router.add_options("/api/heartbeat", handle_options)
    app.router.add_options("/api/track-play", handle_options)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Web server running on http://0.0.0.0:{PORT}")


# ==================== KEYBOARDS ====================
def user_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Open Cinema Hub", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton(text="👥 Invite Friends", callback_data="invite")],
        [InlineKeyboardButton(text="📊 My Statistics", callback_data="my_stats")],
        [InlineKeyboardButton(text="➕ Add to Group", url=f"https://t.me/{BOT_USERNAME}?startgroup=true"),
         InlineKeyboardButton(text="➕ Add to Channel", url=f"https://t.me/{BOT_USERNAME}?startchannel=true")],
    ])


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Open Cinema Hub", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton(text="👥 Invite Friends", callback_data="invite")],
        [InlineKeyboardButton(text="📊 My Statistics", callback_data="my_stats")],
        [InlineKeyboardButton(text="➕ Add to Group", url=f"https://t.me/{BOT_USERNAME}?startgroup=true"),
         InlineKeyboardButton(text="➕ Add to Channel", url=f"https://t.me/{BOT_USERNAME}?startchannel=true")],
        [InlineKeyboardButton(text="🛠 Admin Panel", callback_data="admin_panel")],
    ])


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats"),
         InlineKeyboardButton(text="👥 Users", callback_data="admin_users")],
        [InlineKeyboardButton(text="📢 Broadcast to Users", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📣 Post to Groups/Channels", callback_data="admin_group_post")],
        [InlineKeyboardButton(text="⚙️ Ad Config", callback_data="admin_adcfg")],
        [InlineKeyboardButton(text="🔒 Force Join Channel", callback_data="admin_forcejoin")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_menu")],
    ])


def force_join_admin_keyboard(fj: dict) -> InlineKeyboardMarkup:
    status = "✅ ON" if fj.get("enabled") else "❌ OFF"
    yt_status = "✅ Set" if fj.get("youtube_url") else "➕ Add"
    tt_status = "✅ Set" if fj.get("tiktok_url") else "➕ Add"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Force Join: {status}", callback_data="forcejoin_toggle")],
        [InlineKeyboardButton(text="✏️ Set Channel Username", callback_data="forcejoin_set")],
        [InlineKeyboardButton(text="🧪 Test Connection", callback_data="forcejoin_test")],
        [InlineKeyboardButton(text=f"🔴 YouTube link: {yt_status}", callback_data="forcejoin_set_youtube")],
        [InlineKeyboardButton(text=f"🎵 TikTok link: {tt_status}", callback_data="forcejoin_set_tiktok")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel")],
    ])


def ad_config_keyboard(cfg: dict) -> InlineKeyboardMarkup:
    def label(name, enabled):
        return f"{'✅' if enabled else '❌'} {name}"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label("Video Ads", cfg["video_ad_enabled"]), callback_data="adcfg_toggle_video")],
        [InlineKeyboardButton(text=label("Banner Ads", cfg["banner_ad_enabled"]), callback_data="adcfg_toggle_banner")],
        [InlineKeyboardButton(text=label("Bot Ads", cfg["bot_ad_enabled"]), callback_data="adcfg_toggle_bot")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel")],
    ])


# ==================== COMMANDS ====================

async def process_new_user_and_welcome(user: types.User, referrer_id: int | None) -> str:
    """Registers/updates the user, notifies referrer if applicable, and returns welcome text."""
    _, is_new = await upsert_user(user, referrer_id)

    if is_new and referrer_id and referrer_id != user.id:
        referrer = await users_col.find_one({"_id": referrer_id})
        if referrer:
            try:
                await bot.send_message(
                    referrer_id,
                    f"🎉 *Congratulations!*\n\n"
                    f"{user.first_name} joined using your link!\n"
                    f"You now have {len(referrer.get('referrals', [])) + 1} referrals.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Failed to notify referrer: {e}")

    return f"""🎬 *Welcome to Nilo Cinema!*

Hello {user.first_name}! 👋

Watch movies, TV series, and your favorites for free!

✨ *Features:*
• 🎥 10,000+ Movies
• 📺 TV Series
• ❤️ Favorites List
• 🔄 Screen Rotation

👇 Tap the button below to start!"""


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user = message.from_user
    user_id = user.id

    # Admins ራሳቸው force-join gate ውስጥ አይገቡም - አለበለዚያ config ያደረገው admin
    # ራሱ ውጭ ተቆልፎ (stuck ሆኖ) ወደ bot መግባት አይችልም።
    if not is_admin(user_id):
        fj = await get_force_join()
        if fj.get("enabled") and fj.get("channel_username"):
            joined = await user_has_joined_channel(user_id, fj["channel_username"])
            if not joined:
                await message.answer(
                    "🔒 *Join our channel first*\n\nTo use Nilo Cinema, please join our channel, then tap \"I've Joined\".",
                    reply_markup=force_join_keyboard(fj),
                    parse_mode=ParseMode.MARKDOWN
                )
                return

    args = message.text.split()
    referrer_id = None
    deep_link_param = None
    if len(args) > 1:
        param = args[1]
        if param.startswith("ref_"):
            try:
                referrer_id = int(param.replace("ref_", ""))
            except ValueError:
                referrer_id = None
        elif param.startswith("movie_") or param.startswith("tv_") or param == "open_app":
            deep_link_param = param

    welcome_text = await process_new_user_and_welcome(user, referrer_id)

    if deep_link_param and deep_link_param != "open_app":
        media_type, tmdb_id = deep_link_param.split("_", 1)
        app_url = f"{WEBAPP_URL}?movie={tmdb_id}&type={media_type}"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Open in Nilo Cinema", web_app=WebAppInfo(url=app_url))]
        ])
        await message.answer("🎬 Tap below to open it in the app:", reply_markup=keyboard)
    else:
        keyboard = admin_menu_keyboard() if is_admin(user_id) else user_menu_keyboard()
        await message.answer(welcome_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)


@dp.callback_query(F.data == "check_join")
async def callback_check_join(callback: types.CallbackQuery):
    user = callback.from_user
    fj = await get_force_join()

    if fj.get("enabled") and fj.get("channel_username"):
        joined = await user_has_joined_channel(user.id, fj["channel_username"])
        if not joined:
            # Telegram አንዳንድ ጊዜ member status update ላይ 1-2 ሰከንድ delay
            # ስላለው (ገና ከተቀላቀሉ በኋላ ወዲያውኑ ቢፈትሹ)፣ አንድ ጊዜ ትንሽ ጠብቀን
            # እንደገና እንፈትሻለን ከ "stuck" experience ለማስቀረት።
            await asyncio.sleep(1.5)
            joined = await user_has_joined_channel(user.id, fj["channel_username"])
        if not joined:
            await callback.answer("❌ You haven't joined the channel yet. Join, then tap again.", show_alert=True)
            return

    welcome_text = await process_new_user_and_welcome(user, None)
    keyboard = admin_menu_keyboard() if is_admin(user.id) else user_menu_keyboard()
    await callback.message.edit_text(welcome_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    await callback.answer("✅ Welcome!")


@dp.callback_query(F.data == "invite")
async def callback_invite(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    bot_username = (await bot.get_me()).username
    invite_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    user = await users_col.find_one({"_id": user_id})
    referral_count = len(user.get("referrals", [])) if user else 0

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Share Link", url=f"https://t.me/share/url?url={invite_link}&text=🎬 Nilo Cinema - Watch Movies & TV Shows for Free!")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_menu")]
    ])

    text = f"""👥 *Invite Friends*

Your unique referral link:
`{invite_link}`

📊 *Statistics:*
• Total Invited: {referral_count} people
• Reward: Invite 5 people to get Premium!"""

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()


@dp.callback_query(F.data == "my_stats")
async def callback_stats(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await users_col.find_one({"_id": user_id}) or {}

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_menu")]
    ])

    ref_count = len(user.get("referrals", []))
    text = f"""📊 *My Statistics*

👤 Name: {display_name(user)}
📅 Joined: {user.get('joined', 'N/A')[:10]}
🎬 Total Plays: {user.get('plays', 0)}
👥 Invited: {ref_count} people
⭐ Premium: {'Yes' if user.get('is_premium') else 'No'}

🏆 *Rank:* {get_user_rank(ref_count)}"""

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()


@dp.callback_query(F.data == "back_to_menu")
async def callback_back(callback: types.CallbackQuery):
    keyboard = admin_menu_keyboard() if is_admin(callback.from_user.id) else user_menu_keyboard()
    await callback.message.edit_text(
        "🎬 *Nilo Cinema*\n\nWatch movies for free! 👇",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()


# ==================== ADMIN PANEL (inline, admin-only) ====================

@dp.callback_query(F.data == "admin_panel")
async def callback_admin_panel(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Admins only", show_alert=True)
        return
    await callback.answer()
    try:
        await callback.message.edit_text("🛠 *Admin Panel*", reply_markup=admin_panel_keyboard(), parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"admin_panel edit failed: {e}")


@dp.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Admins only", show_alert=True)
        return

    total = await count_users()
    online = await count_online()
    active_24h = await count_active_24h()
    refs = await total_referrals()
    settings = await get_settings()
    cfg = settings.get("ad_config", DEFAULT_AD_CONFIG)

    text = f"""📊 *Bot Statistics*

👥 Total Users: {total}
🟢 Online now (last {ONLINE_WINDOW_MINUTES}m): {online}
🟡 24h Active: {active_24h}
🎬 Total Plays: {settings.get('total_plays', 0)}
👁️ Total Ad Views: {settings.get('total_ad_views', 0)}
🔗 Total Referrals: {refs}

📢 *Ads:*
• Video: {'✅' if cfg['video_ad_enabled'] else '❌'}
• Banner: {'✅' if cfg['banner_ad_enabled'] else '❌'}
• Bot: {'✅' if cfg['bot_ad_enabled'] else '❌'}"""

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()


@dp.callback_query(F.data == "admin_users")
async def callback_admin_users(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Admins only", show_alert=True)
        return

    total = await count_users()
    cutoff_online = (datetime.now(timezone.utc) - timedelta(minutes=ONLINE_WINDOW_MINUTES)).isoformat()

    cursor = users_col.find().sort("last_active", -1).limit(20)
    lines = []
    async for u in cursor:
        status = "🟢" if u.get("last_active", "") >= cutoff_online else "⚪"
        uname = f"@{u['username']}" if u.get("username") else "no username"
        lines.append(f"{status} {display_name(u)} ({uname}) — Plays: {u.get('plays', 0)}")

    text = "👥 *Registered Users* (most recently active 20)\n\n" + ("\n".join(lines) if lines else "No users yet.")
    if total > 20:
        text += f"\n\n...and {total - 20} more (total {total})"

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()


@dp.callback_query(F.data == "admin_broadcast")
async def callback_admin_broadcast(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Admins only", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_broadcast)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="admin_panel")]])
    await callback.message.edit_text(
        "📢 *Broadcast*\n\nSend text, a photo, video, or file (with optional caption) — "
        "it will be broadcast to all users exactly as sent.",
        reply_markup=kb, parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()


@dp.message(AdminStates.waiting_broadcast)
async def process_broadcast(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    if not has_sendable_content(message):
        await state.clear()
        await message.answer("❌ Empty message, broadcast cancelled.")
        return

    await state.update_data(pending_message_obj=message, target="users")
    await state.set_state(AdminStates.waiting_button_choice)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Add \"Open App\" button", callback_data="btn_choice_app")],
        [InlineKeyboardButton(text="🔗 Add custom link button", callback_data="btn_choice_custom")],
        [InlineKeyboardButton(text="🚫 No button", callback_data="btn_choice_none")],
    ])
    await message.answer("Add a button under this announcement?", reply_markup=kb)


@dp.callback_query(F.data.startswith("btn_choice_"))
async def callback_button_choice(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Admins only", show_alert=True)
        return

    choice = callback.data.replace("btn_choice_", "")

    if choice == "custom":
        await state.set_state(AdminStates.waiting_button_url)
        await callback.message.edit_text(
            "🔗 Send the button in this format:\n\n`Button Text | https://example.com`\n\n"
            "Example:\n`▶️ Watch Now | https://t.me/nilo_cinema_bot`",
            parse_mode=ParseMode.MARKDOWN
        )
        await callback.answer()
        return

    reply_markup = None
    if choice == "app":
        data = await state.get_data()
        target = data.get("target", "users")
        if target == "users":
            # Broadcast-ው ወደ ራሱ users_col ስለሚላክ (private chat with bot)፣
            # web_app ቁልፍ በቀጥታ ይፈቀዳል - Mini App በአንድ ጠቅታ ይከፈታል።
            reply_markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎬 Open Nilo Cinema", web_app=WebAppInfo(url=WEBAPP_URL))]
            ])
        else:
            # groups/channels ውስጥ web_app ቁልፍ ስለሚታገድ (BUTTON_TYPE_INVALID)
            # URL deep-link እንጠቀማለን - ተጠቃሚው ሲነካ ወደ bot chat ገብቶ
            # ከዚያ Open button ያገኛል።
            reply_markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎬 Open Nilo Cinema", url=f"https://t.me/{BOT_USERNAME}?start=open_app")]
            ])

    await callback.answer()
    await finish_broadcast_or_post(callback.message, state, reply_markup)


@dp.message(AdminStates.waiting_button_url)
async def process_button_url(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    if not message.text or "|" not in message.text:
        await message.answer(
            "❌ Wrong format. Use: `Button Text | link`\n\n"
            "Accepted link types: `https://...`, `http://...`, `t.me/...`, `@username`, `tg://...`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    label, url = message.text.split("|", 1)
    label, url = label.strip(), url.strip()

    # ማንኛውንም የተለመደ link ቅርጽ እንቀበላለን፣ ካስፈለገ ራሳችን እናስተካክለዋለን
    if url.startswith("@"):
        url = f"https://t.me/{url[1:]}"
    elif url.startswith("t.me/") or url.startswith("www.t.me/"):
        url = f"https://{url}"
    elif "://" not in url and "." in url:
        # ምንም scheme ያልያዘ ግን domain የሚመስል (ለምሳሌ "example.com/page")
        url = f"https://{url}"

    if "://" not in url:
        await message.answer(
            "❌ That doesn't look like a valid link. Examples:\n"
            "`https://example.com`\n`t.me/nilo_cinema_bot`\n`@nilo_cinema_bot`\n`tg://resolve?domain=nilo_cinema_bot`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    reply_markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=label, url=url)]])
    await finish_broadcast_or_post(message, state, reply_markup)


async def finish_broadcast_or_post(reply_target: types.Message, state: FSMContext, reply_markup):
    data = await state.get_data()
    await state.clear()

    original_message: types.Message = data.get("pending_message_obj")
    target = data.get("target", "users")

    if original_message is None:
        await reply_target.answer("❌ Something went wrong — please try again.")
        return

    if target == "users":
        cursor = users_col.find({}, {"_id": 1})
        prefix = "📢 *Announcement*\n\n"
    else:
        cursor = groups_col.find({}, {"_id": 1})
        prefix = ""

    sent, failed = 0, 0
    async for u in cursor:
        try:
            await copy_message_to_chat(original_message, u["_id"], prefix=prefix, reply_markup=reply_markup)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed += 1
            logger.error(f"Send failed for {u['_id']}: {e}")

    await reply_target.answer(f"✅ Sent: {sent}\n❌ Failed: {failed}")


@dp.callback_query(F.data == "admin_adcfg")
async def callback_admin_adcfg(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Admins only", show_alert=True)
        return
    settings = await get_settings()
    cfg = settings.get("ad_config", DEFAULT_AD_CONFIG)
    await callback.message.edit_text("⚙️ *Ad Configuration*\n\nTap to toggle:", reply_markup=ad_config_keyboard(cfg), parse_mode=ParseMode.MARKDOWN)
    await callback.answer()


@dp.callback_query(F.data.startswith("adcfg_toggle_"))
async def callback_adcfg_toggle(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Admins only", show_alert=True)
        return

    field_map = {
        "adcfg_toggle_video": "video_ad_enabled",
        "adcfg_toggle_banner": "banner_ad_enabled",
        "adcfg_toggle_bot": "bot_ad_enabled",
    }
    field = field_map.get(callback.data)
    settings = await get_settings()
    cfg = settings.get("ad_config", DEFAULT_AD_CONFIG)
    cfg[field] = not cfg.get(field, False)
    await update_ad_config({field: cfg[field]})

    await callback.message.edit_reply_markup(reply_markup=ad_config_keyboard(cfg))
    await callback.answer(f"{field} → {'ON' if cfg[field] else 'OFF'}")


# ==================== GROUP/CHANNEL POSTING (admin) ====================

@dp.callback_query(F.data == "admin_group_post")
async def callback_admin_group_post(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Admins only", show_alert=True)
        return
    total_groups = await count_groups()
    await state.set_state(AdminStates.waiting_group_post)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="admin_panel")]])
    await callback.message.edit_text(
        f"📣 *Post to Groups/Channels*\n\n"
        f"Bot is currently added to {total_groups} group(s)/channel(s).\n\n"
        f"Send text, a photo, video, or file (with optional caption) as your next message.",
        reply_markup=kb, parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()


@dp.message(AdminStates.waiting_group_post)
async def process_group_post(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    if not has_sendable_content(message):
        await state.clear()
        await message.answer("❌ Empty message, post cancelled.")
        return

    await state.update_data(pending_message_obj=message, target="groups")
    await state.set_state(AdminStates.waiting_button_choice)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Add \"Open App\" button", callback_data="btn_choice_app")],
        [InlineKeyboardButton(text="🔗 Add custom link button", callback_data="btn_choice_custom")],
        [InlineKeyboardButton(text="🚫 No button", callback_data="btn_choice_none")],
    ])
    await message.answer("Add a button under this post?", reply_markup=kb)


# ==================== FORCE-JOIN ADMIN CONTROLS ====================

@dp.callback_query(F.data == "admin_forcejoin")
async def callback_admin_forcejoin(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Admins only", show_alert=True)
        return
    await callback.answer()
    fj = await get_force_join()
    channel_line = f"@{fj['channel_username']}" if fj.get("channel_username") else "Not set"
    try:
        await callback.message.edit_text(
            f"🔒 *Force Join Channel*\n\nCurrent channel: {channel_line}\n\n"
            f"When ON, users must join this channel before using the bot.\n"
            f"⚠️ The bot must be an *admin* in that channel to verify membership.",
            reply_markup=force_join_admin_keyboard(fj), parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"admin_forcejoin edit failed: {e}")


@dp.callback_query(F.data == "forcejoin_toggle")
async def callback_forcejoin_toggle(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Admins only", show_alert=True)
        return
    fj = await get_force_join()
    if not fj.get("channel_username"):
        await callback.answer("⚠️ Set a channel username first (✏️ Set Channel Username)", show_alert=True)
        return
    new_val = not fj.get("enabled", False)
    await update_force_join({"enabled": new_val})
    fj["enabled"] = new_val
    await callback.answer(f"Force Join → {'ON' if new_val else 'OFF'}")
    try:
        await callback.message.edit_reply_markup(reply_markup=force_join_admin_keyboard(fj))
    except Exception as e:
        logger.error(f"forcejoin_toggle edit failed: {e}")


@dp.callback_query(F.data == "forcejoin_set")
async def callback_forcejoin_set(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Admins only", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_force_join_channel)
    await callback.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="admin_panel")]])
    try:
        await callback.message.edit_text(
            "✏️ Send the channel *username* (without @), e.g. `nilo_cinema_channel`.\n\n"
            "⚠️ The bot must already be an admin of that channel.",
            reply_markup=kb, parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"forcejoin_set edit failed: {e}")


@dp.callback_query(F.data == "forcejoin_test")
async def callback_forcejoin_test(callback: types.CallbackQuery):
    """Force-join አለመስራት ላይ ትክክለኛውን ምክንያት ለ admin ግልጽ የሚያደርግ diagnostic።"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Admins only", show_alert=True)
        return

    fj = await get_force_join()
    channel = fj.get("channel_username")
    if not channel:
        await callback.answer("⚠️ No channel set yet.", show_alert=True)
        return

    try:
        me = await bot.get_me()
        bot_member = await bot.get_chat_member(f"@{channel}", me.id)
        if bot_member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
            await callback.answer(
                f"❌ Bot is in @{channel} but is NOT an admin there. "
                f"Force-join cannot verify membership until you make the bot an admin.",
                show_alert=True
            )
            return
        await callback.answer(f"✅ Bot is admin in @{channel} — force-join should work correctly.", show_alert=True)
    except Exception as e:
        await callback.answer(
            f"❌ Bot cannot access @{channel} at all (not added, or wrong username). "
            f"Error: {str(e)[:150]}",
            show_alert=True
        )


@dp.message(AdminStates.waiting_force_join_channel)
async def process_forcejoin_channel(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    await state.clear()
    username = (message.text or "").strip().lstrip("@")
    if not username:
        await message.answer("❌ Invalid username.")
        return
    await update_force_join({"channel_username": username})
    await message.answer(f"✅ Force-join channel set to @{username}")


@dp.callback_query(F.data == "forcejoin_set_youtube")
async def callback_forcejoin_set_youtube(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Admins only", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_youtube_url)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="admin_forcejoin")]])
    await callback.message.edit_text(
        "🔴 Send your full YouTube channel URL.\n\n"
        "⚠️ *Note:* Telegram bots cannot verify YouTube subscriptions — "
        "this button is shown as an optional \"also follow us\" link and does not block access.",
        reply_markup=kb, parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()


@dp.message(AdminStates.waiting_youtube_url)
async def process_youtube_url(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    await state.clear()
    url = (message.text or "").strip()
    if not url.startswith("http"):
        await message.answer("❌ Invalid URL.")
        return
    await update_force_join({"youtube_url": url})
    await message.answer("✅ YouTube link saved.")


@dp.callback_query(F.data == "forcejoin_set_tiktok")
async def callback_forcejoin_set_tiktok(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Admins only", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_tiktok_url)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="admin_forcejoin")]])
    await callback.message.edit_text(
        "🎵 Send your full TikTok profile URL.\n\n"
        "⚠️ *Note:* TikTok has no public API for verifying follows — "
        "this button is shown as an optional \"also follow us\" link and does not block access.",
        reply_markup=kb, parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()


@dp.message(AdminStates.waiting_tiktok_url)
async def process_tiktok_url(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    await state.clear()
    url = (message.text or "").strip()
    if not url.startswith("http"):
        await message.answer("❌ Invalid URL.")
        return
    await update_force_join({"tiktok_url": url})
    await message.answer("✅ TikTok link saved.")


# ==================== GROUP/CHANNEL MEMBERSHIP TRACKING ====================

@dp.my_chat_member()
async def on_bot_membership_changed(event: types.ChatMemberUpdated):
    if event.chat.type == ChatType.PRIVATE:
        return  # የግል chat ነው፣ group/channel አይደለም

    new_status = event.new_chat_member.status
    if new_status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR):
        await upsert_group(event.chat)
        logger.info(f"Bot added to {event.chat.type}: {event.chat.title} ({event.chat.id})")
    elif new_status in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED):
        await remove_group(event.chat.id)
        logger.info(f"Bot removed from {event.chat.type}: {event.chat.title} ({event.chat.id})")


# ==================== AUTO-POST NEW MOVIES ====================

async def fetch_top_rated_movies() -> list:
    """'top movie ብቻ' ስለተባለ (አዳዲስ ፊልሞች ቶሎ TMDB ላይ ስለማይጨመሩ)፣ ከ
    now_playing ይልቅ top_rated ሁልጊዜ በቂ ውጤት ስለሚሰጥ እንጠቀማለን።"""
    if not TMDB_API_KEY:
        return []
    url = f"https://api.themoviedb.org/3/movie/top_rated?api_key={TMDB_API_KEY}&language=en-US&page=1"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                return data.get("results", [])
    except Exception as e:
        logger.error(f"TMDB fetch failed: {e}")
        return []


async def fetch_tmdb_details(media_type: str, tmdb_id: int) -> dict | None:
    """ለ inline-share ካርድ (poster+ርዕስ+ደረጃ) ነጠላ ፊልም/ተከታታይ መረጃ ከ TMDB ያመጣል።"""
    if not TMDB_API_KEY:
        return None
    url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}?api_key={TMDB_API_KEY}&language=en-US"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()
    except Exception as e:
        logger.error(f"TMDB details fetch failed: {e}")
        return None


# ==================== SHARE VIA INLINE MODE ====================
# Mini App ላይ "Share" ሲነኩ tg.switchInlineQuery("movie_123",...) ይጠራል -
# ተጠቃሚው chat ሲመርጥ Telegram ይህን handler ይጠራል፣ እኛም ፖስተር+ርዕስ+
# "▶️ Open Mini App" ቁልፍ ያለበት ካርድ እንመልሳለን። ማስታወሻ: ይህ እንዲሰራ
# @BotFather ላይ /setinline ለዚህ bot መንቃት አለበት (አንድ ጊዜ ብቻ የሚደረግ ውቅር)።
@dp.inline_query()
async def handle_inline_query(inline_query: InlineQuery):
    query = inline_query.query.strip()
    parts = query.split("_", 1)
    if len(parts) != 2 or parts[0] not in ("movie", "tv") or not parts[1].isdigit():
        await inline_query.answer([], cache_time=1)
        return

    media_type, tmdb_id = parts[0], int(parts[1])
    details = await fetch_tmdb_details(media_type, tmdb_id)
    if not details:
        await inline_query.answer([], cache_time=1)
        return

    title = details.get("title") or details.get("name") or "Unknown"
    overview = (details.get("overview") or "")[:150]
    poster_path = details.get("poster_path")
    rating = details.get("vote_average") or 0
    year = (details.get("release_date") or details.get("first_air_date") or "")[:4]

    caption = f"🎬 *{title}* ({year})\n⭐ {rating:.1f}/10\n\n{overview}"
    # web_app ቁልፍ inline query results ውስጥ ጨርሶ አይፈቀድም (Telegram
    # "BUTTON_TYPE_INVALID" ይላል) - ስለዚህ URL deep-link ብቻ እንጠቀማለን፣
    # ማንኛውም ሰው (የላከው ብቻ ሳይሆን) ሲነካው ወደ bot ገብቶ Mini App ይከፈትለታል።
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Open Mini App", url=f"https://t.me/{BOT_USERNAME}?start={media_type}_{tmdb_id}")]
    ])

    if poster_path:
        photo_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
        result = InlineQueryResultPhoto(
            id=str(tmdb_id),
            photo_url=photo_url,
            thumbnail_url=photo_url,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb,
        )
    else:
        result = InlineQueryResultArticle(
            id=str(tmdb_id),
            title=title,
            description=overview,
            input_message_content=InputTextMessageContent(message_text=caption, parse_mode=ParseMode.MARKDOWN),
            reply_markup=kb,
        )

    await inline_query.answer([result], cache_time=10, is_personal=True)


async def auto_post_new_movies():
    movies = await fetch_top_rated_movies()
    if not movies:
        return

    groups = await groups_col.find({}, {"_id": 1}).to_list(length=None)
    users = await users_col.find({}, {"_id": 1}).to_list(length=None)
    if not groups and not users:
        return  # ምንም ተቀባይ ከሌለ መልቀቅ ትርጉም የለውም

    posted_count = 0
    for movie in movies:
        if posted_count >= AUTO_POST_MAX_PER_RUN:
            break
        tmdb_id = movie.get("id")
        already = await posted_movies_col.find_one({"_id": tmdb_id})
        if already:
            continue

        title = movie.get("title", "Unknown")
        overview = (movie.get("overview") or "")[:200]
        poster_path = movie.get("poster_path")
        rating = movie.get("vote_average", 0)
        photo_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None

        caption = f"🎬 *{title}*\n\n⭐ {rating:.1f}/10\n\n{overview}{'...' if len(movie.get('overview', '')) > 200 else ''}"

        # groups/channels ውስጥ web_app ቁልፍ ስለሚታገድ URL deep-link እንጠቀማለን
        group_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Play Now", url=f"https://t.me/{BOT_USERNAME}?start=movie_{tmdb_id}")]
        ])
        # ተመዝጋቢ users ግን ቀድሞ bot-ውን private chat ውስጥ ስላናገሩት web_app
        # ቁልፍ በቀጥታ መጠቀም እንችላለን - Mini App በአንድ ጠቅታ ይከፈትላቸዋል
        user_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Play Now", web_app=WebAppInfo(url=f"{WEBAPP_URL}?movie={tmdb_id}&type=movie"))]
        ])

        for g in groups:
            try:
                if photo_url:
                    await bot.send_photo(g["_id"], photo=photo_url, caption=caption, reply_markup=group_kb, parse_mode=ParseMode.MARKDOWN)
                else:
                    await bot.send_message(g["_id"], caption, reply_markup=group_kb, parse_mode=ParseMode.MARKDOWN)
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Auto-post failed for group {g['_id']}: {e}")

        for u in users:
            try:
                if photo_url:
                    await bot.send_photo(u["_id"], photo=photo_url, caption=caption, reply_markup=user_kb, parse_mode=ParseMode.MARKDOWN)
                else:
                    await bot.send_message(u["_id"], caption, reply_markup=user_kb, parse_mode=ParseMode.MARKDOWN)
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"Auto-post failed for user {u['_id']}: {e}")

        await posted_movies_col.insert_one({"_id": tmdb_id, "title": title, "posted_at": now_iso()})
        posted_count += 1


async def auto_post_loop():
    # ቦት ገና ሲነሳ ወዲያውኑ ላለመላክ ትንሽ ጠብቅ
    await asyncio.sleep(60)
    while True:
        try:
            await auto_post_new_movies()
        except Exception as e:
            logger.error(f"auto_post_loop error: {e}")
        await asyncio.sleep(AUTO_POST_INTERVAL_HOURS * 3600)


# ==================== ADMIN TEXT COMMANDS (backup, still work) ====================

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ You are not an admin!")
        return
    total = await count_users()
    online = await count_online()
    active_24h = await count_active_24h()
    settings = await get_settings()
    await message.answer(
        f"👥 Total: {total}\n🟢 Online: {online}\n🟡 24h Active: {active_24h}\n🎬 Plays: {settings.get('total_plays', 0)}"
    )


@dp.message(Command("broadcast"))
async def cmd_broadcast_hint(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "📢 Use the *Admin Panel → Broadcast to Users* button instead — "
        "it now supports text, photos, videos, and files.",
        parse_mode=ParseMode.MARKDOWN
    )


# ==================== WEB APP DATA HANDLER ====================

@dp.message(F.web_app_data)
async def handle_web_app_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        action = data.get("action")
        user_id = message.from_user.id

        await touch_user(user_id)

        if action == "play":
            await users_col.update_one({"_id": user_id}, {"$inc": {"plays": 1}})
            await inc_stat("total_plays", 1)

        elif action == "ad_view":
            await users_col.update_one({"_id": user_id}, {"$inc": {"ad_views": 1}})
            await inc_stat("total_ad_views", 1)

    except Exception as e:
        logger.error(f"WebApp data error: {e}")


# ==================== HELPER FUNCTIONS ====================

def get_user_rank(referral_count: int) -> str:
    if referral_count >= 50: return "👑 Legend"
    elif referral_count >= 20: return "💎 Diamond"
    elif referral_count >= 10: return "🥇 Gold"
    elif referral_count >= 5: return "🥈 Silver"
    elif referral_count >= 1: return "🥉 Bronze"
    return "🆕 Newbie"


async def set_menu_button():
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="🎬 Nilo Cinema", web_app=WebAppInfo(url=WEBAPP_URL))
        )
        logger.info("Menu button set successfully")
    except Exception as e:
        logger.error(f"Failed to set menu button: {e}")


# ==================== MAIN ====================

async def main():
    global BOT_USERNAME
    if not MONGO_URI:
        logger.warning("MONGO_URI is not set! Set it in Railway environment variables.")
    if not TMDB_API_KEY:
        logger.warning("TMDB_API_KEY is not set — auto-posting new movies will be disabled.")
    await ensure_settings()
    me = await bot.get_me()
    BOT_USERNAME = me.username
    await start_web_server()
    await set_menu_button()
    asyncio.create_task(auto_post_loop())
    logger.info("Bot started!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
