@echo off
chcp 65001 > nul
title اسکنر و OCR فارسی رایگان (اجرا در ویندوز)
color 0b

echo ========================================================
echo       اسکنر و OCR فارسی و انگلیسی کاملا رایگان
echo ========================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [خطا] پایتون روی سیستم شما نصب نیست!
    echo لطفا پایتون نسخه 3.10 به بالا را از python.org دانلود و نصب کنید.
    echo حتما تیک 'Add Python to PATH' را در هنگام نصب بزنید.
    pause
    exit /b
)

if not exist venv (
    echo [1/3] در حال ساخت محیط مجازی پایتون (venv)...
    python -m venv venv
)

echo [2/3] در حال بررسی و نصب پیش‌نیازها...
call venv\Scripts\activate
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt

echo.
echo [3/3] در حال راه‌اندازی برنامه...
echo صفحه برنامه تا چند لحظه دیگر در مرورگر شما باز می‌شود.
echo برای توقف برنامه کلیدهای Ctrl + C را فشار دهید.
echo.

start http://localhost:8000
python -m uvicorn web.app:app --host 127.0.0.1 --port 8000

pause
