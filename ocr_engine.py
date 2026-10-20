import os
import re
import cv2
import numpy as np
from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes, convert_from_path
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from config import settings

# Configure pytesseract command if needed
if settings.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

def clean_persian_text(text: str) -> str:
    """Normalize Arabic/Persian characters and clean extra whitespaces."""
    if not text:
        return ""
    # Standardize Arabic Yeh and Kaf to Persian
    text = text.replace("ي", "ی").replace("ك", "ک")
    # Replace Arabic numerals with Persian if desired, or keep as is
    # Fix repeated newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove excessive spaces
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def preprocess_image(image_input, enhance_contrast: bool = True, binarize: bool = False) -> Image.Image:
    """
    Advanced OpenCV preprocessing for Persian OCR:
    - CLAHE (adaptive contrast)
    - Denoise
    - Optional Otsu adaptive threshold
    """
    if isinstance(image_input, str):
        cv_img = cv2.imread(image_input)
    elif isinstance(image_input, Image.Image):
        cv_img = cv2.cvtColor(np.array(image_input), cv2.COLOR_RGB2BGR)
    elif isinstance(image_input, bytes):
        nparr = np.frombuffer(image_input, np.uint8)
        cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    else:
        return image_input

    if cv_img is None:
        raise ValueError("Cannot read image")

    # Convert to grayscale
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

    # Deskew angle detection
    try:
        coords = np.column_stack(np.where(gray < 200))
        if len(coords) > 50:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            if abs(angle) > 0.5 and abs(angle) < 45:
                (h, w) = gray.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                gray = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    except Exception:
        pass

    # Contrast enhancement (CLAHE)
    if enhance_contrast:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

    # Noise removal
    gray = cv2.bilateralFilter(gray, 9, 75, 75)

    # Optional Binarization
    if binarize:
        gray = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

    # Convert back to PIL Image
    pil_img = Image.fromarray(gray)
    return pil_img

def ocr_image(image_input, lang: str = "fas+eng", preprocess: bool = True) -> str:
    """Run OCR on a single image and return recognized text."""
    if preprocess:
        proc_img = preprocess_image(image_input, enhance_contrast=True)
    else:
        if isinstance(image_input, (str, bytes)):
            if isinstance(image_input, bytes):
                import io
                proc_img = Image.open(io.BytesIO(image_input))
            else:
                proc_img = Image.open(image_input)
        else:
            proc_img = image_input

    # OCR config: psm 3 (Fully automatic page segmentation)
    custom_config = r'--psm 3 --oem 3'
    raw_text = pytesseract.image_to_string(proc_img, lang=lang, config=custom_config)
    return clean_persian_text(raw_text)

def ocr_pdf_bytes(pdf_bytes: bytes, max_pages: int = 15, lang: str = "fas+eng") -> tuple[str, int]:
    """Convert multi-page PDF bytes to text."""
    images = convert_from_bytes(pdf_bytes, first_page=1, last_page=max_pages)
    extracted_pages = []
    
    for i, page_img in enumerate(images, start=1):
        page_text = ocr_image(page_img, lang=lang, preprocess=True)
        header = f"━━━━━━━━ 📄 صفحه {i} ━━━━━━━━"
        extracted_pages.append(f"{header}\n\n{page_text}")

    full_text = "\n\n".join(extracted_pages)
    return full_text, len(images)

def set_rtl(paragraph):
    """Helper to set RTL (Right-to-Left) direction in docx paragraph."""
    pPr = paragraph._p.get_or_add_pPr()
    bidi = OxmlElement('w:bidi')
    bidi.set(qn('w:val'), '1')
    pPr.append(bidi)

def create_docx(text: str, output_path: str, title: str = "متن استخراج شده توسط ربات OCR") -> str:
    """Create a professionally styled RTL Word (.docx) document."""
    doc = Document()
    
    # Set page margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Document Title
    p_title = doc.add_paragraph()
    set_rtl(p_title)
    p_title.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run_title = p_title.add_run(title)
    run_title.bold = True
    run_title.font.size = Pt(16)
    run_title.font.name = "B Nazanin"
    run_title.font.color.rgb = RGBColor(30, 41, 59)

    # Sub-header separator
    p_sep = doc.add_paragraph()
    set_rtl(p_sep)
    p_sep.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run_sep = p_sep.add_run("─" * 45)
    run_sep.font.color.rgb = RGBColor(148, 163, 184)

    # Content paragraphs
    paragraphs = text.split('\n')
    for line in paragraphs:
        line_clean = line.strip()
        if not line_clean:
            continue
        p = doc.add_paragraph()
        set_rtl(p)
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p.paragraph_format.line_spacing = 1.3
        p.paragraph_format.space_after = Pt(4)
        
        run = p.add_run(line_clean)
        run.font.name = "B Nazanin"
        run.font.size = Pt(13)
        run.font.color.rgb = RGBColor(15, 23, 42)

    doc.save(output_path)
    return output_path

def create_txt(text: str, output_path: str) -> str:
    """Save clean UTF-8 text file."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    return output_path
