import re
import difflib
from itertools import combinations
from typing import List, Dict

class PairwiseConsistencyEngine:
    @staticmethod
    def normalize_name(name: str) -> str:
        # Remove dots, collapse whitespace, strip single-letter initials for core comparison
        cleaned = re.sub(r'[^a-zA-Z\s]', ' ', name.lower())
        tokens = [t for t in cleaned.split() if len(t) > 1]
        return " ".join(sorted(tokens))

    def compare_all_pairs(self, records: List[Dict]) -> List[Dict]:
        results = []
        for doc_a, doc_b in combinations(records, 2):
            pair_label = f"{doc_a['doc_type']} ({doc_a['doc_id']}) vs {doc_b['doc_type']} ({doc_b['doc_id']})"

            # Compare Name
            if doc_a.get("name") and doc_b.get("name"):
                raw_sim = difflib.SequenceMatcher(None, doc_a["name"].lower(), doc_b["name"].lower()).ratio()
                norm_a = self.normalize_name(doc_a["name"])
                norm_b = self.normalize_name(doc_b["name"])
                norm_sim = difflib.SequenceMatcher(None, norm_a, norm_b).ratio() if (norm_a and norm_b) else raw_sim

                if norm_sim >= 0.90 and raw_sim < 0.90:
                    status = "INITIAL_VARIATION"
                    msg = f"Initial/format variation ('{doc_a['name']}' vs '{doc_b['name']}'). Core tokens match; confirm same person."
                elif norm_sim < 0.80:
                    status = "MISMATCH"
                    msg = f"Name mismatch ('{doc_a['name']}' vs '{doc_b['name']}'). Upload corrected copy or self-declaration."
                else:
                    status = "MATCH"
                    msg = f"Names match ('{doc_a['name']}')."

                results.append({"pair": pair_label, "field": "name", "status": status, "similarity": round(norm_sim, 2), "detail": msg})

            # Compare DOB
            if doc_a.get("dob") and doc_b.get("dob"):
                dob_match = doc_a["dob"] == doc_b["dob"]
                results.append({
                    "pair": pair_label,
                    "field": "dob",
                    "status": "MATCH" if dob_match else "MISMATCH",
                    "similarity": 1.0 if dob_match else 0.0,
                    "detail": f"DOB {'matches' if dob_match else 'differs'} ({doc_a['dob']} vs {doc_b['dob']})."
                })

            # Compare Address
            if doc_a.get("address") and doc_b.get("address"):
                addr_sim = difflib.SequenceMatcher(None, doc_a["address"].lower(), doc_b["address"].lower()).ratio()
                results.append({
                    "pair": pair_label,
                    "field": "address",
                    "status": "MATCH" if addr_sim >= 0.75 else "MISMATCH",
                    "similarity": round(addr_sim, 2),
                    "detail": "Address matches." if addr_sim >= 0.75 else "Address differs across documents."
                })

        return results
