import re
import difflib
from typing import Dict, List

# Words in a checklist item name that are too generic to prove a change affects it
# (e.g. "proof" appears in both "Identity Proof" and "Residence proof").
GENERIC_WORDS = {"proof", "certificate", "document", "copy", "form", "details", "and", "the"}

# Extra words that point to each checklist item, so a change is linked to the right item only.
SYNONYMS = {
    "identity proof": {"identity", "aadhaar", "aadhar", "voter", "id"},
    "bank passbook": {"bank", "passbook", "account"},
    "residence / utility bill": {"residence", "utility", "bill", "ration", "address", "resident"},
    "damage photograph": {"photograph", "photographs", "photo", "photos"},
    "land / patta / adangal": {"land", "patta", "adangal", "chitta", "ownership"},
    "death / medical certificate": {"death", "medical", "postmortem"},
}


def _norm(line: str) -> str:
    """Lower-case, drop punctuation and number commas so formatting-only edits are ignored."""
    s = line.lower()
    s = re.sub(r"(?<=\d),(?=\d)", "", s)   # 1,20,000 -> 120000
    s = re.sub(r"\.(?!\d)", " ", s)         # drop full stops, keep decimals
    s = re.sub(r"[^\w\s/₹.]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


class RuleChangeImpactTracker:
    """Detects meaningful policy changes between two versions and flags only the affected checklist items."""

    def compare_versions(self, old_version_meta: Dict, new_version_meta: Dict, applicant_checklist: List[Dict]) -> Dict:
        old_raw = [ln.strip() for ln in old_version_meta["text"].splitlines() if ln.strip()]
        new_raw = [ln.strip() for ln in new_version_meta["text"].splitlines() if ln.strip()]
        old_lines = [_norm(x) for x in old_raw]
        new_lines = [_norm(x) for x in new_raw]

        # Map normalised line -> original line, to show readable text in the result
        original = {_norm(x): x for x in old_raw + new_raw}

        meaningful_changes = []
        for line in difflib.unified_diff(old_lines, new_lines, lineterm=""):
            if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
                content = line[1:].strip()
                if re.search(r"(?:rs\.?|₹|\d+|hectare|certificate|patta|aadhaar|days|ceiling|accept|proof|document)", content, re.I):
                    meaningful_changes.append(
                        f"{'ADDED' if line.startswith('+') else 'REMOVED'}: {original.get(content, content)}"
                    )

        # Only words that were really added or removed decide which checklist items are affected
        old_words = set(re.findall(r"[a-z]+", " ".join(old_lines)))
        new_words = set(re.findall(r"[a-z]+", " ".join(new_lines)))
        change_words = (old_words ^ new_words) if meaningful_changes else set()

        affected_items = []
        for item in applicant_checklist:
            name = item["required_doc"].lower()
            keys = {t for t in re.findall(r"[a-z]+", name) if len(t) > 3 and t not in GENERIC_WORDS}
            keys |= SYNONYMS.get(name, set())
            if keys & change_words:
                affected_items.append(item["required_doc"])

        eff = new_version_meta.get("effective_date")
        if eff:
            note = (f"New rules are effective from {eff}. Check whether this applies to your case from that date; "
                    "do not assume it applies to files submitted earlier.")
        else:
            note = "Effective date is unclear in the revised notice. Verify it with the issuing office before relying on the change."

        return {
            "old_version": old_version_meta.get("version", "v1"),
            "new_version": new_version_meta.get("version", "v2"),
            "effective_date": eff or "Unspecified",
            "effective_date_note": note,
            "meaningful_changes_count": len(meaningful_changes),
            "meaningful_changes": meaningful_changes,
            "affected_checklist_items": list(dict.fromkeys(affected_items)),
        }
