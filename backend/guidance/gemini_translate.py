import os
from google import genai
from google.genai import types

_client = None


def _get_client():
    global _client
    if _client is None:
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        _client = genai.Client(api_key=key)
    return _client


def gemini_translate(text: str, source: str, target: str) -> str:
    """Translate with Gemini. source/target are language names, e.g. 'Tamil', 'English'."""
    prompt = (
        f"Translate the text below from {source} to {target}.\n"
        "Keep numbers, rupee amounts, file names, page numbers and the G.O. number exactly as they are.\n"
        "Keep the line breaks. Output only the translation, with no notes.\n\n"
        f"Text:\n{text}"
    )
    models = [os.environ.get("GEMINI_MODEL", "gemini-flash-latest"), "gemini-3.5-flash", "gemini-2.5-flash"]
    last = None
    for m in dict.fromkeys(models):
        try:
            r = _get_client().models.generate_content(
                model=m,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=8192),
            )
            if r.text and r.text.strip():
                return r.text.strip()
        except Exception as e:
            last = e
            print(f"[translate] model '{m}' failed: {e}")
    raise RuntimeError(f"Gemini translation failed: {last}")
