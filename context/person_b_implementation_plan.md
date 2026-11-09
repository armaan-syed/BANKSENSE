# Person B — Backend, Data, Frontend, and Integration Plan

> Source of truth: `context/project.md` and `context/BankSense_Project_Proposal.docx` (they describe the same proposal). This plan is the execution contract for **Person B**, and it is written to interlock with `person_a_implementation_plan.md`. Where the two documents refer to shared paths, schemas, constants, or JSON shapes, the definition is identical in both. If a change is needed, **both documents are updated in the same commit**.

---

## 1. Mission

Own and deliver every **application** part of BankSense around Person A's NLP interface:

- Acquire and prepare BANKING77 into a split-preserving handoff package.
- Build the FastAPI service, SQLite persistence, request/response validation, and error behaviour.
- Build the React complaint submission + result flow and the analytics dashboard from real stored records.
- Own dataset/manifest, orchestration, persistence, demo-data labelling, setup docs, and end-to-end integration.

Person B does **not** train models, reimplement classification/retrieval logic, or edit Person A's `backend/nlp/**`, `backend/models/**`, or `backend/reports/**`.

---

## 2. Proposal coverage (what "100%" means for Person B)

| Proposal item | Owner | Phase | Definition of done |
|---|---|---|---|
| §3.1 Intent classification (UI/API surface) | B serves A's model | 3, 4 | UI shows intent + model confidence from API |
| §3.2 Priority suggestion (surface) | B serves A's rules | 3, 4 | UI shows priority + reason, labelled as rule suggestion |
| §3.3 Semantic similarity (surface) | B supplies candidates | 3, 4 | API returns similar cases from stored rows via `rank_similar` |
| §3.4 Summarisation (surface) | B serves A's summariser | 3, 4 | UI shows summary only when present; unavailable state clear |
| §3.5 Analytics dashboard | B | 5 | Counts, intent distribution, priority breakdown from SQLite |
| §5 Dataset pipeline (acquisition) | B | 1 | Repeatable prep script + manifest + split-preserving CSVs |
| §6 Stack (FastAPI, SQLite, React, Plotly) | B | 2–5 | App runs with documented commands |
| §8 Workflow steps 1–2, 6, 10 | B | 3–5 | Submit → API → result → persisted → dashboard |
| §10 Deliverables 1, 3 (server), 7, 8, 9 | B | 1–6 | Data package, API, React UI, dashboard, README |
| §11 Limitations surfaced in UI/README | B | 4–6 | Demo marker, confidence/priority disclaimers visible |

---

## 3. Ownership and file boundaries (identical in both plans)

Person B **only** writes inside `data/**`, `backend/{app.py,config.py,routes,services,db,tests}/**`, `frontend/**`, `scripts/**`, the root `requirements.txt`, and the app-owned sections of `README.md`. Person A owns `backend/nlp/**`, `backend/models/**`, `backend/reports/**`.

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
│   ├── app.py                     # Person B (FastAPI app, routers, middleware)
│   ├── config.py                  # Person B (DB path, port, CORS)
│   ├── schemas.py                 # Person B (Pydantic request/response models)
│   ├── requirements.txt           # Person B (FastAPI runtime)
│   ├── routes/                    # Person B
│   │   ├── __init__.py
│   │   ├── complaints.py
│   │   ├── analytics.py
│   │   └── health.py
│   ├── services/                  # Person B
│   │   ├── __init__.py
│   │   └── complaint_service.py
│   ├── db/                        # Person B
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   └── schema.sql
│   ├── tests/                     # Person B (test_db.py, test_api_*.py)
│   ├── nlp/                       # Person A ONLY — do not edit
│   ├── models/                    # Person A ONLY — read-only at runtime
│   └── reports/                   # Person A ONLY
└── frontend/                      # Person B
    └── src/
        ├── api/
        ├── components/
        └── pages/
```

**Import rule (prevents integration failures):** the backend is a package served from the repo root with `uvicorn backend.app:app --reload --port 8000`. All imports are absolute, e.g. `from backend.nlp.predictor import predict, predict_top_k, health as nlp_health`. Do not add `sys.path` hacks or import `nlp.*` directly.

**Local run (both):** venv + `pip install -r requirements.txt`; backend from repo root. Person B owns the root aggregator:

```text
# requirements.txt (Person B)
-r backend/requirements.txt
-r backend/nlp/requirements.txt
```

---

## 4. Shared contracts (must match Person A exactly)

These definitions are duplicated verbatim in Person A's plan. Change both together.

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

Rules: models load once per process. Person B calls these functions **once per request**; it never loads model artifacts itself and never duplicates inference logic. Person B maps Person A's exceptions to HTTP errors (see §4.4).

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

`low < medium < high < critical`. Person B treats the value as opaque but validates it against `PRIORITIES`, and the UI labels it as a **rule suggestion**, never a fraud/risk score.

---

## 5. Prerequisites

- Python 3.10+ venv; Node 18+ for React; network access to download BANKING77 once.
- Person B deps (`backend/requirements.txt`): `fastapi[standard]` (includes Uvicorn + Pydantic), `pytest`, `httpx` (for FastAPI `TestClient`); pin where practical. CORS uses Starlette's built-in `CORSMiddleware` (no extra package). Frontend deps via `frontend/package.json`.
- Person A's modules/artifacts for the real integration (Person B can build and test with monkeypatched Person A functions before artifacts exist).
- Agreed shared constants module path: `backend/nlp/config.py`.

---

## 6. Detailed work plan (two-day timeline, interlocked with Person A)

### Phase 0 — Contract + scaffold (Day 1, first 30–45 min)

1. Re-read `project.md`, the `.docx`, and Person A's plan. Confirm §4 in writing.
2. Create the backend package skeleton (`backend/__init__.py`, `app.py`, `config.py`, `schemas.py`, `routes/`, `services/`, `db/`, `tests/`), the FastAPI app (`app = FastAPI(...)` with grouped `APIRouter`s, `CORSMiddleware`, and custom exception handlers), root `requirements.txt` aggregator, `.gitignore`, and the React scaffold. Stay inside Person B's ownership.
3. Freeze the HTTP contract, error envelope, `source` values, and summary-unavailable representation; share with Person A and the frontend.
4. Import shared constants from `backend.nlp.config` (coordinate with Person A so the file exists early).

**Exit check:** contract agreed; backend skeleton imports; Person A can import `backend.nlp.config`; data-prep plan confirmed.

### Phase 1 — Acquire and prepare BANKING77 (Day 1 AM — do this FIRST, it unblocks Person A)

1. `data/processed/prepare_banking77.py`: download BANKING77 from the PolyAI/HF source; keep `data/raw/` immutable; export the **official** train/test partitions to `data/processed/train.csv` / `test.csv`.
2. Schema exactly per §4.1 (`example_id`, `text`, `normalized_text`, `label`); deterministic ids; original `text` unchanged.
3. Conservative cleaning only (trim/collapse whitespace in `normalized_text`); no stopword removal/stemming/lemmatising; no row deletion; preserve labels.
4. Validate: required columns, null/empty text, row counts, 77 labels, train/test label parity, duplicate counts, class distribution.
5. Write `dataset_manifest.md` with source, access date, HF config/version, raw checksums, counts, validation results, cleaning steps, and the untouched-test rule.
6. Tell Person A immediately when files are ready; share a loading snippet.

**Exit check:** Person A loads both files unedited and confirms counts/labels match the manifest.

### Phase 2 — FastAPI foundation + SQLite (Day 1 AM, after data prep starts)

1. `app.py`: create `app = FastAPI(title="BankSense", version="0.1.0")`; add `CORSMiddleware` for local dev; include `APIRouter`s; register exception handlers that emit the §4.4 error envelope. Custom `RequestValidationError` handler must return **400** (not FastAPI's default 422) and an `HTTPException` handler must return the same envelope (including 404).
2. `schemas.py`: Pydantic request models (`AnalyzeRequest`: `text: str`, `model: str = "tfidf"`) and response models (`ComplaintResult`, `ComplaintList`, `Analytics`, `Health`, `ErrorEnvelope`) matching §4.4 exactly. Validation length/blank checks happen in the service (using `MAX_TEXT_LENGTH`) so the error code is `VALIDATION_ERROR`, not a Pydantic 422.
3. `config.py`: `BANKSENSE_DB_PATH` (default documented local data dir), CORS origins from env, never commit secrets; run with `uvicorn backend.app:app --reload --port 8000` from the repo root.
4. **Concurrency:** define route handlers as plain `def` (not `async def`) so FastAPI runs the blocking NLP/SQLite work in its threadpool; do not call blocking model inference inside `async def`.
5. `db/schema.sql` + `db/connection.py`: idempotent init, parameterized queries, `complaints` table per §4.5; document reset.
6. `GET /api/health`: report DB ok and Person A's model availability via `backend.nlp.predictor.health()` — never claim a model is loaded when it is not.
7. `services/complaint_service.py`: the only place that calls Person A's functions and writes rows. Routes stay thin.
8. `backend/tests/`: DB init/CRUD tests and API tests using `fastapi.testclient.TestClient` with `monkeypatch` for Person A's functions (no duplicated model logic). Free OpenAPI docs available at `/docs` and `/openapi.json`.

**Exit check:** `uvicorn` starts, DB initializes, a row inserts/reads, `/docs` renders, health reflects reality.

### Phase 3 — Complaint analysis API (Day 1 PM)

1. `POST /api/complaints/analyze`: validate JSON, non-blank `text`, `MAX_TEXT_LENGTH`, `model ∈ SUPPORTED_MODELS`; map `InvalidInputError`→400, `UnknownModelError`→400, `ArtifactUnavailableError`→503, unexpected→500. Malformed JSON / wrong field types are caught by the `RequestValidationError` handler and returned as 400 `VALIDATION_ERROR` per §4.4 (not 422).
2. Orchestrate exactly once: `predict(text, model)` → `suggest_priority(text, intent)` → fetch candidate rows → `rank_similar(text, candidates, top_k=5)` → `summarize(text)` if `summary_status()=="enabled"`.
3. Persist only after successful analysis: core fields per §4.5, `source="submitted"`, UTC timestamp; `similar_cases` not persisted.
4. Return the §4.4 response (round confidence to 4 dp; summary `null` + `summary_status` when unavailable).
5. `GET /api/complaints`: bounded pagination, include `source`; don't over-expose fields.
6. `GET /api/analytics`: aggregate from SQLite only; zero/empty shapes on a new DB; `includes_demo` uses one consistent rule.
7. Tests: invalid JSON, blank, too long, unknown model, model-unavailable, happy path persistence, empty-DB analytics.

**Exit check:** curl submits a query, receives structured analysis, and the record + analytics reflect it.

### Phase 4 — React submission + result flow (Day 2 AM)

1. One `frontend/src/api/` module for all API calls (base URL from env, e.g. `VITE_API_BASE_URL`), no scattered fetch.
2. Complaint form: text area with character counter (`MAX_TEXT_LENGTH`), submit state, clear validation, prevent duplicate submits while pending.
3. Result view: intent, model confidence (labelled "model confidence"), model name, priority + reason (labelled "rule suggestion"), similar cases with similarity scores and `source`/demo labels, summary only when present with explicit unavailable state.
4. Loading/pending/empty/error states; show backend error messages; preserve entered text on failure.
5. Keep the flow linear (submit → result → optional related cases); no out-of-scope features before the core path is stable.

**Exit check:** browser submission shows the API result without manual refresh.

### Phase 5 — Dashboard + history (Day 2 PM)

1. Summary cards: total analyzed, priority counts.
2. Intent distribution and priority breakdown charts (Plotly) from `/api/analytics`; handle empty/no-data without fake values.
3. Recent complaints/history list (bounded), marking demo vs submitted.
4. Loading/error states; readable at the demo viewport; doesn't obscure submission.
5. If seed/demo rows are inserted, insert via the DB/service with `source="demo"` (never through a fake prediction path) and clearly label them.

**Exit check:** dashboard values reconcile with SQLite rows and update after a successful submission.

### Phase 6 — Integration, docs, demo (Day 2 PM, joint with Person A)

1. Wire Person A's real modules/artifacts; verify startup with artifacts present and a clear failure state when absent.
2. Walk the full path: submit → classify → priority → similarity → summary state → persist → render → analytics update.
3. Fix CORS/API URL config; document exact startup commands for backend (`uvicorn backend.app:app --reload --port 8000` from repo root) and frontend.
4. README app sections: prerequisites, Python/Node versions, install, DB init/reset, run commands, env vars, endpoint reference, demo-data note. Person A writes the NLP/evaluation sections.
5. Ensure no secrets committed; `.gitignore` covers DB files, models, caches, `node_modules`, env files.
6. Verify confidence/priority disclaimers and demo markers are visible; record incomplete features accurately.
7. Confirm README, dashboard, and demo use the same measured metrics and limitations.

**Exit check:** full end-to-end workflow runs from documented commands; every B-owned feature is wired; incomplete items have safe fallbacks.

---

## 7. Verification checklist (Person B)

- [ ] BANKING77 source/config documented; preparation repeatable; raw untouched.
- [ ] Official train/test kept separate; text and original labels preserved; schema per §4.1.
- [ ] Nulls/empties/duplicates/label counts/split sizes checked and reported; Person A confirmed load.
- [ ] Backend starts via `uvicorn backend.app:app`; `/api/health` reflects real model/DB state; `/docs` renders.
- [ ] Invalid JSON, blank, too-long, unknown-model requests return the §4.4 error envelope.
- [ ] Analyze calls Person A's functions once and persists after success only.
- [ ] Model failures never yield fake labels/confidence (no mock in production mode).
- [ ] Parameterized SQL; idempotent DB init; reset documented.
- [ ] List/analytics endpoints work on empty and populated DB; `similar_cases` not fabricated.
- [ ] Demo rows marked `source="demo"` and visibly labelled; analytics states `includes_demo`.
- [ ] React shows pending/success/no-data/validation/server-error states; preserves text on failure.
- [ ] Confidence labelled model confidence; priority labelled rule suggestion; summary unavailable explicit.
- [ ] Successful submission appears in history/dashboard without reload.
- [ ] CORS/API base URL fixed; documented start commands for both servers.
- [ ] Root `requirements.txt` installs both dependency sets; no secrets committed.
- [ ] README app sections complete and consistent with Person A's metrics.

---

## 8. Time-box and fallback order

1. BANKING77 data package + manifest (unblocks Person A).
2. FastAPI + SQLite + `/api/complaints/analyze` with mocked Person A functions.
3. React submission + result view.
4. Persistence/history + analytics endpoint.
5. Dashboard charts + demo labelling.
6. Similarity UI, summary UI, visual polish.

If Person A's similarity is not ready: return `similar_cases: []` with an explicit not-yet-available note in the UI, not fabricated matches. If the summariser is unavailable: render the unavailable state, never invent text. If time is tight: deliver submit → result → persistence → dashboard first.

---

## 9. Handoff acceptance from Person A

- [ ] `data/processed/` package delivered and confirmed by Person A.
- [ ] Person A's `backend/nlp/` modules importable when served via `uvicorn backend.app:app`.
- [ ] `backend/models/` artifacts present; `health()` reports availability correctly.
- [ ] `backend/reports/` metrics available to copy into README/dashboard narrative.
- [ ] Shared constants in `backend/nlp/config.py` unchanged or updated in both plans.
- [ ] End-to-end walkthrough signed off; limitations documented.
