# BankSense

Intelligent NLP-based banking complaint analysis and triage prototype.

BankSense accepts a banking complaint, predicts its intent, suggests a priority
using explicit rules, retrieves semantically similar stored complaints, offers an
optional summary, and shows complaint patterns on a dashboard. It is a
decision-support prototype, not an autonomous complaint-resolution or banking
transaction system.

## Project status

The application layer (Person B) is implemented: dataset preparation, FastAPI
service, SQLite persistence, React interface, and analytics dashboard. The NLP
layer (Person A) is pending: model training, artifacts, `predict`,
`suggest_priority`, `rank_similar`, and `summarize`. Until those artifacts exist,
`POST /api/complaints/analyze` returns a clear `503 MODEL_UNAVAILABLE` error;
health, dataset, persistence, and dashboard endpoints already work.

The NLP model and evaluation sections at the end of this README are completed by
Person A after training.

## Stack

- Backend: Python, FastAPI, Uvicorn, Pydantic, SQLite (`sqlite3`)
- Frontend: React + Vite, Plotly (basic bundle)
- Data: BANKING77 (PolyAI), prepared with the standard library only
- Tests: pytest + FastAPI `TestClient` (NLP functions mocked)

## Repository layout

```text
data/
  raw/                     # immutable BANKING77 downloads (git-ignored)
  processed/
    train.csv              # example_id,text,normalized_text,label
    test.csv               # official test partition, untouched until final eval
    dataset_manifest.md    # provenance, checksums, validation results
    prepare_banking77.py   # reproducible preparation script
backend/
  app.py                   # FastAPI app, CORS, exception handlers
  config.py                # DB path, CORS origins, list limits
  schemas.py               # Pydantic request/response models
  routes/                  # health, complaints, analytics routers
  services/                # orchestration; only caller of Person A's functions
  db/                      # connection, schema.sql, repository
  nlp/                     # Person A: config constants, models, inference
  models/                  # Person A artifacts (git-ignored)
  reports/                 # Person A evaluation artifacts
  tests/                   # API/database tests
frontend/
  src/api/                 # single fetch layer for the API
  src/components/          # form, result, chart, dashboard, history
  src/pages/ (inline)      # views composed in App.jsx
scripts/
  seed_demo.py             # optional, clearly labelled demo rows
```

## Dataset

BANKING77 is downloaded from the PolyAI-LDN `task-specific-datasets` repository
(the upstream source behind the Hugging Face dataset) into `data/raw/`, then
exported to the official split:

- `data/processed/train.csv`: 10,003 rows, 77 labels
- `data/processed/test.csv`: 3,080 rows, 77 labels
- schema: `example_id,text,normalized_text,label`
- only whitespace is normalized (`normalized_text`); original `text` is unchanged
- duplicates are reported, not deleted
- the official test partition must stay untouched until final evaluation

Provenance, SHA-256 checksums, duplicate counts, label parity, and cleaning steps
are recorded in [`data/processed/dataset_manifest.md`](data/processed/dataset_manifest.md).

Regenerate:

```bash
python data/processed/prepare_banking77.py --force-download
```

## Backend setup

Python 3.10+ is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

App layer only (no model training):

```bash
pip install -r backend/requirements.txt
```

The full `requirements.txt` also pulls `sentence-transformers`/PyTorch for Person
A's models; use a Python 3.10-3.12 interpreter for that path if your environment
does not yet provide wheels for newer Python versions.

Run from the repository root so absolute `backend.*` imports resolve:

```bash
uvicorn backend.app:app --reload --port 8000
```

- OpenAPI docs: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/api/health>

The SQLite database defaults to `data/banksense.db` and is created on startup.
Reset it by deleting that file and restarting.

### Configuration

| variable | default | purpose |
|---|---|---|
| `BANKSENSE_DB_PATH` | `data/banksense.db` | SQLite file location |
| `BANKSENSE_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | allowed frontend origins |
| `BANKSENSE_MODELS_DIR` | `backend/models` | Person A artifacts |
| `BANKSENSE_REPORTS_DIR` | `backend/reports` | Person A reports |
| `VITE_API_BASE_URL` | empty (Vite proxy) | frontend API origin |

## API reference

Error responses always use:

```json
{"error": {"code": "VALIDATION_ERROR", "message": "...", "field": "text"}}
```

Codes: `VALIDATION_ERROR`, `UNKNOWN_MODEL`, `MODEL_UNAVAILABLE`,
`INFERENCE_ERROR`, `NOT_FOUND`.

### `POST /api/complaints/analyze`

```bash
curl -sS http://127.0.0.1:8000/api/complaints/analyze \
  -H 'Content-Type: application/json' \
  -d '{"text": "I was charged twice for the same purchase.", "model": "tfidf"}'
```

```json
{
  "complaint_id": 1,
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

`model` is optional and defaults to `tfidf`. `text` is trimmed, must be non-empty,
and is limited to 2,000 characters. `confidence` is model confidence, not a
calibrated real-world probability. `similar_cases` are derived at request time
and are not persisted.

### Other endpoints

- `GET /api/complaints?limit=20&offset=0` → `{"items": [...], "count": n}`
- `GET /api/analytics` → totals, intent counts, priority counts, top intents,
  `includes_demo`
- `GET /api/health` → service, model, summary, and database readiness

## Frontend setup

Node 18+ is required.

```bash
cd frontend
npm install
npm run dev
```

Open <http://127.0.0.1:5173>. The Vite dev server proxies `/api` to
`http://127.0.0.1:8000`; set `VITE_API_BASE_URL` to call a different origin.

Production build:

```bash
cd frontend
npm run build
```

## Tests

```bash
python -m pytest backend/tests -q
```

Tests use a temporary SQLite database and mock Person A's NLP functions, so they
run before model artifacts exist. They cover the response contract, validation
errors, 503 model-unavailable behaviour, persistence, empty/populated analytics,
health, and 404 error envelopes.

## Demo data

Optional, clearly labelled demonstration rows:

```bash
python scripts/seed_demo.py
```

These are hand-authored examples stored with `source="demo"` and shown as demo
records in the UI. They are not model predictions and not verified bank complaint
history.

## Limitations

- BANKING77 is a labelled intent benchmark, not real bank complaint history.
- Priority is a configurable rule suggestion, not a fraud or risk score.
- Model confidence is not a calibrated probability of a real-world outcome.
- The prototype does not connect to banking, payment, or identity systems.
- Analytics describe only rows stored by this prototype; they do not represent
  real complaint volumes, SLAs, or operational outcomes.
- The demo build is an MVP, not a production system.

## NLP and evaluation (Person A)

To be completed after training:

- chosen Sentence-BERT model and TF-IDF configuration
- measured accuracy, macro-F1, weighted-F1, per-class precision/recall/F1, and
  confusion matrices on the untouched official test split
- artifact locations and regeneration commands (`backend/models/`,
  `backend/reports/`)
- observed inference latency and any resource constraints
- whether summarisation is enabled or explicitly unavailable
