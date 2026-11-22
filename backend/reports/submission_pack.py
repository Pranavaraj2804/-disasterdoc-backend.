import os
import pymupdf
from datetime import datetime
from typing import List, Dict
from backend.document_processing.privacy import PrivacyService

class SubmissionPackExporter:
    def generate_pdf(self, applicant_name: str, checklist_items: List[Dict], uploaded_files: List[Dict], output_path: str = "backend/storage/DisasterDoc_Submission_Pack.pdf") -> str:
        pack = pymupdf.open()
        cover = pack.new_page()
        y = 50

        cover.insert_text((50, y), "DISASTERDOC AI — ORDERED CLAIM SUBMISSION PACK", fontsize=14, fontname="helv")
        y += 22
        cover.insert_text((50, y), f"Applicant: {PrivacyService.mask_sensitive_text(applicant_name)} | Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}", fontsize=10)
        y += 25
        cover.insert_text((50, y), "INDEX & VERIFICATION STATUS COVER SHEET:", fontsize=11)
        y += 18

        for idx, item in enumerate(checklist_items, 1):
            if y > 760:
                cover = pack.new_page()
                y = 50
            tag = "[VERIFIED]" if item.get("status") in ("VERIFIED", "SUPPLIED") else f"[UNRESOLVED: {item.get('status')}]"
            line = f"{idx}. {item.get('required_doc')} — {tag}"
            cover.insert_text((55, y), line[:92], fontsize=9)
            y += 16

        # Append files in checklist order
        file_map = {f["doc_type"]: f["file_path"] for f in uploaded_files if f.get("file_path")}
        for item in checklist_items:
            fpath = file_map.get(item.get("required_doc"))
            if fpath and os.path.exists(fpath):
                ext = os.path.splitext(fpath)[1].lower()
                if ext == ".pdf":
                    pack.insert_pdf(pymupdf.open(fpath))
                elif ext in [".jpg", ".jpeg", ".png"]:
                    pg = pack.new_page()
                    pg.insert_image(pymupdf.Rect(50, 50, 545, 780), filename=fpath)

        pack.save(output_path)
        pack.close()
        return output_path
