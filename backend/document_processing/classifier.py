import re

class DocumentClassifier:
    RULES = {
        "Identity Proof": [r"government of india", r"unique identification", r"year of birth", r"dob", r"male|female"],
        "Ration Card": [r"family card", r"ration", r"head of family", r"civil supplies", r"smart card"],
        "Land / Patta / Adangal": [r"patta", r"chitta", r"adangal", r"survey no", r"hectare", r"revenue department"],
        "Residence / Utility Bill": [r"electricity", r"tneb", r"tangedco", r"property tax", r"house tax", r"consumer no"],
        "Death / Medical Certificate": [r"death certificate", r"post mortem", r"hospital", r"cause of death", r"medical officer"],
        "Bank Passbook": [r"ifsc", r"account no", r"branch", r"passbook", r"bank"],
        "Application Form": [r"application for relief", r"disaster relief", r"claimant", r"signature of applicant"]
    }

    def classify(self, masked_text: str, filename: str = "") -> str:
        t_low = f"{filename} {masked_text}".lower()
        if any(w in filename.lower() for w in ["damage", "photo", "flood", "house_img"]):
            return "Damage Photograph"

        best_label = "Supporting Document"
        best_hits = 0
        for label, patterns in self.RULES.items():
            hits = sum(1 for p in patterns if re.search(p, t_low))
            if hits > best_hits:
                best_hits = hits
                best_label = label
        return best_label
