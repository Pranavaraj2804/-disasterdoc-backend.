import re
from typing import List, Dict

class RequirementChunker:
    def __init__(self, max_chars: int = 650, overlap_chars: int = 120):
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    def chunk_structured_records(self, records: List[Dict]) -> List[Dict]:
        chunks = []
        for rec in records:
            entry = rec["raw_data"]
            formatted_fields = " | ".join(f"{k}: {v}" for k, v in entry.items() if v is not None and str(v).strip())
            domain = "housing" if "house" in formatted_fields.lower() or "hut" in formatted_fields.lower() else (
                "agriculture" if "hectare" in formatted_fields.lower() or "crop" in formatted_fields.lower() else "general"
            )
            chunks.append({
                "chunk_id": f"{rec['source']}_{len(chunks)+1}",
                "source": rec["source"],
                "page": rec["page"],
                "domain": domain,
                "text": formatted_fields
            })
        return chunks

    def chunk_pdf_pages(self, pages: List[Dict]) -> List[Dict]:
        chunks = []
        for p in pages:
            text = p["text"]
            # Split by sentence boundaries first
            sentences = re.split(r'(?<=[.!?])\s+', text)
            current_chunk = ""

            for sent in sentences:
                if len(current_chunk) + len(sent) + 1 <= self.max_chars:
                    current_chunk = f"{current_chunk} {sent}".strip()
                else:
                    if current_chunk:
                        chunks.append(self._build_chunk_obj(p, current_chunk, len(chunks) + 1))
                    # Keep overlap from tail of previous chunk
                    tail = current_chunk[-self.overlap_chars:] if len(current_chunk) > self.overlap_chars else current_chunk
                    current_chunk = f"{tail} {sent}".strip()

            if current_chunk:
                chunks.append(self._build_chunk_obj(p, current_chunk, len(chunks) + 1))
        return chunks

    def _build_chunk_obj(self, page_meta: Dict, text: str, idx: int) -> Dict:
        t_low = text.lower()
        domain = "general"
        if any(w in t_low for w in ["house", "pucca", "kutcha", "hut", "cattle shed"]):
            domain = "housing"
        elif any(w in t_low for w in ["hectare", "crop", "paddy", "input subsidy", "de-silting", "rainfed"]):
            domain = "agriculture"
        elif any(w in t_low for w in ["deceased", "ex-gratia", "limb", "eye", "injury"]):
            domain = "gratuitous_relief"

        return {
            "chunk_id": f"{page_meta['source']}_p{page_meta['page']}_c{idx}",
            "source": page_meta["source"],
            "page": page_meta["page"],
            "domain": domain,
            "text": text
        }
