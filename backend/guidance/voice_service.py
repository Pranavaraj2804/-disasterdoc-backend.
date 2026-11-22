import os
import re
import time
import speech_recognition as sr
from pydub import AudioSegment
from gtts import gTTS
from deep_translator import GoogleTranslator
from typing import Dict

class VoiceAndTamilService:
    def __init__(self, audio_out_dir: str = "backend/storage/voice_responses"):
        self.audio_out_dir = audio_out_dir
        os.makedirs(audio_out_dir, exist_ok=True)
        self.recognizer = sr.Recognizer()

    @staticmethod
    def detect_text_language(text: str) -> str:
        """Returns 'ta' if Tamil Unicode characters exist, else 'en'."""
        return "ta" if re.search(r'[\u0B80-\u0BFF]', text) else "en"

    def normalize_query_to_english(self, query: str) -> Dict:
        """Translates Tamil text queries into English for accurate RAG retrieval and relief math."""
        detected = self.detect_text_language(query)
        if detected == "ta":
            try:
                en_query = GoogleTranslator(source="ta", target="en").translate(query)
                return {"original_query": query, "english_query": en_query, "detected_lang": "ta"}
            except Exception:
                return {"original_query": query, "english_query": query, "detected_lang": "ta"}
        return {"original_query": query, "english_query": query, "detected_lang": "en"}

    def transcribe_audio_auto(self, audio_path: str) -> Dict:
        """
        Transcribes microphone audio and auto-detects whether the user spoke Tamil ('ta') or English ('en').
        """
        wav_path = f"{audio_path}_converted.wav"
        sound = AudioSegment.from_file(audio_path)
        sound.export(wav_path, format="wav")

        with sr.AudioFile(wav_path) as source:
            audio_data = self.recognizer.record(source)

        try:
            # 1. Try Tamil (India) first
            ta_text = self.recognizer.recognize_google(audio_data, language="ta-IN")
            if ta_text and self.detect_text_language(ta_text) == "ta":
                return {"text": ta_text, "detected_lang": "ta"}
            if ta_text:
                return {"text": ta_text, "detected_lang": "en"}
        except sr.UnknownValueError:
            pass

        try:
            # 2. Fallback to Indian English
            en_text = self.recognizer.recognize_google(audio_data, language="en-IN")
            if en_text:
                return {"text": en_text, "detected_lang": "en"}
        except sr.UnknownValueError:
            pass
        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)

        return {"text": "", "detected_lang": "ta"}

    def synthesize_speech(self, text: str, lang: str = "ta") -> str:
        """Generates a clean MP3 audio file in Tamil ('ta') or English ('en')."""
        clean_text = re.sub(r'[*#`_\[\]]+', '', text).strip()[:1200]
        tts_lang = "ta" if lang == "ta" else "en"

        filename = f"reply_{tts_lang}_{int(time.time())}.mp3"
        out_path = os.path.join(self.audio_out_dir, filename)
        tts = gTTS(text=clean_text, lang=tts_lang, slow=False)
        tts.save(out_path)
        return out_path
