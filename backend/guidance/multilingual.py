from typing import Dict
from deep_translator import GoogleTranslator

class MultilingualService:
    SUPPORTED = {"en": "English", "ta": "Tamil", "ml": "Malayalam", "hi": "Hindi"}

    def translate_with_source(self, explanation_en: str, official_passage: str, citation: str, target_lang: str = "en") -> Dict:
        lang = target_lang.lower() if target_lang.lower() in self.SUPPORTED else "en"
        if lang == "en":
            translated = explanation_en
        else:
            try:
                translated = GoogleTranslator(source="en", target=lang).translate(explanation_en)
            except Exception as e:
                translated = f"{explanation_en} [Translation unavailable: {str(e)}]"

        return {
            "language": self.SUPPORTED[lang],
            "translated_guidance": translated,
            "original_official_passage": official_passage,
            "citation": citation
        }
