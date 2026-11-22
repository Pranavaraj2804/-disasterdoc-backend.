from typing import Dict
from deep_translator import GoogleTranslator
from backend.guidance.gemini_translate import gemini_translate


class MultilingualService:
    SUPPORTED = {"en": "English", "ta": "Tamil", "ml": "Malayalam", "hi": "Hindi"}

    def translate_with_source(self, explanation_en: str, official_passage: str, citation: str, target_lang: str = "en") -> Dict:
        lang = target_lang.lower() if target_lang.lower() in self.SUPPORTED else "en"
        if lang == "en":
            translated = explanation_en
        else:
            try:
                translated = gemini_translate(explanation_en, "English", self.SUPPORTED[lang])
            except Exception as e1:
                print(f"[translate] Gemini failed, trying Google web translator: {e1}")
                try:
                    translated = GoogleTranslator(source="en", target=lang).translate(explanation_en)
                except Exception as e2:
                    print(f"[translate] fallback failed: {e2}")
                    translated = explanation_en + "\n\n[Translation is not available right now. Showing English.]"

        return {
            "language": self.SUPPORTED[lang],
            "translated_guidance": translated,
            "original_official_passage": official_passage,
            "citation": citation,
        }
