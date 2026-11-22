import os
import pymupdf
from typing import List, Dict

class DocumentExtractor:
    def extract_pdf_pages(self, pdf_path: str) -> List[Dict]:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        doc = pymupdf.open(pdf_path)
        source_name = os.path.basename(pdf_path)
        extracted_pages = []

        for page_idx, page in enumerate(doc):
            raw_text = page.get_text("text")
            clean_text = " ".join(raw_text.split())
            if len(clean_text) >= 30:
                extracted_pages.append({
                    "source": source_name,
                    "doc_type": "government_pdf",
                    "page": page_idx + 1,
                    "total_pages": len(doc),
                    "text": clean_text
                })
        doc.close()
        return extracted_pages
