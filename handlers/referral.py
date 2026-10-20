import urllib.parse
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import settings
import database as db

router = Router()

@router.callback_query(F.data == "referral_menu")
async def handle_referral_menu(call: CallbackQuery, bot: Bot):
    user_id = call.from_user.id
    user = await db.get_user(user_id) or {}
    
    bot_info = await bot.get_me()
    bot_username = bot_info.username or "OcrPersianBot"
    
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    bonus = await db.get_setting("referral_bonus", str(settings.REFERRAL_BONUS_CREDITS))
    
    share_banner = (
        "🚀 سریع‌ترین ربات رایگان تبدیل عکس، جزوه و PDF به متن و فایل Word!\n\n"
        "بدون نیاز به تایپ دستی، فقط عکس کتاب یا جزوت رو بفرست تا فوری تحویل بگیری:\n"
        f"{ref_link}"
    )
    share_url = f"https://t.me/share/url?url={urllib.parse.quote(ref_link)}&text={urllib.parse.quote(share_banner)}"

    text = (
        "👥 **سیستم زیرمجموعه‌گیری و دعوت دوستان**\n\n"
        f"🎁 با دعوت از هر یک از دوستان، همکلاسی‌ها یا همکاران، **{bonus} اعتبار تبدیل رایگان** به حسابتان اضافه می‌شود!\n\n"
        f"📊 **آمار دعوت‌های شما:**\n"
        f"▫️ تعداد افراد دعوت‌شده: **{user.get('ref_count', 0)} نفر**\n"
        f"▫️ پاداش‌های دریافتی: **{user.get('ref_count', 0) * int(bonus)} صفحه**\n\n"
        "🔗 **لینک اختصاصی شما:**\n"
        f"`{ref_link}`\n\n"
        "👇 با زدن دکمه زیر می‌توانید این پیام را مستقیماً برای دوستان یا گروه‌های دانشگاهی فوروارد کنید:"
    )

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 ارسال لینک به دوستان و گروه‌ها", url=share_url)],
            [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
        ]
    )

    await call.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
