from typing import Dict, List

class ConfidenceAbstainEngine:
    def evaluate(self, top_retrieval_score: float, quality_scores: List[float], has_unresolved_mismatch: bool) -> Dict:
        min_qual = min(quality_scores) if quality_scores else 1.0

        # Calibrated rule: abstains if retrieval is weak, scan quality is poor, or critical mismatch exists
        if top_retrieval_score < 0.45 or min_qual < 0.55:
            return {
                "confidence_level": "LOW",
                "abstain": True,
                "action": "NEEDS HUMAN REVIEW — Low retrieval similarity or poor scan quality; do not auto-approve."
            }
        if has_unresolved_mismatch or min_qual < 0.80:
            return {
                "confidence_level": "MEDIUM",
                "abstain": False,
                "action": "CONDITIONAL MATCH — Resolve flagged document discrepancies before submission."
            }
        return {
            "confidence_level": "HIGH",
            "abstain": False,
            "action": "VERIFIED — High-confidence policy and evidence match."
        }
