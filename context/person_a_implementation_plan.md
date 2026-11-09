# Person A — NLP / ML Implementation Plan

> Source of truth: `context/project.md` and `context/BankSense_Project_Proposal.docx` (they describe the same proposal). This plan is the execution contract for **Person A**, and it is written to interlock with `person_b_implementation_plan.md`. Where the two documents refer to shared paths, schemas, constants, or JSON shapes, the definition is identical in both. If a change is needed, **both documents are updated in the same commit**.

---

## 1. Mission

Own and deliver every **NLP/ML** part of BankSense so that Person B can build the Flask/SQLite/React app around a stable Python interface without touching model internals:

- Prepare and validate the model side of Person B's BANKING77 handoff.
- Train and honestly compare **TF-IDF + Logistic Regression** and **Sentence-BERT + Logistic Regression** on the **same official split**.
- Ship reloadable model artifacts and a small, documented inference API.
- Implement **semantic similarity**, **rule-assisted priority**, and an **optional summariser** with explicit unavailable states.
- Hand off setup notes, metrics, limitations, and a working integration example.

Person A is **not** responsible for the Flask server, SQLite, React, dashboard, dataset acquisition, or any user-facing persistence.

---

## 2. Proposal coverage (what "100%" means for Person A)

Every core feature and deliverable from the proposal maps to a phase below.

| Proposal item | Owner | Phase | Definition of done |
|---|---|---|---|
| §3.1 Intent classification | A | 1, 2, 3 | `predict()` returns BANKING77 label + model confidence for both models |
| §3.2 Priority suggestion | A | 4 | `suggest_priority()` returns `low/medium/high/critical` + reason, no fraud/risk claims |
| §3.3 Semantic similarity | A | 4 | `rank_similar()` ranks candidates by cosine over SBERT embeddings, empty corpus safe |
| §3.4 Complaint summarisation | A | 5 | `summarize()` returns summary or explicit `unavailable`; never fabricates |
| §5 Dataset pipeline (model side) | B owns acquisition, A validates | 1 | Both CSVs load, 77 labels, expected counts, no manual edits |
| §7 Two-pipeline comparison | A | 1, 2 | Accuracy, macro-F1, weighted-F1, per-class P/R/F1, confusion matrix on untouched test |
| §8 Steps 3–5, 7–9 (classify, priority, retrieval, summary) | A | 3, 4, 5 | Callable, documented functions used by B |
| §10 Deliverables 2, 3(API logic), 4, 5, 6 | A | 1–5 | Artifacts + reports + interface exist and are reproducible |
| §10 Deliverable 9 README (NLP sections) | A contributes | 6 | Setup, dataset, evaluation, limitations documented |

---

## 3. Ownership and file boundaries (identical in both plans)

Person A **only** writes inside `backend/nlp/**`, `backend/models/**`, `backend/reports/**`, plus the NLP-owned sections of `README.md`. Person B owns everything else. Do not create a second structure or edit Person B's files without agreement.

```text
BankSense/
├── README.md                      # joint; section owners below
├── .gitignore                     # joint
├── requirements.txt               # Person B (aggregator)
├── data/
│   ├── raw/                       # Person B (immutable source)
│   └── processed/                 # Person B
│       ├── train.csv
│       ├── test.csv
│       ├── dataset_manifest.md
│       └── prepare_banking77.py
├── backend/
│   ├── __init__.py                # Person B
│   ├── app.py                     # Person B
│   ├── config.py                  # Person B (DB path, port, CORS)
│   ├── requirements.txt           # Person B (Flask runtime)
│   ├── routes/                    # Person B
│   │   ├── complaints.py
│   │   ├── analytics.py
│   │   └── health.py
│   ├── services/                  # Person B
│   │   └── complaint_service.py
│   ├── db/                        # Person B
│   │   ├── connection.py
│   │   └── schema.sql
│   ├── tests/                     # Person B (test_db.py, test_api_*.py)
│   ├── nlp/                       # Person A ONLY
│   │   ├── __init__.py
│   │   ├── config.py              # shared constants (MAX_TEXT_LENGTH, SUPPORTED_MODELS, PRIORITIES, paths)
│   │   ├── data.py                # load/validate Person B CSVs
│   │   ├── preprocess.py          # model-specific transforms
│   │   ├── train.py               # build + fit both pipelines
│   │   ├── evaluate.py            # metrics + reports
│   │   ├── predictor.py           # predict(), predict_top_k(), health()
│   │   ├── similarity.py          # rank_similar()
│   │   ├── priority.py            # suggest_priority()
│   │   ├── summarizer.py          # summarize(), summary_status()
│   │   ├── requirements.txt       # Person A deps
│   │   └── tests/                 # Person A smoke tests
│   ├── models/                    # Person A artifacts (git-ignored)
│   │   ├── tfidf_logreg.joblib
│   │   ├── sbert_logreg.joblib
│   │   ├── sbert_model_name.txt
│   │   └── label_classes.json
│   └── reports/                   # Person A
│       ├── model_comparison.json
│       ├── classification_report_tfidf.csv
│       ├── classification_report_sbert.csv
│       ├── confusion_matrix_tfidf.csv
│       ├── confusion_matrix_sbert.csv
│       └── evaluation_manifest.md
└── frontend/                      # Person B
```

**Import rule (prevents integration failures):** the backend is a package run from the repo root with `python -m backend.app`. All cross-module imports are absolute, e.g. `from backend.nlp.predictor import predict`. Person B adds no `sys.path` hacks; Person A exposes no top-level modules outside `backend/nlp`.

**Local run (both):** venv + `pip install -r requirements.txt`; backend from repo root. Only Person B owns the root aggregator:

```text
# requirements.txt (Person B)
-r backend/requirements.txt
-r backend/nlp/requirements.txt
```

---

## 4. Shared contracts (must match Person B exactly)

These definitions are duplicated verbatim in Person B's plan. Change both together.

### 4.1 Processed-data contract (Person B → Person A)

Files: `data/processed/train.csv`, `data/processed/test.csv`, UTF-8, header row, comma-separated, **no pandas index column**.

| column | type | rule |
|---|---|---|
| `example_id` | string | `train-000001` / `test-000001`, deterministic |
| `text` | string | original BANKING77 text, unchanged |
| `normalized_text` | string | trim + collapse whitespace only |
| `label` | string | exact BANKING77 intent label |

Expected: 77 labels; ~10,003 train / ~3,080 test (record any source difference, do not force counts). `dataset_manifest.md` must state source URL, access date, HF config/version, raw filenames + checksums, row counts, label count, null/empty/duplicate checks, cleaning steps, and the "test set untouched" rule.

### 4.2 Shared constants (`backend/nlp/config.py`, owned by Person A, imported by Person B)

```python
MAX_TEXT_LENGTH = 2000
SUPPORTED_MODELS = ("tfidf", "sbert")
DEFAULT_MODEL = "tfidf"
PRIORITIES = ("low", "medium", "high", "critical")   # ascending severity
MODELS_DIR = <env BANKSENSE_MODELS_DIR or backend/models>
REPORTS_DIR = <env BANKSENSE_REPORTS_DIR or backend/reports>
```

Person B imports `MAX_TEXT_LENGTH`, `SUPPORTED_MODELS`, `PRIORITIES` from here instead of redefining them, so validation cannot drift.

### 4.3 Python interface (Person A → Person B)

```python
# backend/nlp/predictor.py
SUPPORTED_MODELS: tuple[str, ...]
class NLPError(Exception): ...
class InvalidInputError(NLPError): ...
class UnknownModelError(NLPError): ...
class ArtifactUnavailableError(NLPError): ...

def predict(text: str, model_name: str = "tfidf") -> dict:
    # {"intent": str, "confidence": float, "model": str}

def predict_top_k(text: str, model_name: str = "tfidf", k: int = 3) -> list[dict]:
    # [{"intent": str, "confidence": float}, ...]  (descending confidence)

def health() -> dict:
    # {"tfidf": bool, "sbert": bool, "summary": "enabled"|"unavailable"}
```

```python
# backend/nlp/priority.py
PRIORITIES: tuple[str, ...]
def suggest_priority(text: str, intent: str) -> dict:
    # {"priority": "low|medium|high|critical",
    #  "priority_reason": "Rule matched: ...",
    #  "rule_id": "unauthorised_card|duplicate_charge|cash_access|refund|informational|fallback"}
```

```python
# backend/nlp/similarity.py
def rank_similar(query_text: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    # candidates: [{"id": <str>, "text": <str>, ...passthrough...}]
    # returns the same dicts + {"similarity": float in [0,1]}, sorted desc, at most top_k
    # empty candidates -> []
```

```python
# backend/nlp/summarizer.py
def summary_status() -> str:  # "enabled" | "unavailable"
def summarize(text: str, max_len: int = 60) -> dict:
    # {"status": "ok", "summary": str, "summary_status": "enabled"}
    # {"status": "unavailable", "summary": None, "summary_status": "unavailable", "reason": str}
```

Rules: models are loaded **once per process** (cached loader), never per request. `confidence` is real `predict_proba` output, not calibrated. Empty/whitespace input raises `InvalidInputError`; unknown model raises `UnknownModelError`; missing artifact raises `ArtifactUnavailableError`. All returns are plain Python/JSON-serialisable.

### 4.4 HTTP contract (Person B implements, both agree)

`POST /api/complaints/analyze`
```json
// request
{"text": "I was charged twice for the same purchase.", "model": "tfidf"}
```
```json
// 200
{
  "complaint_id": 12,
  "text": "I was charged twice for the same purchase.",
  "intent": "transaction_charged_twice",
  "confidence": 0.82,
  "model": "tfidf",
  "priority": "high",
  "priority_reason": "Rule matched: duplicate or repeated charge",
  "similar_cases": [
    {"complaint_id": 3, "text": "...", "intent": "...", "similarity": 0.91, "source": "demo"}
  ],
  "summary": null,
  "summary_status": "unavailable",
  "source": "submitted",
  "created_at": "2026-11-09T12:00:00Z"
}
```
Error envelope (all errors):
```json
{"error": {"code": "VALIDATION_ERROR|UNKNOWN_MODEL|MODEL_UNAVAILABLE|INFERENCE_ERROR|NOT_FOUND", "message": "...", "field": "text"}}
```
Status mapping: 400 invalid/blank/too-long JSON or unknown model; 503 model unavailable; 500 inference failure; 404 unknown id. `confidence` rounded to 4 decimals in transport.

`GET /api/complaints?limit=20&offset=0` → `{"items": [...], "count": n}`.
`GET /api/analytics` → `{"total_complaints": n, "by_intent": [{"intent": str, "count": n}], "by_priority": [{"priority": str, "count": n}], "most_common_intents": [...], "includes_demo": bool}`.
`GET /api/health` → `{"status": "ok", "models": {"tfidf": bool, "sbert": bool}, "summary": "enabled|unavailable", "database": "ok"}`.

### 4.5 Analytics/DB conventions

`complaints` table: `id` (PK), `text`, `normalized_text`, `intent`, `confidence`, `model`, `priority`, `priority_reason`, `summary` nullable, `summary_status`, `source` (`submitted`|`demo`), `created_at` (ISO-8601 UTC). **Decision:** `similar_cases` are derived at request time and **not persisted** (keeps schema minimal; documented in README). `source` is the single demo marker used everywhere.

### 4.6 Priority scale

`low < medium < high < critical`. Must cover at least: unauthorised card activity → `critical`; duplicate/repeated charge → `high`; cash-withdrawal/refund access issues → `medium`; informational intents → `low`; unmatched → `low` with a documented fallback reason. Every output includes the matched rule and a plain-language reason. Never describe it as risk/fraud scoring.

---

## 5. Prerequisites

- Python 3.10+ with a venv.
- Person A deps (`backend/nlp/requirements.txt`): `pandas`, `numpy`, `scikit-learn`, `joblib`, `sentence-transformers`, `nltk` (only if used). Pin versions where practical. Summariser dep is **optional** and must not be required for core flow.
- Network access once to download the Sentence-BERT model (`all-MiniLM-L6-v2`). Cache it locally; document the requirement and offline limitation.
- Person B's `data/processed/` files + manifest.

---

## 6. Detailed work plan (two-day timeline, interlocked with Person B)

### Phase 0 — Contract + scaffold (Day 1, first 30–45 min)

1. Re-read `project.md`, the `.docx`, and Person B's plan. Confirm the contracts in §4 with Person B in writing (this document + Person B's mirror).
2. Create `backend/nlp/` package skeleton (`__init__.py`, `config.py`, module stubs), `backend/nlp/requirements.txt`, and `backend/nlp/tests/`. Do **not** create files outside Person A's ownership.
3. Put shared constants in `backend/nlp/config.py` and tell Person B to import them.
4. Ask Person B to confirm data paths, schema, and the exact JSON shapes; ask for a small sample of `train.csv` early if the full prep is still running.

**Exit check:** Person B can import `backend.nlp.config`; both agree on §4; Person A knows when `data/processed/` will be ready.

### Phase 1 — Data validation + baseline classifier (Day 1 AM)

1. `data.py`: load both CSVs, assert required columns, non-null/non-empty `text`, label parity between splits, 77 unique labels, row counts vs manifest; record duplicate counts and per-label distribution. Report anomalies to Person B; never silently alter/delete rows.
2. `preprocess.py`: choose `text` or `normalized_text` (record the choice per model); TF-IDF needs no aggressive cleaning; keep preprocessing deterministic.
3. Create a **stratified validation split from `train.csv` only** (e.g. 90/10, `random_state=42`) for tuning. The official test set is never used here.
4. `train.py` baseline: `Pipeline([("tfidf", TfidfVectorizer(lowercase=True, ngram_range=(1,2), min_df=2, max_df=0.9, sublinear_tf=True, strip_accents="unicode")), ("clf", LogisticRegression(C=1.0, max_iter=2000, solver="lbfgs", n_jobs=-1))])`. Tune a tiny grid (`ngram_range`, `min_df`, `C`) on the validation split by macro-F1.
5. Fit on the full training partition once choices are fixed; `joblib.dump` to `backend/models/tfidf_logreg.joblib`.
6. Quick check: reload artifact in a fresh process and predict a sample; confidence in `[0, 1]`.

**Exit check:** data report written; baseline artifact reloads and predicts; no test-set leakage.

### Phase 2 — Sentence-BERT classifier + honest comparison (Day 1 PM)

1. `preprocess.py`/`train.py`: encode training text with `SentenceTransformer("all-MiniLM-L6-v2")` (`batch_size=64`, `normalize_embeddings=True`); **cache** embeddings (`.npy` + input hash) to avoid re-encoding.
2. Train `LogisticRegression` on the cached embeddings with the same labels/rows; tune `C` on the validation split by macro-F1.
3. Save `sbert_logreg.joblib` + `sbert_model_name.txt` (`all-MiniLM-L6-v2`); keep `label_classes.json` (ordered class strings) so both models decode identically.
4. `evaluate.py`: after all choices are frozen, evaluate **both models once on the untouched official test partition**. Produce `model_comparison.json` (config, split sizes, accuracy, macro-F1, weighted-F1, seed, text field, date), per-class `classification_report_*.csv`, and `confusion_matrix_*.csv` (raw counts). Write `evaluation_manifest.md` describing the split and that test was used only here.
5. Note embedding download, CPU/GPU, and inference latency.

**Exit check:** both artifacts reload in a clean process; metrics are measured, traceable to the official test split, and no claim of superiority is made without these numbers.

### Phase 3 — Stable inference interface (Day 2 AM)

1. `predictor.py`: cached model/encoder loaders; `predict`, `predict_top_k`, `health`; exceptions from §4.3.
2. Validate input and model name; decode labels via `label_classes.json` (or `classes_`) in one place; return plain JSON-safe values.
3. Add `backend/nlp/tests/test_predictor.py` (valid label, confidence range, empty input, unknown model, missing artifact path).
4. Write a short usage snippet + sample output to hand to Person B.

**Exit check:** Person B can call `predict()`/`predict_top_k()` for both models and insert results into the API without touching model objects.

### Phase 4 — Similarity + priority (Day 2 AM/PM)

**Similarity**
1. `similarity.py`: encode query + candidate texts with the same SBERT encoder, cosine = dot of L2-normalised vectors; return ranked matches with `similarity`; empty candidates → `[]`; be robust to blank candidate text.
2. Accept candidates from Person B (pure function, no DB). Explain to Person B that `source` travels through unchanged so demo rows stay labelled.
3. Test: empty corpus, identical text → similarity ≈ 1.0, ordering.

**Priority**
1. Implement `priority.py` per §4.6 with a small reviewable rule table (intent sets + explicit text conditions, evaluated in severity order).
2. Every path returns `rule_id`, `priority`, and a reason string; unmatched → `low` fallback.
3. Test the required cases (unauthorised card → critical, duplicate charge → high, etc.).

**Exit check:** both functions callable independently; reasons present; no fraud/risk claims.

### Phase 5 — Optional summariser (Day 2 PM, only after core path)

1. `summarizer.py`: try a small local pretrained summariser or approved API; core submission must not require an API key.
2. If unavailable, return the explicit `unavailable` shape (§4.3) with a reason; optionally a clearly labelled extractive fallback. Never fabricate.
3. Expose `summary_status()` so Person B can render the state; share expected latency.

**Exit check:** `summarize()` either returns a real summary or a visible `unavailable`; submission flow still succeeds.

### Phase 6 — Integration, docs, handoff (Day 2 PM, joint with Person B)

1. Pair on one end-to-end call: submit text → `predict` → `suggest_priority` → `rank_similar` (B supplies DB candidates) → `summarize` → B persists → React renders.
2. Fix import/path/serialization/dependency mismatches (absolute `backend.*` imports; `python -m backend.app`).
3. Write README NLP sections: Python/deps, dataset + manifest, training/eval commands, artifact locations, model selection, measured results + split, limitations (benchmark data, confidence meaning, priority not risk, test discipline).
4. Add `backend/models/` and generated DB/embedding caches to `.gitignore`; document regeneration.
5. Confirm metrics are identical across README, dashboard, and demo script.

**Exit check:** full workflow runs from documented commands; Person B confirms every A-owned feature is wired; incomplete items are explicitly marked with a safe disabled state.

---

## 7. Verification checklist (Person A)

- [ ] `train.csv`/`test.csv` load unedited; counts, 77 labels, nulls, duplicates recorded against the manifest.
- [ ] Validation split comes only from train; test used once, after choices frozen.
- [ ] TF-IDF vectoriser + classifier live in one Pipeline; fit only on train.
- [ ] Both pipelines use the same official split and the same label strings.
- [ ] `model_comparison.json` + per-class reports + confusion matrices saved with config and split details.
- [ ] Both artifacts reload in a clean process; predictions return a real BANKING77 label and confidence in `[0, 1]`.
- [ ] `predict`, `predict_top_k`, `health` match §4.3; empty/unknown/missing-artifact behaviours defined.
- [ ] `rank_similar` sorts by cosine, handles empty corpus, passes `source` through untouched.
- [ ] `suggest_priority` covers required rules, always returns a reason, uses the exact `PRIORITIES` scale.
- [ ] `summarize` unavailable path is explicit and never blocks submission.
- [ ] Person B has a working import example and the documented contract is unchanged.
- [ ] README NLP sections and limitations are complete and consistent with the reports.

---

## 8. Time-box and fallback order

1. Data validation + TF-IDF classifier + `predictor.predict` (working baseline).
2. Priority rules + similarity (Person B can then wire the full flow).
3. Sentence-BERT classifier + honest comparison.
4. Extractive/optional summariser.
5. Report polish and docs.

If SBERT compute/download blocks progress: ship the baseline, keep `sbert` returning `ArtifactUnavailableError`, and state the blocker in the report. **Never claim a model was trained/evaluated if it was not.**

---

## 9. Handoff package to Person B

- [ ] `data/processed/` validated; report shared.
- [ ] `backend/models/` artifacts + `label_classes.json` + `sbert_model_name.txt`.
- [ ] `backend/reports/` metrics + `evaluation_manifest.md`.
- [ ] `backend/nlp/config.py` constants importable by B.
- [ ] `predict`, `predict_top_k`, `health`, `suggest_priority`, `rank_similar`, `summarize`, `summary_status` implemented per §4.
- [ ] Usage snippet + sample outputs for both models.
- [ ] README NLP sections + limitations.
- [ ] Confirmation that the end-to-end walkthrough passed with Person B.
