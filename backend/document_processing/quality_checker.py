import os
import re
import cv2
import pymupdf
from datetime import datetime
from typing import Dict

class EvidenceQualityChecker:
    def check_file(self, file_path: str, masked_text: str, doc_type: str) -> Dict:
        if not os.path.exists(file_path):
            return {"status": "MISSING", "quality_score": 0.0, "reasons": ["File not found on disk."]}

        ext = os.path.splitext(file_path)[1].lower()
        reasons = []
        score = 1.0

        if ext in [".jpg", ".jpeg", ".png"]:
            img = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                h, w = img.shape
                blur_var = cv2.Laplacian(img, cv2.CV_64F).var()
                if blur_var < 75.0:
                    reasons.append(f"Blurry image (sharpness={blur_var:.1f} < 75); text unreadable.")
                    score -= 0.50
                if w < 300 or h < 300:
                    reasons.append(f"Low resolution / heavily cropped ({w}x{h}px).")
                    score -= 0.35
                # Edge border cropping check
                border_mean = (img[0, :].mean() + img[-1, :].mean() + img[:, 0].mean() + img[:, -1].mean()) / 4.0
                if border_mean < 40.0:
                    reasons.append("Dark/clipped edges detected — verify document borders are not cut off.")
                    score -= 0.15

        elif ext == ".pdf":
            doc = pymupdf.open(file_path)
            if len(doc) == 0:
                reasons.append("Empty PDF with 0 pages.")
                score = 0.0
            for idx, page in enumerate(doc):
                pix = page.get_pixmap(dpi=100)
                if pix.width < 200 or pix.height < 200:
                    reasons.append(f"Page {idx+1} has unusually small dimensions.")
                    score -= 0.30
            doc.close()

        # Check multi-page completeness markers (e.g., "Page 1 of 2" when only 1 page uploaded)
        page_of_match = re.search(r'page\s*\d+\s*of\s*(\d+)', masked_text, re.I)
        if page_of_match and ext == ".pdf":
            expected = int(page_of_match.group(1))
            actual = len(pymupdf.open(file_path))
            if actual < expected:
                reasons.append(f"Incomplete document: uploaded {actual} of {expected} pages.")
                score -= 0.45

        # Expiry check
        exp_match = re.search(r'(?:valid\s*(?:till|upto)|expiry)\s*[:\-]?\s*(\d{2}[/-]\d{2}[/-]\d{4})', masked_text, re.I)
        if exp_match:
            try:
                exp_dt = datetime.strptime(exp_match.group(1).replace("-", "/"), "%d/%m/%Y")
                if exp_dt < datetime.now():
                    reasons.append(f"Document expired on {exp_match.group(1)}.")
                    score -= 0.50
            except ValueError:
                pass

        if len(masked_text.strip()) < 20 and doc_type != "Damage Photograph":
            reasons.append("Insufficient readable text extracted — upload a clearer scan.")
            score -= 0.40

        final_score = max(0.1, round(score, 2))
        status = "VERIFIED" if not reasons else "NEEDS REVIEW"
        return {"status": status, "quality_score": final_score, "reasons": reasons or ["Clear, complete, and readable."]}
