import os
import pymupdf
import pytesseract
from PIL import Image
from typing import Dict, List
from backend.document_processing.privacy import PrivacyService

class OCREngine:
    def __init__(self, lang: str = "eng+tam"):
        self.lang = lang

    def extract_text(self, file_path: str) -> Dict:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        pages_text: List[str] = []
        ocr_used = False

        if ext in [".jpg", ".jpeg", ".png"]:
            img = Image.open(file_path)
            raw = pytesseract.image_to_string(img, lang=self.lang)
            pages_text.append(PrivacyService.mask_sensitive_text(raw))
            ocr_used = True
        elif ext == ".pdf":
            doc = pymupdf.open(file_path)
            for page in doc:
                txt = page.get_text("text").strip()
                if len(txt) < 25:
                    pix = page.get_pixmap(dpi=200)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    txt = pytesseract.image_to_string(img, lang=self.lang)
                    ocr_used = True
                pages_text.append(PrivacyService.mask_sensitive_text(txt))
            doc.close()
        else:
            raise ValueError(f"Unsupported format: {ext}")

        return {
            "file_path": file_path,
            "page_count": len(pages_text),
            "ocr_used": ocr_used,
            "masked_pages": pages_text,
            "full_masked_text": "\n".join(pages_text)
        }
