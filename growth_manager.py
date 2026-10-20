import time
from typing import List, Tuple, Dict, Any
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import settings
import database as db

# In-memory cache for channel membership: { (user_id, channel_id): (is_member, timestamp) }
MEMBERSHIP_CACHE: Dict[Tuple[int, str], Tuple[bool, float]] = {}
CACHE_TTL = 180  # 3 minutes

async def is_user_channel_member(bot: Bot, user_id: int, channel_id: str) -> bool:
    """Check if user is a member of the given channel with caching."""
    cache_key = (user_id, channel_id)
    now = time.time()
    
    if cache_key in MEMBERSHIP_CACHE:
        is_mem, ts = MEMBERSHIP_CACHE[cache_key]
        if now - ts < CACHE_TTL:
            return is_mem

    try:
        chat_member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        # Statuses that mean user is inside the chat
        is_member = chat_member.status in ["creator", "administrator", "member", "restricted"]
    except Exception as e:
        # If bot is not admin in channel or error, allow user through to avoid blocking
        print(f"Warning: Channel check error for {channel_id}: {e}")
        is_member = True

    MEMBERSHIP_CACHE[cache_key] = (is_member, now)
    return is_member

def clear_user_cache(user_id: int):
    """Clear cache for a specific user so re-check is fresh."""
    keys_to_delete = [k for k in MEMBERSHIP_CACHE if k[0] == user_id]
    for k in keys_to_delete:
        MEMBERSHIP_CACHE.pop(k, None)

async def check_all_force_channels(bot: Bot, user_id: int) -> Tuple[bool, List[Dict[str, str]]]:
    """Check all registered force-join channels. Returns (all_joined, missing_channels)."""
    # 1. Get channels from database
    channels = await db.get_active_channels()
    
    # 2. If no channels in DB, fall back to config settings
    if not channels and settings.force_channel_list:
        channels = [
            {"channel_id": ch, "title": "کانال رسمی", "invite_link": settings.FORCE_JOIN_LINKS}
            for ch in settings.force_channel_list
        ]

    missing = []
    for ch in channels:
        ch_id = ch["channel_id"]
        joined = await is_user_channel_member(bot, user_id, ch_id)
        if not joined:
            missing.append(ch)

    return (len(missing) == 0, missing)

def get_force_join_markup(missing_channels: List[Dict[str, str]]) -> InlineKeyboardMarkup:
    """Build beautiful keyboard with join buttons and check button."""
    buttons = []
    for idx, ch in enumerate(missing_channels, start=1):
        title = ch.get("title") or f"کانال {idx}"
        link = ch.get("invite_link") or f"https://t.me/{ch['channel_id'].replace('@', '')}"
        buttons.append([InlineKeyboardButton(text=f"📢 عضویت در {title}", url=link)])

    # Re-check button
    buttons.append([InlineKeyboardButton(text="🔄 تأیید عضویت و ادامه", callback_data="check_join_again")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_instagram_markup(ig_url: str) -> InlineKeyboardMarkup:
    """Build keyboard for Instagram engagement."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📸 مشاهده پیج اینستاگرام ما", url=ig_url)],
            [InlineKeyboardButton(text="🎁 ثبت کد استوری امروز (+۲۰ اعتبار)", callback_data="enter_ig_code")],
            [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
        ]
    )

def get_referral_share_markup(bot_username: str, user_id: int) -> InlineKeyboardMarkup:
    """Build keyboard for viral referral sharing."""
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    share_text = (
        "🔥 سریع‌ترین ربات رایگان تبدیل عکس و PDF به متن و فایل ورد (Word)!\n\n"
        "دیگه نیاز به تایپ دستی جزوه و کتاب نداری. همین الان رایگان امتحان کن:\n"
        f"{ref_link}"
    )
    import urllib.parse
    share_url = f"https://t.me/share/url?url={urllib.parse.quote(ref_link)}&text={urllib.parse.quote(share_text)}"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 اشتراک‌گذاری با دوستان در تلگرام", url=share_url)],
            [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
        ]
    )
