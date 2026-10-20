import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import settings
import database as db

router = Router()

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_channel_info = State()
    waiting_for_new_ig_code = State()
    waiting_for_credit_info = State()

def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_id_list

def get_admin_main_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 آمار کلی ربات", callback_data="admin_stats"),
                InlineKeyboardButton(text="📢 ارسال همگانی", callback_data="admin_broadcast")
            ],
            [
                InlineKeyboardButton(text="📢 مدیریت کانال‌های جوین اجباری", callback_data="admin_channels"),
            ],
            [
                InlineKeyboardButton(text="📸 تغییر کد استوری اینستاگرام", callback_data="admin_set_ig_code"),
                InlineKeyboardButton(text="🎁 افزایش اعتبار کاربر", callback_data="admin_give_credits")
            ],
            [
                InlineKeyboardButton(text="🔙 بازگشت به منوی کاربر", callback_data="main_menu")
            ]
        ]
    )

@router.message(Command("admin"))
async def handle_admin_command(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    text = (
        "👑 **به پنل مدیریت ربات OCR خوش آمدید!**\n\n"
        "از طریق این پنل می‌توانید کانال‌های جوین اجباری، کدهای جذب اینستاگرام و آمار کاربران را مدیریت کنید:"
    )
    await message.answer(text, reply_markup=get_admin_main_markup(), parse_mode="Markdown")

@router.callback_query(F.data == "admin_panel")
async def handle_admin_panel_callback(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("⛔️ دسترسی غیرمجاز!", show_alert=True)
        return
    
    text = (
        "👑 **پنل مدیریت ربات OCR**\n\n"
        "بخش مورد نظر خود را انتخاب کنید:"
    )
    await call.message.edit_text(text, reply_markup=get_admin_main_markup(), parse_mode="Markdown")

@router.callback_query(F.data == "admin_stats")
async def handle_admin_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    
    stats = await db.get_admin_stats()
    text = (
        "📊 **گزارش لحظه‌ای سیستم:**\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"👥 کل کاربران: **{stats['total_users']:,} نفر**\n"
        f"🆕 کاربران جدید امروز: **{stats['users_today']:,} نفر**\n"
        f"📄 کل فایل‌ها/عکس‌های تبدیل شده: **{stats['total_conversions']:,} عدد**\n"
        f"📑 کل صفحات اسکن‌شده: **{stats['total_pages']:,} صفحه**\n"
        f"⚡️ تبدیل‌های امروز: **{stats['conversions_today']:,} بار**\n"
        f"📢 کانال‌های جوین اجباری فعال: **{stats['channels_count']} کانال**\n"
        "━━━━━━━━━━━━━━━━━━━"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به پنل ادمین", callback_data="admin_panel")]
    ])
    await call.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")

@router.callback_query(F.data == "admin_channels")
async def handle_admin_channels(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    channels = await db.get_active_channels()
    if not channels:
        ch_list_str = "هیچ کانالی در دیتابیس ثبت نشده است (تنظیمات از فایل config خوانده می‌شود)."
    else:
        ch_list_str = "\n".join([f"▫️ {c['title']} | `{c['channel_id']}`" for c in channels])

    text = (
        "📢 **مدیریت کانال‌های جوین اجباری (Force Join):**\n\n"
        f"لیست کانال‌های فعال فعلی:\n{ch_list_str}\n\n"
        "⚠️ توجه: برای اینکه ربات بتواند عضویت کاربران را چک کند، حتماً ربات را در کانال **ادمین (Admin)** کنید."
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ افزودن کانال جدید", callback_data="admin_add_channel")],
        [InlineKeyboardButton(text="🔙 بازگشت به پنل ادمین", callback_data="admin_panel")]
    ])
    await call.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")

@router.callback_query(F.data == "admin_add_channel")
async def handle_add_channel_prompt(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    await state.set_state(AdminStates.waiting_for_channel_info)
    text = (
        "➕ **افزودن کانال جدید:**\n\n"
        "اطلاعات کانال را در یک خط با فرمت زیر ارسال کنید:\n\n"
        "`شناسه_کانال|عنوان_کانال|لینک_عضویت`\n\n"
        "مثال:\n"
        "`@MyNewChannel|کانال رسمی فناوری|https://t.me/MyNewChannel`\n\n"
        "*(برای لغو /cancel را ارسال کنید)*"
    )
    await call.message.edit_text(text, parse_mode="Markdown")

@router.message(AdminStates.waiting_for_channel_info)
async def process_add_channel_input(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text.startswith("/"):
        await state.clear()
        await message.answer("عملیات لغو شد.")
        return

    parts = message.text.split("|")
    if len(parts) != 3:
        await message.answer("❌ فرمت ورودی اشتباه است. لطفاً دقیقاً مانند مثال ارسال کنید:\n`@ChannelId|Title|Link`")
        return

    ch_id, title, link = parts[0].strip(), parts[1].strip(), parts[2].strip()
    success = await db.add_channel(ch_id, title, link)
    await state.clear()

    if success:
        await message.answer(f"✅ کانال `{title}` با موفقیت اضافه شد و از این لحظه در جوین اجباری قرار گرفت!")
    else:
        await message.answer("❌ خطا در ثبت کانال!")

@router.callback_query(F.data == "admin_set_ig_code")
async def handle_set_ig_code_prompt(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    current = await db.get_setting("daily_ig_code", settings.DAILY_INSTAGRAM_CODE)
    await state.set_state(AdminStates.waiting_for_new_ig_code)
    text = (
        "📸 **تغییر کد مخفی استوری اینستاگرام:**\n\n"
        f"کد فعلی: `{current}`\n\n"
        "لطفاً کد جدیدی که امروز در استوری اینستاگرام قرار می‌دهید را ارسال کنید:\n"
        "*(مثلاً: GOLD2026 یا OCR_DAY2)*"
    )
    await call.message.edit_text(text, parse_mode="Markdown")

@router.message(AdminStates.waiting_for_new_ig_code)
async def process_new_ig_code(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text.startswith("/"):
        await state.clear()
        await message.answer("عملیات لغو شد.")
        return

    new_code = message.text.strip().upper()
    await db.set_setting("daily_ig_code", new_code)
    await state.clear()
    await message.answer(f"✅ کد جدید اینستاگرام با موفقیت به `{new_code}` تغییر یافت!\nکاربران با وارد کردن این کد شارژ هدیه می‌گیرند.")

@router.callback_query(F.data == "admin_broadcast")
async def handle_broadcast_prompt(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    await state.set_state(AdminStates.waiting_for_broadcast)
    text = (
        "📢 **ارسال همگانی به تمام کاربران:**\n\n"
        "پیام متنی یا عکسی که می‌خواهید برای همه ارسال شود را بفرستید:\n"
        "*(برای لغو /cancel را ارسال فرمایید)*"
    )
    await call.message.edit_text(text, parse_mode="Markdown")

@router.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    if message.text and message.text.startswith("/"):
        await state.clear()
        await message.answer("ارسال همگانی لغو شد.")
        return

    user_ids = await db.get_all_user_ids()
    await state.clear()
    
    status_msg = await message.answer(f"🚀 شروع ارسال پیام به {len(user_ids)} کاربر...")
    sent, failed = 0, 0

    for uid in user_ids:
        try:
            await message.send_copy(chat_id=uid)
            sent += 1
            await asyncio.sleep(0.04)  # Prevent flooding Telegram API
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"🏁 **ارسال همگانی به پایان رسید:**\n\n"
        f"✅ ارسال موفق: {sent}\n"
        f"❌ ناموفق (بلاک ربات یا خطای اکانت): {failed}"
    )

@router.callback_query(F.data == "admin_give_credits")
async def handle_give_credits_prompt(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    await state.set_state(AdminStates.waiting_for_credit_info)
    text = (
        "🎁 **افزایش دستی اعتبار کاربر:**\n\n"
        "آیدی عددی کاربر و تعداد اعتبار را با فاصله بفرستید:\n"
        "مثال:\n"
        "`123456789 50`\n"
        "*(برای لغو /cancel بفرستید)*"
    )
    await call.message.edit_text(text, parse_mode="Markdown")

@router.message(AdminStates.waiting_for_credit_info)
async def process_give_credits(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text.startswith("/"):
        await state.clear()
        await message.answer("عملیات لغو شد.")
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        await message.answer("❌ ورودی نامعتبر است. مثال: `123456789 50`")
        return

    target_id = int(parts[0])
    amount = int(parts[1])
    
    new_credits = await db.add_user_credits(target_id, amount)
    await state.clear()
    await message.answer(f"✅ با موفقیت {amount} اعتبار به کاربر `{target_id}` اضافه شد. موجودی جدید: {new_credits}")
