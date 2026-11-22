import re
from typing import Dict, List

class ReliefAndEvidenceMatcher:
    """Deterministic G.O. (Ms) No. 579 (09.12.2023) Calculator & Document Matcher."""

    def evaluate_claim(self, query: str, uploaded_doc_types: List[str]) -> Dict:
        q_low = query.lower()
        has_death = bool(re.search(r'\b(died|death|dead|deceased|killed|loss of life|person loss)\b', q_low))
        has_house = bool(re.search(r'\b(house|houses|home|homes|pucca|kutcha|hut|huts|shed)\b', q_low))
        has_agri = bool(re.search(r'\b(hectare|hectares|ha|crop|crops|paddy|farm|agriculture|agri|silt|banana|coconut|rainfed)\b', q_low))

        death_m = re.search(r'(\d+)\s*(?:[a-z]+\s+){0,2}(?:persons?|people|members?|deaths?|lives)', q_low)
        num_deaths = int(death_m.group(1)) if (has_death and death_m) else (1 if has_death else 0)

        house_m = re.search(r'(\d+)\s*(?:[a-z]+\s+){0,2}(?:houses?|homes?|buildings?)', q_low)
        num_houses = int(house_m.group(1)) if (has_house and house_m) else (1 if has_house else 0)

        ha_m = re.search(r'(\d+(?:\.\d+)?)\s*(?:hectares?|ha\b)', q_low)
        num_ha = float(ha_m.group(1)) if ha_m else None

        breakdown = []
        required_docs = ["Identity Proof", "Bank Passbook"]
        total_amount = 0

        if has_death:
            amt = num_deaths * 400000
            total_amount += amt
            breakdown.append({"category": "Loss of Human Life", "calculation": f"{num_deaths} x Rs. 4,00,000", "amount": amt})
            required_docs.append("Death / Medical Certificate")

        if has_house:
            is_hilly = any(w in q_low for w in ["hill", "hilly", "nilgiris", "kodaikanal"])
            is_partial = any(w in q_low for w in ["partial", "partially", "minor", "crack"])
            unit = (4000 if "kutcha" in q_low else 6500) if is_partial else (130000 if is_hilly else 120000)
            amt = num_houses * unit
            total_amount += amt
            breakdown.append({"category": "Housing Relief", "calculation": f"{num_houses} x Rs. {unit:,}", "amount": amt})
            required_docs.extend(["Residence / Utility Bill", "Damage Photograph"])

        if has_agri:
            rate = 22500 if any(w in q_low for w in ["perennial", "banana", "coconut"]) else (
                18000 if "silt" in q_low else (8500 if "rainfed" in q_low else 17000)
            )
            eff_ha = min(num_ha, 2.0) if num_ha is not None else 1.0
            amt = int(eff_ha * rate)
            total_amount += amt
            cap_note = " (2.0 ha statutory ceiling)" if (num_ha and num_ha > 2.0) else ""
            breakdown.append({"category": "Agriculture Subsidy", "calculation": f"{eff_ha} ha x Rs. {rate:,}{cap_note}", "amount": amt})
            required_docs.append("Land / Patta / Adangal")

        unique_req = list(dict.fromkeys(required_docs))
        doc_status = [
            {"required_doc": req, "status": "SUPPLIED" if req in uploaded_doc_types else "MISSING"}
            for req in unique_req
        ]

        return {
            "breakdown": breakdown,
            "total_payable_inr": total_amount,
            "document_checklist": doc_status
        }
