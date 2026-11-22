import os
from typing import List, Dict

from google import genai
from google.genai import types

SYSTEM_PROMPT = (
    "You are DisasterDoc AI, an official Tamil Nadu disaster relief assistant grounded in G.O. (Ms) No. 579 (09.12.2023).\n"
    "STRICT RULES:\n"
    "1. Use ONLY the provided Retrieved Evidence and Verified Calculation Block.\n"
    "2. Never invent relief rates, foreign programs, or unmentioned claim categories.\n"
    "3. When a Verified Calculation Block is given, copy its amounts exactly and call the total the indicative total as per the G.O. Never say the person is eligible or will receive it. The officer decides.\n"
    "4. List required verification documents clearly and cite exact source names and page numbers.\n"
    "5. If the evidence does not contain the answer, say you could not find it in G.O. (Ms) No. 579. Do not guess.\n"
    "6. Write in simple, short English sentences (the answer is translated later).\n"
    "7. Plain text only. No markdown symbols such as #, *, or backticks. For lists use short lines that start with a dash."
)


class GroundedGenerator:
    """Same interface as the old Qwen version, but uses the Gemini API instead of a local model."""

    def __init__(self, model_name: str = None):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it in Hugging Face Space > Settings > Secrets."
            )
        self.client = genai.Client(api_key=api_key)
        primary = model_name or os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
        # If the first model name fails (renamed / limit reached), try the next one.
        self.models = [primary] + [m for m in ("gemini-3.5-flash", "gemini-2.5-flash") if m != primary]

    def generate_grounded_response(
        self, question: str, retrieved_items: List[Dict], verified_calc_block: str = ""
    ) -> Dict:
        evidence_lines = []
        citations = []

        for rank, item in enumerate(retrieved_items, 1):
            c = item["chunk"]
            score = item["similarity_score"]
            evidence_lines.append(
                f"[Source {rank} | {c['source']} | Page {c['page']} | Score: {score}]\n{c['text']}"
            )
            citations.append({
                "source": c["source"],
                "page": c["page"],
                "domain": c["domain"],
                "similarity_score": score,
            })

        user_prompt = (
            f"Retrieved Evidence:\n{chr(10).join(evidence_lines)}\n\n"
            f"{verified_calc_block}\n\n"
            f"User Question: {question}"
        )

        answer = None
        for model in self.models:
            try:
                resp = self.client.models.generate_content(
                    model=model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.0,
                        max_output_tokens=2048,
                    ),
                )
                if resp.text:
                    answer = resp.text.strip()
                    break
            except Exception as e:
                print(f"[Gemini] model '{model}' failed: {e}")

        if not answer:
            answer = (
                "The AI explanation is not available right now. Please try again in a minute.\n\n"
                + (verified_calc_block or "")
            ).strip()

        return {
            "answer": answer,
            "citations": citations,
            "top_similarity": retrieved_items[0]["similarity_score"] if retrieved_items else 0.0,
        }
