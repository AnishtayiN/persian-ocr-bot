from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import settings
import database as db

router = Router()

class InstagramStates(StatesGroup):
    waiting_for_code = State()

@router.callback_query(F.data == "instagram_menu")
async def handle_instagram_menu(call: CallbackQuery):
    ig_url = await db.get_setting("ig_page_url", settings.INSTAGRAM_PAGE_URL)
    ig_user = await db.get_setting("ig_username", settings.INSTAGRAM_USERNAME)
    bonus = await db.get_setting("ig_bonus", str(settings.INSTAGRAM_BONUS_CREDITS))
    
    text = (
        "📸 **دریافت اعتبار هدیه با فالو و استوری اینستاگرام**\n\n"
        f"پیج اینستاگرام ما را دنبال کنید: **@{ig_user}**\n\n"
        "💡 **چطور هر روز اعتبار رایگان بگیریم؟**\n"
        f"ما هر روز داخل **استوری‌های پیج اینستاگرام** یک کد هدیه اختصاصی قرار می‌دهیم!\n"
        f"با وارد کردن این کد، حساب شما فوراً **{bonus} صفحه شارژ رایگان** دریافت می‌کند.\n\n"
        "👇 برای شروع روی دکمه‌های زیر کلیک کنید:"
    )
    
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"📸 ورود به پیج @{ig_user}", url=ig_url)],
            [InlineKeyboardButton(text="🎁 وارد کردن کد استوری امروز", callback_data="enter_ig_code")],
            [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
        ]
    )
    await call.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")

@router.callback_query(F.data == "enter_ig_code")
async def handle_enter_code_prompt(call: CallbackQuery, state: FSMContext):
    await state.set_state(InstagramStates.waiting_for_code)
    text = (
        "🎁 **وارد کردن کد مخفی استوری اینستاگرام:**\n\n"
        "لطفاً کد ۵ الی ۸ رقمی که در استوری امروز پیج قرار داده شده را تایپ و ارسال کنید:\n\n"
        "*(برای لغو ارسال، عبارت /cancel را بفرستید)*"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ انصراف", callback_data="cancel_ig_state")]
    ])
    await call.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")

@router.callback_query(F.data == "cancel_ig_state")
async def handle_cancel_ig(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer("عملیات لغو شد.")
    # Return to Instagram menu
    await handle_instagram_menu(call)

@router.message(InstagramStates.waiting_for_code)
async def process_ig_code_input(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/"):
        await state.clear()
        await message.answer("عملیات لغو شد.")
        return

    user_code = message.text.strip()
    user_id = message.from_user.id
    
    success, resp_text = await db.check_and_apply_ig_code(user_id, user_code)
    await state.clear()
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 تبدیل یک عکس جدید", callback_data="guide_photo")],
        [InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="main_menu")]
    ])
    
    await message.answer(resp_text, reply_markup=markup, parse_mode="Markdown")
