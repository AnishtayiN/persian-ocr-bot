import os
import tempfile
import asyncio
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from config import settings
import database as db
import ocr_engine

app = FastAPI(title="Persian OCR & Growth App", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.on_event("startup")
async def on_startup():
    await db.init_db()

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = os.path.join(TEMPLATES_DIR, "index.html")
    with open(index_file, "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)

@app.get("/api/info")
async def get_app_info():
    daily_code = await db.get_setting("daily_ig_code", settings.DAILY_INSTAGRAM_CODE)
    ig_url = await db.get_setting("ig_page_url", settings.INSTAGRAM_PAGE_URL)
    ig_user = await db.get_setting("ig_username", settings.INSTAGRAM_USERNAME)
    stats = await db.get_admin_stats()
    
    return {
        "status": "online",
        "ig_url": ig_url,
        "ig_username": ig_user,
        "daily_code_hint": "در استوری امروز پیج اینستاگرام قرار دارد",
        "stats": stats
    }

@app.post("/api/ocr")
async def process_ocr(file: UploadFile = File(...), lang: str = Form("fas+eng"), binarize: bool = Form(False)):
    filename = (file.filename or "").lower()
    is_pdf = filename.endswith(".pdf")
    is_image = filename.endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp"))
    
    if not (is_image or is_pdf):
        raise HTTPException(status_code=400, detail="فرمت فایل پشتیبانی نمی‌شود. لطفاً عکس یا فایل PDF ارسال کنید.")

    contents = await file.read()
    loop = asyncio.get_running_loop()

    try:
        if is_pdf:
            text_result, pages_count = await loop.run_in_executor(
                None, ocr_engine.ocr_pdf_bytes, contents, settings.MAX_PDF_PAGES, lang
            )
        else:
            text_result = await loop.run_in_executor(
                None, ocr_engine.ocr_image, contents, lang, True
            )
            pages_count = 1

        return {
            "success": True,
            "text": text_result,
            "pages": pages_count,
            "char_count": len(text_result),
            "word_count": len(text_result.split())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در پردازش OCR: {str(e)}")

@app.post("/api/export-docx")
async def export_docx(text: str = Form(...), title: str = Form("سند OCR")):
    if not text.strip():
        raise HTTPException(status_code=400, detail="متنی برای خروجی ورد ارسال نشده است.")

    temp_docx = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
    docx_path = temp_docx.name
    temp_docx.close()

    ocr_engine.create_docx(text, docx_path, title=title)
    return FileResponse(docx_path, filename="Persian_OCR_Export.docx", media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

@app.post("/api/verify-code")
async def verify_instagram_code(code: str = Form(...)):
    current_code = await db.get_setting("daily_ig_code", settings.DAILY_INSTAGRAM_CODE)
    if code.strip().lower() == current_code.strip().lower():
        return {
            "valid": True,
            "message": "کد تأیید شد! قفل خروجی نامحدود Word و صفحات اضافه فعال گردید."
        }
    return {
        "valid": False,
        "message": "کد اشتباه است! لطفاً استوری امروز پیج اینستاگرام را مشاهده کنید."
    }
