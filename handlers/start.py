from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from config import settings
import database as db
import growth_manager as growth

router = Router()

def get_main_menu_markup(is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="📸 تبدیل عکس به متن", callback_data="guide_photo"),
            InlineKeyboardButton(text="📄 تبدیل PDF به ورد", callback_data="guide_pdf")
        ],
        [
            InlineKeyboardButton(text="🎁 دریافت اعتبار رایگان (کد اینستاگرام)", callback_data="instagram_menu"),
        ],
        [
            InlineKeyboardButton(text="👥 زیرمجموعه‌گیری و دعوت دوستان", callback_data="referral_menu"),
            InlineKeyboardButton(text="👤 حساب کاربری من", callback_data="profile_menu")
        ],
        [
            InlineKeyboardButton(text="💡 راهنما و ترفندهای وضوح اسکن", callback_data="help_menu")
        ]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="⚙️ پنل مدیریت (ادمین)", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(CommandStart())
async def handle_start(message: Message, bot: Bot):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Check referral code from deep link /start ref_12345
    ref_by = None
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        ref_str = args[1].replace("ref_", "")
        if ref_str.isdigit():
            ref_by = int(ref_str)

    user = await db.register_or_update_user(user_id, username, first_name, ref_by)
    
    # Check channel force-join
    joined, missing = await growth.check_all_force_channels(bot, user_id)
    if not joined:
        text = (
            f"سلام {first_name} عزیز! به **ربات تبدیل عکس و جزوه به متن (OCR)** خوش آمدید 🌸\n\n"
            "برای استفاده کاملاً رایگان و نامحدود از امکانات ربات، لطفاً ابتدا در کانال‌های رسمی ما عضو شوید:\n\n"
            "👇 پس از عضویت، روی دکمه «تأیید عضویت و ادامه» بزنید:"
        )
        await message.answer(text, reply_markup=growth.get_force_join_markup(missing), parse_mode="Markdown")
        return

    is_admin = user_id in settings.admin_id_list
    welcome_text = (
        f"سلام {first_name} گرامی! به **سریع‌ترین ربات رایگان OCR فارسی و انگلیسی** خوش آمدید 🚀\n\n"
        "✨ **امکانات ویژه:**\n"
        "▫️ تبدیل عکس کتاب، جزوه و دست‌نویس به متن تایپ شده\n"
        "▫️ تبدیل فایل‌های چند صفحه‌ای PDF به متن\n"
        "▫️ خروجی مستقیم فایل Word (.docx) و متنی (.txt)\n"
        "▫️ فیلترهای هوشمند ضدسایه و افزایش وضوح\n\n"
        f"💎 **اعتبار فعلی شما:** {user.get('credits', 15)} صفحه رایگان\n\n"
        "👇 همین حالا می‌توانید یک **عکس یا فایل PDF** برای ربات بفرستید:"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu_markup(is_admin), parse_mode="Markdown")

@router.callback_query(F.data == "check_join_again")
async def handle_check_join_again(call: CallbackQuery, bot: Bot):
    user_id = call.from_user.id
    growth.clear_user_cache(user_id)
    
    joined, missing = await growth.check_all_force_channels(bot, user_id)
    if not joined:
        await call.answer("❌ شما هنوز در تمام کانال‌ها عضو نشده‌اید!", show_alert=True)
        try:
            await call.message.edit_reply_markup(reply_markup=growth.get_force_join_markup(missing))
        except Exception:
            pass
        return

    await call.answer("✅ عضویت شما با موفقیت تأیید شد!", show_alert=False)
    user = await db.get_user(user_id) or {}
    is_admin = user_id in settings.admin_id_list
    welcome_text = (
        "🎉 **عضویت شما تأیید شد!**\n\n"
        "ربات آماده به کار است. کافی است هر عکس یا فایل PDF که می‌خواهید را برای ربات ارسال کنید تا متن آن را تحویل بگیرید."
    )
    await call.message.edit_text(welcome_text, reply_markup=get_main_menu_markup(is_admin), parse_mode="Markdown")

@router.callback_query(F.data == "main_menu")
async def handle_main_menu(call: CallbackQuery):
    user_id = call.from_user.id
    user = await db.get_user(user_id) or {}
    is_admin = user_id in settings.admin_id_list
    text = (
        "🏠 **منوی اصلی ربات OCR**\n\n"
        f"👤 کاربر: {call.from_user.first_name}\n"
        f"💎 اعتبار شما: {user.get('credits', 0)} صفحه\n"
        f"👥 تعداد دعوت‌ها: {user.get('ref_count', 0)} نفر\n\n"
        "یک عکس یا سند PDF بفرستید یا از گزینه‌های زیر استفاده کنید:"
    )
    await call.message.edit_text(text, reply_markup=get_main_menu_markup(is_admin), parse_mode="Markdown")

@router.callback_query(F.data == "profile_menu")
async def handle_profile(call: CallbackQuery):
    user_id = call.from_user.id
    user = await db.get_user(user_id) or {}
    vip_status = "⭐️ کاربر ویژه (VIP نامحدود)" if user.get("is_vip") else "معمولی (با اعتبار روزانه)"
    text = (
        "👤 **اطلاعات حساب کاربری شما**\n\n"
        f"▫️ شناسه کاربری: `{user_id}`\n"
        f"▫️ نام: {user.get('first_name', '-')}\n"
        f"▫️ وضعیت حساب: {vip_status}\n"
        f"▫️ موجودی اعتبار: **{user.get('credits', 0)} صفحه**\n"
        f"▫️ کل تبدیل‌های انجام شده: **{user.get('conversions_count', 0)} سند**\n"
        f"▫️ دوستان دعوت‌شده: **{user.get('ref_count', 0)} نفر**\n\n"
        "💡 برای دریافت اعتبار رایگان بیشتر می‌توانید از بخش **زیرمجموعه‌گیری** یا **کد استوری اینستاگرام** استفاده کنید."
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 شارژ رایگان با کد اینستاگرام", callback_data="instagram_menu")],
        [InlineKeyboardButton(text="👥 دریافت لینک دعوت اختصاصی", callback_data="referral_menu")],
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="main_menu")]
    ])
    await call.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")

@router.callback_query(F.data == "help_menu")
async def handle_help(call: CallbackQuery):
    text = (
        "💡 **راهنمای استفاده و ترفندهای افزایش دقت OCR:**\n\n"
        "1️⃣ **نور مناسب:** عکس را در محیط با نور کافی و بدون سایه شدید گوشی بگیرید.\n"
        "2️⃣ **زاویه مستقیم:** دوربین را درست روبه‌روی صفحه با کمترین کجی نگه دارید.\n"
        "3️⃣ **وضوح و فوکوس:** مطمئن شوید تصویر تار نیست و حروف واضح دیده می‌شوند.\n"
        "4️⃣ **فرمت فایل:** ارسال تصویر به عنوان «فایل/Document» به دلیل حفظ کیفیت اصلی، نتیجه بهتری نسبت به عکس فشرده شده می‌دهد.\n"
        "5️⃣ **فایل PDF:** فایل‌های پی‌دی‌اف تا ۱۵ صفحه در هر بار به راحتی پردازش و به Word تبدیل می‌شوند.\n\n"
        "🛠 هرگونه انتقاد یا پیشنهاد را می‌توانید با پشتیبانی در میان بگذارید."
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="main_menu")]
    ])
    await call.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")

@router.callback_query(F.data.in_(["guide_photo", "guide_pdf"]))
async def handle_quick_guide(call: CallbackQuery):
    tip = (
        "📸 **برای تبدیل عکس:** کافی است عکس کتاب، جزوه، مجله یا صفحه مورد نظرتان را همین الان ارسال کنید!\n\n"
        "📄 **برای تبدیل PDF:** فایل PDF مورد نظرتان را در چت آپلود کنید تا صفحات آن اسکن و به متن و فایل Word تبدیل شود."
    )
    await call.answer(tip, show_alert=True)
