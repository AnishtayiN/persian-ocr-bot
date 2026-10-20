import os
import sys
import pytest
import asyncio
from PIL import Image, ImageDraw

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import ocr_engine
import database as db

@pytest.mark.asyncio
async def test_database_and_credits():
    await db.init_db()
    test_user_id = 999999
    user = await db.register_or_update_user(test_user_id, "testuser", "Test")
    assert user["user_id"] == test_user_id
    assert user["credits"] >= 10

    # Deduct credit
    deducted = await db.deduct_user_credits(test_user_id, 1)
    assert deducted is True

    # Test Instagram code verification
    success, msg = await db.check_and_apply_ig_code(test_user_id, "OCR2026")
    assert success is True
    assert "تبریک" in msg

@pytest.mark.asyncio
async def test_ocr_and_docx():
    # Create synthetic test image
    img = Image.new("RGB", (300, 100), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((10, 30), "Test Persian OCR 2026", fill=(0, 0, 0))
    
    test_img_path = "/tmp/test_ocr_input.png"
    img.save(test_img_path)

    # Test OCR
    text = ocr_engine.ocr_image(test_img_path, lang="eng", preprocess=True)
    assert len(text) > 0

    # Test DOCX creation
    docx_path = "/tmp/test_output.docx"
    ocr_engine.create_docx(text, docx_path, title="تست خروجی ورد")
    assert os.path.exists(docx_path)
    assert os.path.getsize(docx_path) > 0

if __name__ == "__main__":
    asyncio.run(test_database_and_credits())
    asyncio.run(test_ocr_and_docx())
    print("✅ تمام تست‌ها با موفقیت پاس شدند!")
