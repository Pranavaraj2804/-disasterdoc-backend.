import os
import json
from typing import List, Dict

class KnowledgeIngestor:
    def __init__(self, knowledge_dir: str = "backend/knowledge"):
        self.knowledge_dir = knowledge_dir
        self.pdf_dir = os.path.join(knowledge_dir, "government_documents")

    def discover_sources(self) -> Dict[str, List[str]]:
        json_files = []
        pdf_files = []

        if os.path.exists(self.knowledge_dir):
            for f in sorted(os.listdir(self.knowledge_dir)):
                if f.endswith(".json"):
                    json_files.append(os.path.join(self.knowledge_dir, f))

        if os.path.exists(self.pdf_dir):
            for f in sorted(os.listdir(self.pdf_dir)):
                if f.endswith(".pdf"):
                    pdf_files.append(os.path.join(self.pdf_dir, f))

        return {"json_files": json_files, "pdf_files": pdf_files}

    def load_structured_json(self, json_path: str) -> List[Dict]:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = data.get("items", data) if isinstance(data, dict) else data
        source_name = os.path.basename(json_path)
        records = []
        for idx, entry in enumerate(items, 1):
            records.append({
                "source": source_name,
                "doc_type": "structured_norm",
                "page": str(entry.get("page", f"Annexure-I (Item {idx})")),
                "raw_data": entry
            })
        return records
