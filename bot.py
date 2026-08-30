import asyncio
import logging
import json
import os
from datetime import datetime, timedelta, timezone

import aiohttp
from aiohttp import web
from motor.motor_asyncio import AsyncIOMotorClient

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, MenuButtonWebApp
from aiogram.enums import ParseMode, ChatMemberStatus, ChatType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://web-production-edcca.up.railway.app/")
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


def force_join_keyboard(channel_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Join Channel", url=f"https://t.me/{channel_username}")],
        [InlineKeyboardButton(text="✅ I've Joined", callback_data="check_join")],
    ])


# ==================== INITIALIZE BOT ====================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class AdminStates(StatesGroup):
    waiting_broadcast = State()
    waiting_group_post = State()
    waiting_force_join_channel = State()


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


# ==================== KEYBOARDS ====================
def user_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Open Cinema Hub", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton(text="👥 Invite Friends", callback_data="invite")],
        [InlineKeyboardButton(text="📊 My Statistics", callback_data="my_stats")],
    ])


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Open Cinema Hub", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton(text="👥 Invite Friends", callback_data="invite")],
        [InlineKeyboardButton(text="📊 My Statistics", callback_data="my_stats")],
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
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Force Join: {status}", callback_data="forcejoin_toggle")],
        [InlineKeyboardButton(text="✏️ Set Channel Username", callback_data="forcejoin_set")],
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

    fj = await get_force_join()
    if fj.get("enabled") and fj.get("channel_username"):
        joined = await user_has_joined_channel(user_id, fj["channel_username"])
        if not joined:
            await message.answer(
                "🔒 *Join our channel first*\n\nTo use Nilo Cinema, please join our channel, then tap \"I've Joined\".",
                reply_markup=force_join_keyboard(fj["channel_username"]),
                parse_mode=ParseMode.MARKDOWN
            )
            return

    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].replace("ref_", ""))
        except ValueError:
            referrer_id = None

    welcome_text = await process_new_user_and_welcome(user, referrer_id)
    keyboard = admin_menu_keyboard() if is_admin(user_id) else user_menu_keyboard()
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)


@dp.callback_query(F.data == "check_join")
async def callback_check_join(callback: types.CallbackQuery):
    user = callback.from_user
    fj = await get_force_join()

    if fj.get("enabled") and fj.get("channel_username"):
        joined = await user_has_joined_channel(user.id, fj["channel_username"])
        if not joined:
            await callback.answer("❌ You haven't joined the channel yet.", show_alert=True)
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
    await callback.message.edit_text("🛠 *Admin Panel*", reply_markup=admin_panel_keyboard(), parse_mode=ParseMode.MARKDOWN)
    await callback.answer()


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
        "📢 *Broadcast*\n\nSend the message you want to broadcast to all users as your next message.",
        reply_markup=kb, parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()


@dp.message(AdminStates.waiting_broadcast)
async def process_broadcast(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    await state.clear()
    broadcast_text = message.text or ""
    if not broadcast_text.strip():
        await message.answer("❌ Empty message, broadcast cancelled.")
        return

    sent, failed = 0, 0
    cursor = users_col.find({}, {"_id": 1})
    async for u in cursor:
        try:
            await bot.send_message(u["_id"], f"📢 *Announcement*\n\n{broadcast_text}", parse_mode=ParseMode.MARKDOWN)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed += 1
            logger.error(f"Broadcast failed for {u['_id']}: {e}")

    await message.answer(f"✅ Sent: {sent}\n❌ Failed: {failed}")


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
        f"Send the text (or a photo with caption) you want posted there as your next message.",
        reply_markup=kb, parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()


@dp.message(AdminStates.waiting_group_post)
async def process_group_post(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    await state.clear()

    sent, failed = 0, 0
    cursor = groups_col.find({}, {"_id": 1})
    async for g in cursor:
        try:
            if message.photo:
                await bot.send_photo(g["_id"], photo=message.photo[-1].file_id, caption=message.caption or "", parse_mode=ParseMode.MARKDOWN)
            else:
                await bot.send_message(g["_id"], message.text or "", parse_mode=ParseMode.MARKDOWN)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed += 1
            logger.error(f"Group post failed for {g['_id']}: {e}")

    await message.answer(f"✅ Posted to: {sent}\n❌ Failed: {failed}")


# ==================== FORCE-JOIN ADMIN CONTROLS ====================

@dp.callback_query(F.data == "admin_forcejoin")
async def callback_admin_forcejoin(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Admins only", show_alert=True)
        return
    fj = await get_force_join()
    channel_line = f"@{fj['channel_username']}" if fj.get("channel_username") else "Not set"
    await callback.message.edit_text(
        f"🔒 *Force Join Channel*\n\nCurrent channel: {channel_line}\n\n"
        f"When ON, users must join this channel before using the bot.\n"
        f"⚠️ The bot must be an *admin* in that channel to verify membership.",
        reply_markup=force_join_admin_keyboard(fj), parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()


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
    await callback.message.edit_reply_markup(reply_markup=force_join_admin_keyboard(fj))
    await callback.answer(f"Force Join → {'ON' if new_val else 'OFF'}")


@dp.callback_query(F.data == "forcejoin_set")
async def callback_forcejoin_set(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Admins only", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_force_join_channel)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="admin_panel")]])
    await callback.message.edit_text(
        "✏️ Send the channel *username* (without @), e.g. `nilo_cinema_channel`.\n\n"
        "⚠️ The bot must already be an admin of that channel.",
        reply_markup=kb, parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()


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

async def fetch_now_playing_movies() -> list:
    if not TMDB_API_KEY:
        return []
    url = f"https://api.themoviedb.org/3/movie/now_playing?api_key={TMDB_API_KEY}&language=en-US&page=1"
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


async def auto_post_new_movies():
    movies = await fetch_now_playing_movies()
    if not movies:
        return

    groups = await groups_col.find({}, {"_id": 1}).to_list(length=None)
    if not groups:
        return  # ምንም group/channel ካልታከለ መልቀቅ ትርጉም የለውም

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

        caption = f"🎬 *{title}*\n\n⭐ {rating:.1f}/10\n\n{overview}{'...' if len(movie.get('overview', '')) > 200 else ''}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Play Now", web_app=WebAppInfo(url=f"{WEBAPP_URL}?movie={tmdb_id}"))]
        ])

        for g in groups:
            try:
                if poster_path:
                    await bot.send_photo(
                        g["_id"],
                        photo=f"https://image.tmdb.org/t/p/w500{poster_path}",
                        caption=caption, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await bot.send_message(g["_id"], caption, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Auto-post failed for group {g['_id']}: {e}")

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
async def cmd_broadcast(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    broadcast_text = message.text.replace("/broadcast", "").strip()
    if not broadcast_text:
        await message.answer("❌ Usage: /broadcast <message>")
        return
    sent, failed = 0, 0
    cursor = users_col.find({}, {"_id": 1})
    async for u in cursor:
        try:
            await bot.send_message(u["_id"], f"📢 *Announcement*\n\n{broadcast_text}", parse_mode=ParseMode.MARKDOWN)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed += 1
            logger.error(f"Failed to send to {u['_id']}: {e}")
    await message.answer(f"✅ Sent: {sent}\n❌ Failed: {failed}")


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
    if not MONGO_URI:
        logger.warning("MONGO_URI is not set! Set it in Railway environment variables.")
    if not TMDB_API_KEY:
        logger.warning("TMDB_API_KEY is not set — auto-posting new movies will be disabled.")
    await ensure_settings()
    await start_web_server()
    await set_menu_button()
    asyncio.create_task(auto_post_loop())
    logger.info("Bot started!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
