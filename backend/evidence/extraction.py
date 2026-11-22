import re
from typing import Dict

class ApplicantFieldExtractor:
    def extract_fields(self, doc_id: str, doc_type: str, masked_text: str) -> Dict:
        lines = [ln.strip() for ln in masked_text.splitlines() if len(ln.strip()) > 2]

        name = ""
        for pat in [
            r'(?:Name|Head of Family|Family Head|Applicant Name|Claimant)\s*[:\-]\s*([A-Za-z\s\.]{3,45})',
            r'(?:Shri|Smt|Mr|Mrs|Ms)\.?\s+([A-Za-z\s\.]{3,45})'
        ]:
            m = re.search(pat, masked_text, re.I)
            if m:
                name = re.sub(r'\s+', ' ', m.group(1)).strip()
                break

        if not name:
            for i, ln in enumerate(lines):
                if re.search(r'(?:DOB|Year of Birth|YOB|Male|Female)', ln, re.I) and i > 0:
                    cand = re.sub(r'[^A-Za-z\s\.]', '', lines[i - 1]).strip()
                    if 3 <= len(cand) <= 45:
                        name = cand
                        break

        dob_m = re.search(r'(?:DOB|Date of Birth|YOB|Year of Birth)\s*[:\-]?\s*(\d{2}[/-]\d{2}[/-]\d{4}|\d{4})', masked_text, re.I)
        addr_m = re.search(r'(?:Address|Addr|S/O|W/O|D/O)\s*[:\-]?\s*(.{8,90})', masked_text, re.I)

        return {
            "doc_id": doc_id,
            "doc_type": doc_type,
            "name": name,
            "dob": dob_m.group(1) if dob_m else "",
            "address": addr_m.group(1).strip() if addr_m else ""
        }
