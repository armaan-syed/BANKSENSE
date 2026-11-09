# BankSense

Intelligent NLP-based banking complaint analysis and triage prototype.

BankSense accepts a banking complaint, predicts its intent, suggests a priority
using explicit rules, retrieves semantically similar stored complaints, offers an
optional summary, and shows complaint patterns on a dashboard. It is a
decision-support prototype, not an autonomous complaint-resolution or banking
transaction system.

> **Hosting handoff:** see [HANDOFF.md](HANDOFF.md). This branch is trimmed for
> deployment. Development test suites and local planning notes are intentionally
> excluded; model artifacts are supplied separately in `model.zip`.

## Project status

Both layers are implemented. Person B delivered dataset preparation, the FastAPI
service, SQLite persistence, the React interface, and the analytics dashboard.
Person A delivered data validation, both trained classifiers, evaluation
reports, `predict`/`predict_top_k`/`health`, rule-based priority, semantic
similarity, and an optional summariser.

`POST /api/complaints/analyze` works end to end when the artifacts in
`backend/models/` exist. If they are missing (for example on a fresh clone before
training), it returns a clear `503 MODEL_UNAVAILABLE` error instead of guessing.

## Stack

- Backend: Python, FastAPI, Uvicorn, Pydantic, Supabase Postgres/Data API
- Auth: Supabase Auth, Google OAuth, per-user row-level security (RLS)
- Local/test persistence: SQLite (`sqlite3`)
- NLP: scikit-learn (TF-IDF + Logistic Regression), Sentence-BERT
  (`all-MiniLM-L6-v2`) + Logistic Regression, optional DistilBART summariser
- Frontend: React + Vite, Plotly (basic bundle), `@supabase/supabase-js`
- Data: BANKING77 (PolyAI), prepared with the standard library only

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
  auth.py                  # Supabase JWT verification (JWKS)
  config.py                # DB backend, Supabase, CORS, list limits
  env.py                   # root .env loader
  schemas.py               # Pydantic request/response models
  routes/                  # health, complaints, analytics routers
  services/                # orchestration; only caller of Person A's functions
  db/                      # connection, schemas, SQLite + Supabase repositories
  nlp/                     # Person A: config constants, models, inference
  models/                  # Person A artifacts (git-ignored)
  reports/                 # Person A evaluation artifacts
frontend/
  src/api/                 # single fetch layer for the API
  src/lib/supabase.js      # browser Supabase client
  src/components/          # form, result, chart, dashboard, auth screen
  src/pages/ (inline)      # views composed in App.jsx
scripts/
  seed_demo.py             # optional, clearly labelled demo rows
```

## Architecture

```text
React UI (Vite)
  -> Supabase Auth (Google OAuth)
  -> frontend/src/api/client.js (Bearer access token)
  -> FastAPI routes (backend/routes)
  -> JWT verification via Supabase JWKS (backend/auth.py)
  -> complaint_service (validation + orchestration)
       -> Person A NLP: predict -> suggest_priority -> rank_similar -> summarize
       -> Supabase Data API with the user's JWT (RLS) or SQLite in local mode
  -> JSON response -> UI result + dashboard
```

Request flow for `POST /api/complaints/analyze`:

1. FastAPI validates the Supabase access token and extracts the user id.
2. Pydantic parses the request and the service validates `text`, length, and `model`.
3. `predict` returns the intent and model confidence.
4. `suggest_priority` returns a rule-based priority and reason.
5. Stored rows are passed to `rank_similar` for cosine-ranked similar cases.
6. `summarize` is called only when the summariser reports `enabled`.
7. The record is persisted under the signed-in user and the response is returned.

Supabase RLS policies enforce `auth.uid() = user_id`; the backend never uses a
service-role key for normal complaint operations.

Person A's functions are imported lazily through one adapter in
`complaint_service`; Person B never loads model artifacts directly and never
duplicates inference logic.

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

The full `requirements.txt` also installs PyTorch for Person A's models. On CPU
hosts, install the smaller CPU wheel first, then the rest:

```bash
pip install --index-url https://download.pytorch.org/whl/cpu torch
pip install -r requirements.txt
```

The SBERT encoder model (`sentence-transformers/all-MiniLM-L6-v2`, ~90 MB) is
downloaded on first use and cached by Hugging Face. Override it with
`BANKSENSE_SBERT_MODEL`. The optional summariser
(`sshleifer/distilbart-cnn-12-6`, ~1.2 GB) is downloaded only when a complaint
longer than 30 words is summarised; override it with `BANKSENSE_SUMMARY_MODEL`.

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
| `BANKSENSE_DB_BACKEND` | auto: `supabase` when configured, else `sqlite` | persistence backend |
| `BANKSENSE_DB_PATH` | `data/banksense.db` | SQLite file location |
| `SUPABASE_URL` | empty | Supabase project URL |
| `SUPABASE_PUBLISHABLE_KEY` | empty | Supabase publishable/anon key |
| `SUPABASE_SECRET_KEY` | empty | optional admin key; not used for user requests |
| `SUPABASE_JWT_SECRET` | empty | optional legacy HS256 project JWT secret |
| `VITE_SUPABASE_URL` | falls back to `SUPABASE_URL` | optional browser override |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | falls back to `SUPABASE_PUBLISHABLE_KEY` | optional browser override |
| `BANKSENSE_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | allowed frontend origins |
| `BANKSENSE_MODELS_DIR` | `backend/models` | Person A artifacts |
| `BANKSENSE_REPORTS_DIR` | `backend/reports` | Person A reports |
| `BANKSENSE_SBERT_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | SBERT encoder |
| `BANKSENSE_SUMMARY_MODEL` | `sshleifer/distilbart-cnn-12-6` | optional summariser |
| `VITE_API_BASE_URL` | empty (Vite proxy) | frontend API origin |

Configuration is read from the repository-root `.env`. Copy `.env.example` to
`.env` and fill in the Supabase values. `.env` is git-ignored.

### Supabase setup

1. Create a Supabase project and run `backend/db/supabase_schema.sql` in the SQL
   editor. It creates `public.allowed_users`, `public.complaints`, indexes,
   grants, and RLS policies. If the project's Data API settings require explicit
   table exposure, add both tables there.
2. In **Authentication → Providers**, enable Google and add the Google OAuth
   client ID/secret. Add
   `https://<project-ref>.supabase.co/auth/v1/callback` as the authorized Google
   redirect URI.
3. In **Authentication → URL Configuration**, set the Site URL to
   `http://localhost:5173` for local development and add
   `http://localhost:5173/**`, `http://127.0.0.1:5173/**`, and the production
   Vercel URL to the redirect allowlist.
4. For invite-only access, keep Google sign-in enabled and add each allowed
   Google email to `public.allowed_users`. Uninvited accounts can authenticate
   but are rejected by the API and by the complaint RLS policies.
5. Fill the root `.env` with `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY`.
   Leave `BANKSENSE_DB_BACKEND` blank to auto-select Supabase, or set it
   explicitly. The `VITE_` variables are optional browser overrides; Vite falls
   back to the backend values.
6. Restart both servers. The API will verify Supabase access tokens via the
   project JWKS endpoint (new projects sign with ES256).

The optional `SUPABASE_SECRET_KEY` is not required for the app and is never used
for user complaint requests; RLS is always evaluated with the user's token.

## API reference

Error responses always use:

```json
{"error": {"code": "VALIDATION_ERROR", "message": "...", "field": "text"}}
```

Codes: `VALIDATION_ERROR`, `UNKNOWN_MODEL`, `MODEL_UNAVAILABLE`,
`INFERENCE_ERROR`, `NOT_FOUND`, `HTTP_ERROR`, `UNAUTHORIZED`,
`AUTH_UNAVAILABLE`, `NOT_INVITED`.
Complaint and analytics endpoints require
`Authorization: Bearer <supabase-access-token>` when the Supabase backend is
active. `/api/health` is public.

### `POST /api/complaints/analyze`

```bash
curl -sS http://127.0.0.1:8000/api/complaints/analyze \
  -H 'Authorization: Bearer <supabase-access-token>' \
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
- `GET /api/health` → service, model, summary, database readiness, and whether
  auth is `required` or `disabled`

## Frontend setup

Node 18+ is required.

```bash
cd frontend
npm install
npm run dev
```

Open <http://127.0.0.1:5173>. The Vite dev server proxies `/api` to
`http://127.0.0.1:8000`; set `VITE_API_BASE_URL` to call a different origin.
When Supabase is configured, the UI shows a Google sign-in screen and sends the
Supabase access token with each API request. The Vite config reads the root
`.env` file.

Production build:

```bash
cd frontend
npm run build
```

## Training and evaluation

Train both classifiers and write the artifacts to `backend/models/`:

```bash
python -m backend.nlp.train --model all
```

Train a single pipeline with `--model tfidf` or `--model sbert`. Training uses a
90/10 stratified validation split carved out of `train.csv` for a tiny
hyper-parameter search (`random_state=42`); `test.csv` is never touched.

Evaluate both artifacts once on the official test split:

```bash
python -m backend.nlp.evaluate
```

This writes `model_comparison.json`, per-class classification reports, raw-count
confusion matrices, and `evaluation_manifest.md` to `backend/reports/`.

The SBERT training embeddings are cached in `backend/models/embedding_cache/`
(git-ignored) and keyed by model name plus text content.

## Tests

Development test suites are not included in this hosting handoff branch. They
are not required to deploy or run the application; use the acceptance checklist
in [`HANDOFF.md`](HANDOFF.md) instead.

## Demo data

Optional, clearly labelled demonstration rows:

```bash
python -m scripts.seed_demo
```

These are hand-authored examples stored with `source="demo"` and shown as demo
records in the UI. They are not model predictions and not verified bank complaint
history. The seed script targets the local SQLite database; it does not seed
Supabase.

## Limitations

- BANKING77 is a labelled intent benchmark, not real bank complaint history.
- Priority is a configurable rule suggestion, not a fraud or risk score.
- Model confidence is not a calibrated probability of a real-world outcome.
- The prototype does not connect to banking, payment, or identity systems.
- Analytics describe only rows stored by this prototype; they do not represent
  real complaint volumes, SLAs, or operational outcomes.
- The demo build is an MVP, not a production system.

## NLP and evaluation (Person A)

### Models

- **TF-IDF + Logistic Regression**: `TfidfVectorizer(ngram_range=(1,2),
  min_df=1, max_df=0.9, sublinear_tf=True, strip_accents="unicode")` with
  `LogisticRegression(C=2.0, max_iter=2000, solver="lbfgs")`.
- **Sentence-BERT + Logistic Regression**: `all-MiniLM-L6-v2` embeddings
  (L2-normalised, 384 dimensions) with `LogisticRegression(C=10.0)`.
- Both models use the same `normalized_text` field and the same label ordering
  from `backend/models/label_classes.json`.
- `confidence` is raw `predict_proba` output, not a calibrated probability.

### Measured results (untouched official test split)

| Model | Accuracy | Macro-F1 | Weighted-F1 | Inference ms/example (CPU) |
|---|---:|---:|---:|---:|
| TF-IDF + LogReg | 0.8779 | 0.8781 | 0.8781 | 0.017 |
| SBERT + LogReg | 0.9295 | 0.9294 | 0.9294 | 3.615 |

- Evaluation row count: 3,080; labels: 77; seed: 42.
- The validation split (1,001 rows) came only from `train.csv`; the test split
  was evaluated once, after model choices were frozen.
- Full per-class precision/recall/F1 and raw confusion matrices are in
  `backend/reports/`. The measured comparison is the only source for model
  claims; no superiority is implied beyond these numbers.
- Environment for the reported run: Python 3.14.7, scikit-learn 1.9.1,
  torch 2.15.0+cpu, sentence-transformers 6.2.0 (CPU-only).

### Artifacts and interface

`backend/models/` (git-ignored, regenerate with the training command):

- `tfidf_logreg.joblib`, `sbert_logreg.joblib`
- `label_classes.json`, `sbert_model_name.txt`, `training_metadata.json`
- `embedding_cache/` (training embeddings)

`backend/reports/` (committed):

- `data_validation.json`, `model_comparison.json`, `evaluation_manifest.md`
- `classification_report_{tfidf,sbert}.csv`
- `confusion_matrix_{tfidf,sbert}.csv`

Interface used by the API:

```python
from backend.nlp.predictor import predict, predict_top_k, health
from backend.nlp.priority import suggest_priority
from backend.nlp.similarity import rank_similar
from backend.nlp.summarizer import summarize, summary_status
```

```python
predict("I was charged twice for the same purchase.", "sbert")
# {"intent": "transaction_charged_twice", "confidence": 0.9949, "model": "sbert"}

suggest_priority("I was charged twice.", "transaction_charged_twice")
# {"priority": "high", "priority_reason": "Rule matched: ...", "rule_id": "duplicate_charge"}
```

The summariser returns a verbatim result for complaints of 30 words or fewer and
an abstractive result for longer text. If the optional stack or model is
unavailable it returns `{"status": "unavailable", ...}`; submission still
succeeds. The first abstractive call downloads the model, and CPU generation
takes a few seconds; short complaints avoid that cost. `GET /api/health` reports
whether summarisation is enabled or explicitly unavailable.
