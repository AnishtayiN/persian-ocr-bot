import os
import uuid
import tempfile
import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from config import settings
import database as db
import growth_manager as growth
import ocr_engine

router = Router()

# In-memory storage for processed results to allow downloading word/txt: { session_id: {"text": str, "orig_path": str} }
OCR_SESSIONS = {}

def get_ocr_result_markup(session_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 دانلود فایل Word (.docx)", callback_data=f"get_docx:{session_id}"),
                InlineKeyboardButton(text="📄 دانلود فایل Text (.txt)", callback_data=f"get_txt:{session_id}")
            ],
            [
                InlineKeyboardButton(text="🔍 تقویت مجدد کنتراست (ضدسایه)", callback_data=f"re_contrast:{session_id}"),
            ],
            [
                InlineKeyboardButton(text="🎁 دریافت شارژ رایگان", callback_data="instagram_menu"),
                InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="main_menu")
            ]
        ]
    )

@router.message(F.photo)
async def handle_photo(message: Message, bot: Bot):
    user_id = message.from_user.id
    
    # 1. Force Join Check
    joined, missing = await growth.check_all_force_channels(bot, user_id)
    if not joined:
        text = (
            "⚠️ **برای استفاده از ربات باید در کانال‌های زیر عضو باشید:**\n\n"
            "لطفاً عضو شوید و سپس دکمه «تأیید عضویت و ادامه» را بزنید:"
        )
        await message.answer(text, reply_markup=growth.get_force_join_markup(missing), parse_mode="Markdown")
        return

    # 2. Check and deduct credits
    has_credits = await db.deduct_user_credits(user_id, 1)
    if not has_credits:
        text = (
            "❌ **اعتبار رایگان شما تمام شده است!**\n\n"
            "برای ادامه تبدیل عکس‌ها می‌توانید:\n"
            "1️⃣ **کد امروز استوری اینستاگرام** را ثبت کنید (+۲۰ اعتبار فوری)\n"
            "2️⃣ دوستان خود را با لینک دعوت به ربات بیاورید (+۱۰ اعتبار به ازای هر دوست)"
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 ثبت کد استوری اینستاگرام", callback_data="instagram_menu")],
            [InlineKeyboardButton(text="👥 دریافت لینک دعوت", callback_data="referral_menu")],
        ])
        await message.answer(text, reply_markup=markup, parse_mode="Markdown")
        return

    # 3. Processing notification
    status_msg = await message.answer("⏳ در حال دریافت تصویر و بهینه‌سازی وضوح...")
    
    try:
        # Download highest resolution photo
        photo = message.photo[-1]
        file_io = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        temp_path = file_io.name
        file_io.close()
        
        await bot.download(photo, destination=temp_path)
        
        await status_msg.edit_text("🔍 در حال شناسایی حروف و کلمات فارسی...")
        
        # Perform OCR
        loop = asyncio.get_running_loop()
        recognized_text = await loop.run_in_executor(None, ocr_engine.ocr_image, temp_path, settings.DEFAULT_OCR_LANG, True)
        
        # Log conversion
        await db.log_conversion(user_id, "photo", 1)
        
        # Save session
        session_id = str(uuid.uuid4())[:8]
        OCR_SESSIONS[session_id] = {
            "text": recognized_text,
            "image_path": temp_path,
            "user_id": user_id
        }

        # Telegram message preview
        preview_text = recognized_text
        if not preview_text.strip():
            preview_text = "⚠️ متنی در این تصویر یافت نشد! لطفاً از کیفیت و وضوح و زاویه مناسب عکس اطمینان حاصل کنید."
        elif len(preview_text) > 3500:
            preview_text = preview_text[:3500] + "\n\n...(ادامه متن به دلیل طولانی بودن در فایل‌های زیر موجود است)"

        response_text = (
            "✅ **متن استخراج‌شده با موفقیت آماده شد:**\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            f"{preview_text}\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "📁 برای دریافت خروجی با فونت استاندارد روی گزینه‌های زیر کلیک کنید:"
        )

        await status_msg.edit_text(response_text, reply_markup=get_ocr_result_markup(session_id))

    except Exception as e:
        await status_msg.edit_text(f"❌ خطایی در پردازش رخ داد: {str(e)}")

@router.message(F.document)
async def handle_document(message: Message, bot: Bot):
    user_id = message.from_user.id
    doc = message.document
    mime = (doc.mime_type or "").lower()
    file_name = (doc.file_name or "").lower()
    
    # Verify file type: Image or PDF
    is_image = "image" in mime or file_name.endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp"))
    is_pdf = "pdf" in mime or file_name.endswith(".pdf")
    
    if not (is_image or is_pdf):
        await message.answer("⚠️ لطفاً فقط فایل‌های تصویری (JPG, PNG) یا اسناد PDF ارسال کنید.")
        return

    # Force Join Check
    joined, missing = await growth.check_all_force_channels(bot, user_id)
    if not joined:
        text = "⚠️ برای استفاده از ربات باید ابتدا در کانال‌های زیر عضو شوید:"
        await message.answer(text, reply_markup=growth.get_force_join_markup(missing), parse_mode="Markdown")
        return

    # Credit check
    has_credits = await db.deduct_user_credits(user_id, 1)
    if not has_credits:
        text = (
            "❌ **اعتبار رایگان شما تمام شده است!**\n\n"
            "برای شارژ فوری اعتبار می‌توانید کد استوری اینستاگرام را وارد کنید یا دوستانتان را دعوت نمایید:"
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 دریافت اعتبار با کد اینستاگرام", callback_data="instagram_menu")],
            [InlineKeyboardButton(text="👥 دعوت دوستان", callback_data="referral_menu")],
        ])
        await message.answer(text, reply_markup=markup, parse_mode="Markdown")
        return

    status_msg = await message.answer("⏳ در حال دریافت سند... لطفاً کمی صبر کنید.")

    try:
        suffix = ".pdf" if is_pdf else os.path.splitext(file_name)[1]
        temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        temp_path = temp_file.name
        temp_file.close()

        await bot.download(doc, destination=temp_path)
        loop = asyncio.get_running_loop()

        if is_pdf:
            await status_msg.edit_text("📄 در حال تبدیل صفحات PDF به متن فارسی و ساخت فایل Word...")
            with open(temp_path, "rb") as f:
                pdf_bytes = f.read()
            text_result, pages_count = await loop.run_in_executor(
                None, ocr_engine.ocr_pdf_bytes, pdf_bytes, settings.MAX_PDF_PAGES, settings.DEFAULT_OCR_LANG
            )
            await db.log_conversion(user_id, "pdf", pages_count)
        else:
            await status_msg.edit_text("🔍 در حال شناسایی حروف و کلمات تصویر...")
            text_result = await loop.run_in_executor(
                None, ocr_engine.ocr_image, temp_path, settings.DEFAULT_OCR_LANG, True
            )
            await db.log_conversion(user_id, "photo_doc", 1)

        session_id = str(uuid.uuid4())[:8]
        OCR_SESSIONS[session_id] = {
            "text": text_result,
            "image_path": temp_path,
            "user_id": user_id
        }

        preview_text = text_result
        if not preview_text.strip():
            preview_text = "⚠️ متنی در این سند یافت نشد یا کیفیت اسکن برای خواندن کافی نبود."
        elif len(preview_text) > 3500:
            preview_text = preview_text[:3500] + "\n\n...(متن کامل در فایل‌های زیر قرار دارد)"

        response_text = (
            "✅ **سند با موفقیت پردازش شد!**\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            f"{preview_text}\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "📁 برای دریافت فایل کامل با قالب‌بندی استاندارد روی گزینه‌های زیر کلیک کنید:"
        )

        await status_msg.edit_text(response_text, reply_markup=get_ocr_result_markup(session_id))

    except Exception as e:
        await status_msg.edit_text(f"❌ خطایی در پردازش سند رخ داد: {str(e)}")

@router.callback_query(F.data.startswith("get_docx:"))
async def handle_get_docx(call: CallbackQuery):
    session_id = call.data.split(":")[1]
    session = OCR_SESSIONS.get(session_id)
    if not session or not session.get("text"):
        await call.answer("⚠️ اطلاعات این نشست منقضی شده است. لطفاً عکس را دوباره ارسال کنید.", show_alert=True)
        return

    await call.answer("⏳ در حال ساخت فایل Word...", show_alert=False)
    
    temp_docx = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
    docx_path = temp_docx.name
    temp_docx.close()

    ocr_engine.create_docx(session["text"], docx_path, title="متن استخراج شده توسط ربات OCR")
    
    file_to_send = FSInputFile(docx_path, filename="OCR_Output.docx")
    await call.message.answer_document(
        document=file_to_send,
        caption="📝 فایل Word آماده شد! برای تبدیل فایل‌های بیشتر عکس یا PDF بفرستید."
    )

@router.callback_query(F.data.startswith("get_txt:"))
async def handle_get_txt(call: CallbackQuery):
    session_id = call.data.split(":")[1]
    session = OCR_SESSIONS.get(session_id)
    if not session or not session.get("text"):
        await call.answer("⚠️ اطلاعات این نشست منقضی شده است.", show_alert=True)
        return

    await call.answer("⏳ در حال آماده‌سازی فایل متنی...", show_alert=False)
    
    temp_txt = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
    txt_path = temp_txt.name
    temp_txt.close()

    ocr_engine.create_txt(session["text"], txt_path)
    file_to_send = FSInputFile(txt_path, filename="OCR_Output.txt")
    await call.message.answer_document(
        document=file_to_send,
        caption="📄 فایل متنی (Text) آماده شد."
    )

@router.callback_query(F.data.startswith("re_contrast:"))
async def handle_recontrast(call: CallbackQuery):
    session_id = call.data.split(":")[1]
    session = OCR_SESSIONS.get(session_id)
    if not session or not session.get("image_path") or not os.path.exists(session["image_path"]):
        await call.answer("⚠️ تصویر اصلی در سرور یافت نشد. لطفاً عکس را مجدد ارسال فرمایید.", show_alert=True)
        return

    await call.answer("⏳ پردازش با الگوریتم وضوح بالا...", show_alert=False)
    loop = asyncio.get_running_loop()
    
    # Process with adaptive binarization
    new_text = await loop.run_in_executor(
        None, ocr_engine.ocr_image, session["image_path"], settings.DEFAULT_OCR_LANG, True
    )
    
    session["text"] = new_text
    
    preview_text = new_text[:3500] if len(new_text) > 3500 else new_text
    if not preview_text.strip():
        preview_text = "⚠️ حتی با تقویت کنتراست هم متنی شناسایی نشد. تصویر ممکن است بیش از حد تار باشد."

    response_text = (
        "🔍 **نتیجه پردازش مجدد با وضوح بالا:**\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"{preview_text}\n\n"
        "━━━━━━━━━━━━━━━━━━━"
    )
    await call.message.edit_text(response_text, reply_markup=get_ocr_result_markup(session_id))
