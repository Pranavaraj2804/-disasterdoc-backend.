import re
from datetime import datetime, timedelta
from typing import Dict, Optional

class DeadlineTracker:
    def extract_and_compute(self, notice_text: str, publication_date: Optional[str] = None) -> Dict:
        # 1. Explicit date pattern (e.g., "on or before 15-12-2026" or "deadline: 2026-12-15")
        explicit_m = re.search(r'(?:before|by|deadline|last date)\s*[:\-]?\s*(\d{2}[/-]\d{2}[/-]\d{4}|\d{4}-\d{2}-\d{2})', notice_text, re.I)
        if explicit_m:
            raw_dt = explicit_m.group(1)
            for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
                try:
                    due_dt = datetime.strptime(raw_dt, fmt)
                    days_left = (due_dt - datetime.now()).days
                    return {
                        "status": "OVERDUE" if days_left < 0 else "ACTIVE",
                        "due_date": due_dt.strftime("%Y-%m-%d"),
                        "days_remaining": days_left,
                        "message": f"Application form: {'OVERDUE by ' + str(abs(days_left)) if days_left < 0 else 'due in ' + str(days_left)} days ({due_dt.strftime('%d-%b-%Y')})."
                    }
                except ValueError:
                    continue

        # 2. Relative window pattern (e.g., "within 30 days after publication")
        rel_m = re.search(r'(\d+)\s*days?\s*(?:from|after|of)\s*(?:publication|notification|calamity|issue)', notice_text, re.I)
        if rel_m and publication_date:
            window = int(rel_m.group(1))
            pub_dt = datetime.strptime(publication_date, "%Y-%m-%d")
            due_dt = pub_dt + timedelta(days=window)
            days_left = (due_dt - datetime.now()).days
            return {
                "status": "OVERDUE" if days_left < 0 else "ACTIVE",
                "due_date": due_dt.strftime("%Y-%m-%d"),
                "days_remaining": days_left,
                "message": f"Application form: due in {days_left} days (Deadline: {due_dt.strftime('%d-%b-%Y')})."
            }

        # 3. Safe abstention when ambiguous
        return {
            "status": "UNCLEAR",
            "due_date": None,
            "days_remaining": None,
            "message": "Deadline date is unclear or missing publication date — verify cut-off directly with local VAO/Tahsildar (no date guessed)."
        }
