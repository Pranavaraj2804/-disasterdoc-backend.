from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
import os, shutil, time, uuid, json

from backend.rag.embeddings import EmbeddingEngine
from backend.rag.vector_store import FAISSVectorStore
from backend.rag.retrieval import SemanticRetriever
from backend.rag.generation import GroundedGenerator
from backend.document_processing.ocr import OCREngine
from backend.document_processing.classifier import DocumentClassifier
from backend.document_processing.quality_checker import EvidenceQualityChecker
from backend.document_processing.privacy import PrivacyService
from backend.evidence.extraction import ApplicantFieldExtractor
from backend.evidence.consistency import PairwiseConsistencyEngine
from backend.evidence.matching import ReliefAndEvidenceMatcher
from backend.evidence.confidence import ConfidenceAbstainEngine
from backend.guidance.multilingual import MultilingualService
from backend.guidance.deadline_tracker import DeadlineTracker
from backend.guidance.voice_service import VoiceAndTamilService
from backend.reports.submission_pack import SubmissionPackExporter
from backend.rule_changes.impact_analyzer import RuleChangeImpactTracker

app = FastAPI(title="DisasterDoc AI API (Text & Voice Enabled)", version="2.4")

# Set ALLOWED_ORIGINS in Space secrets later, e.g. "https://yoursite.com". "*" = anyone (ok for testing).
ALLOWED = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

TMP_DIR = "backend/storage/tmp_uploads"
PACK_DIR = "backend/storage/packs"
AUDIO_DIR = "backend/storage/voice_responses"
DEFAULT_NOTICE = "Claims close 30 days after publication."
for d in (TMP_DIR, PACK_DIR, AUDIO_DIR):
    os.makedirs(d, exist_ok=True)

app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")
app.mount("/packs", StaticFiles(directory=PACK_DIR), name="packs")

embedder = EmbeddingEngine()
store = FAISSVectorStore()
store.load()
retriever = SemanticRetriever(embedder, store)
generator = GroundedGenerator()

ocr_engine = OCREngine()
classifier = DocumentClassifier()
quality_checker = EvidenceQualityChecker()
privacy_service = PrivacyService()
field_extractor = ApplicantFieldExtractor()
consistency_engine = PairwiseConsistencyEngine()
matcher = ReliefAndEvidenceMatcher()
confidence_engine = ConfidenceAbstainEngine()
multilingual = MultilingualService()
deadline_tracker = DeadlineTracker()
voice_service = VoiceAndTamilService()
pack_exporter = SubmissionPackExporter()
impact_tracker = RuleChangeImpactTracker()


def cleanup_old(folder: str, max_age_seconds: int = 3600):
    """Delete files older than 1 hour (privacy: do not keep users' documents)."""
    now = time.time()
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        try:
            if now - os.path.getmtime(path) > max_age_seconds:
                shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
        except Exception:
            pass


def process_claim(query, language, enable_voice, notice_text, publication_date, files):
    for d in (TMP_DIR, PACK_DIR, AUDIO_DIR):
        cleanup_old(d)

    files = [f for f in files if f.filename]
    norm_q = voice_service.normalize_query_to_english(query)
    en_query = norm_q["english_query"]
    target_lang = language if language else norm_q["detected_lang"]

    req_dir = os.path.join(TMP_DIR, uuid.uuid4().hex)
    os.makedirs(req_dir, exist_ok=True)
    processed_docs = []
    extracted_records = []

    try:
        for idx, f in enumerate(files, 1):
            tmp_path = os.path.join(req_dir, os.path.basename(f.filename))
            with open(tmp_path, "wb") as out:
                shutil.copyfileobj(f.file, out)

            ocr_res = ocr_engine.extract_text(tmp_path)
            doc_type = classifier.classify(ocr_res["full_masked_text"], f.filename)
            qual_res = quality_checker.check_file(tmp_path, ocr_res["full_masked_text"], doc_type)
            fields = field_extractor.extract_fields(f"DOC_{idx}", doc_type, ocr_res["full_masked_text"])

            processed_docs.append({
                "doc_id": f"DOC_{idx}",
                "filename": f.filename,
                "file_path": tmp_path,
                "doc_type": doc_type,
                "quality": qual_res,
                "fields": fields,
            })
            extracted_records.append(fields)

        consistency_report = consistency_engine.compare_all_pairs(extracted_records)
        has_mismatch = any(c["status"] == "MISMATCH" for c in consistency_report)

        claim_eval = matcher.evaluate_claim(en_query, [d["doc_type"] for d in processed_docs])
        hits = retriever.retrieve(en_query, top_k=5)

        calc_summary = "\n".join(
            [f"• {b['category']}: {b['calculation']} = Rs. {b['amount']:,}" for b in claim_eval["breakdown"]]
        )
        calc_block = (
            f"VERIFIED G.O. 579 CALCULATION:\n{calc_summary}\nTotal Payable: Rs. {claim_eval['total_payable_inr']:,}/-"
            if calc_summary else ""
        )

        rag_res = generator.generate_grounded_response(en_query, hits, verified_calc_block=calc_block)
        conf_res = confidence_engine.evaluate(
            rag_res["top_similarity"],
            [d["quality"]["quality_score"] for d in processed_docs],
            has_mismatch,
        )
        deadline_res = deadline_tracker.extract_and_compute(notice_text, publication_date)
        lang_res = multilingual.translate_with_source(
            rag_res["answer"],
            hits[0]["chunk"]["text"] if hits else "",
            f"{hits[0]['chunk']['source']} (Page {hits[0]['chunk']['page']})" if hits else "G.O. (Ms) No. 579",
            target_lang=target_lang,
        )

        audio_url = None
        if enable_voice:
            mp3_path = voice_service.synthesize_speech(lang_res["translated_guidance"], lang=target_lang)
            audio_url = f"/audio/{os.path.basename(mp3_path)}"

        applicant_name = next((r["name"] for r in extracted_records if r.get("name")), "Applicant")
        pack_file = f"pack_{uuid.uuid4().hex[:12]}.pdf"   # unique name per request (no mixing users)
        pack_exporter.generate_pdf(
            applicant_name, claim_eval["document_checklist"], processed_docs,
            output_path=os.path.join(PACK_DIR, pack_file),
        )
    finally:
        shutil.rmtree(req_dir, ignore_errors=True)  # delete uploaded documents right away

    public_docs = [{k: v for k, v in d.items() if k != "file_path"} for d in processed_docs]

    return {
        "response_mode": "voice" if enable_voice else "text",
        "detected_language": target_lang,
        "query_info": norm_q,
        "relief_calculation": claim_eval,
        "grounded_guidance": lang_res,
        "voice_audio_url": audio_url,
        "citations": rag_res["citations"],
        "document_reviews": public_docs,
        "cross_document_consistency": consistency_report,
        "confidence_guardrail": conf_res,
        "deadline_status": deadline_res,
        "submission_pack_url": f"/packs/{pack_file}",
    }


@app.get("/")
def health():
    return {"status": "ok", "service": "DisasterDoc AI"}


@app.post("/api/evaluate-claim")
def evaluate_claim(
    query: str = Form(...),
    language: Optional[str] = Form(None),
    enable_voice: bool = Form(False),
    notice_text: str = Form(DEFAULT_NOTICE),
    publication_date: Optional[str] = Form(None),
    files: List[UploadFile] = File(default=[]),
):
    """TEXT MODE: user types Tamil/English -> reply text in the same language."""
    return process_claim(query, language, enable_voice, notice_text, publication_date, files)


@app.post("/api/voice-query")
def voice_query(
    audio: UploadFile = File(...),
    files: List[UploadFile] = File(default=[]),
):
    """VOICE MODE: user speaks Tamil/English -> text + MP3 reply in the same language."""
    req_dir = os.path.join(TMP_DIR, uuid.uuid4().hex)
    os.makedirs(req_dir, exist_ok=True)
    try:
        audio_path = os.path.join(req_dir, os.path.basename(audio.filename or "voice.webm"))
        with open(audio_path, "wb") as out:
            shutil.copyfileobj(audio.file, out)
        stt = voice_service.transcribe_audio_auto(audio_path)
    finally:
        shutil.rmtree(req_dir, ignore_errors=True)

    if not stt["text"]:
        return {"error": "குரல் தெளிவாகப் புரியவில்லை. மீண்டும் பேசவும். / Could not recognize speech clearly. Please speak again."}

    result = process_claim(stt["text"], stt["detected_lang"], True, DEFAULT_NOTICE, None, files)
    result["transcribed_speech"] = stt["text"]
    return result


@app.post("/api/rule-change")
def rule_change(
    old_text: str = Form(...),
    new_text: str = Form(...),
    old_version: str = Form("Old notice"),
    new_version: str = Form("Revised notice"),
    effective_date: Optional[str] = Form(None),
    checklist: Optional[str] = Form(None),   # JSON list, e.g. ["Identity Proof","Bank Passbook"]
    query: str = Form(""),                   # used only if checklist is not sent
):
    """RULE-CHANGE TRACKER: compare two notice versions, flag only the affected checklist items."""
    if checklist:
        items = [{"required_doc": d, "status": "UNKNOWN"} for d in json.loads(checklist)]
    else:
        items = matcher.evaluate_claim(query, [])["document_checklist"]
    return impact_tracker.compare_versions(
        {"version": old_version, "text": old_text},
        {"version": new_version, "text": new_text, "effective_date": effective_date},
        items,
    )
