# Person B — Backend, Data, Frontend, and Integration Plan

## Mission

Build the application around Person A's NLP components: Flask API, SQLite persistence, React complaint workflow, and analytics dashboard. Person B owns request/response behavior, database lifecycle, frontend integration, and application-level validation. Person A owns model training and NLP logic.

The proposal describes a two-day MVP. Get complaint submission and a visible result working first, then add storage, similar cases, and dashboard views. Summarisation and visual polish are stretch work after the core path works.

## Outcomes and deliverables

- Acquired and validated BANKING77 data, with a reproducible preparation script and a clearly documented handoff package for Person A.
- Flask application with documented endpoints and input validation.
- SQLite schema and persistence for submitted complaints and their analysis outputs.
- React page for submitting a message and displaying intent, confidence, suggested priority/reason, similar cases, and optional summary state.
- Dashboard with complaint count, intent distribution, priority breakdown, and common issues based only on records actually stored by this prototype.
- Clear loading, empty, and error states; no fabricated prediction or analytics data.
- Setup instructions, environment configuration, and end-to-end handoff notes.

## Ownership boundaries

Person B owns:

- Flask API, validation, orchestration, database access, React interface, dashboard, and application setup.
- Dataset acquisition and general-purpose cleaning/validation, preserving the official train/test split and handing Person A stable, labeled files for model work.
- Calling Person A's stable Python interface and mapping its results to the HTTP response.
- Any seed/demo rows used to show the workflow; label these as demo data and make them distinguishable from user-submitted records.

Person A owns:

- Model-specific text transformations, training/validation choices, evaluation, model artifacts, intent inference, embeddings/retrieval calculations, priority rule definitions, and summary generation.

Both people own agreement on the data handoff and API contract, integration, end-to-end walkthrough, and accurate completion/limitation reporting. Person B prepares clean, split-preserving data; Person A decides transformations needed by each model. Person B should not reimplement the classifier in JavaScript or duplicate model logic in Flask routes.

## Suggested application structure

Adapt to the existing repository after inspection; do not create parallel structures if equivalents already exist.

```text
data/
  raw/                    # downloaded source; do not edit by hand
  processed/
    train.csv
    test.csv
    dataset_manifest.md
backend/
  app.py
  routes/
    complaints.py
    analytics.py
  services/
    complaint_service.py
  db/
    connection.py
    schema.sql
  requirements.txt
frontend/
  src/
    api/
    components/
    pages/
```

Keep database and model paths configurable. Store the SQLite database in a documented local data directory and avoid committing generated user data.

## Detailed implementation sequence

### Phase 0 — Agree on contract and inspect the repo (first 30–45 minutes)

1. Inspect existing source, package files, framework versions, and run commands before adding a scaffold.
2. Agree with Person A on the predictor, similarity, priority, and optional summary interface. Request a working mock result while model artifacts are still being built.
3. Freeze the HTTP response shape and model selection option, then share it with the frontend so the UI can be built against the contract.
4. Decide allowed priority values, how unavailable summary is represented, and whether the results page includes top alternatives.
5. Identify environment variables needed for API URL, database path, and optional model/API configuration; do not commit secrets.

**Exit check:** frontend can be built against a written response example, backend knows the exact NLP import names or temporary adapter boundary, and both people agree on the dataset columns and split handoff.

### Phase 1 — Acquire and prepare BANKING77 for Person A (Day 1, first half)

Person B prepares the source data; Person A owns any model-specific tokenization, vectorization, embedding preparation, and training-time transformations.

1. Download BANKING77 from the documented PolyAI source (or its Hugging Face dataset page) using a repeatable script or documented command. Record the source, access date, dataset configuration/version if available, and any license/use notes in a manifest.
2. Keep the raw downloaded source unchanged under `data/raw/`. Do not edit the original files manually.
3. Export the official training and test partitions separately to `data/processed/train.csv` and `data/processed/test.csv`. Preserve the official split; do not shuffle rows across partitions or combine them into a single unlabeled file.
4. Normalize the handoff schema to stable columns such as `example_id`, `text`, and `label`. Keep the original text unchanged in `text`; if whitespace normalization is useful, put it in a separate `normalized_text` column so Person A can choose which version to model.
5. Apply only conservative cleaning: trim leading/trailing whitespace and normalize repeated whitespace in `normalized_text`; retain punctuation, casing, contractions, and wording in the original column. Do not remove stop words, stem/lemmatize, or perform TF-IDF/Sentence-BERT transformations here.
6. Validate required columns, null/empty values, row counts, unique label counts, and train/test label consistency. Expected benchmark counts are 10,003 train and 3,080 test examples across 77 labels; if the downloaded dataset differs, investigate and document the actual configuration rather than silently forcing these counts.
7. Check and report duplicate texts and class distribution, but do not silently delete rows. Preserve labels exactly as supplied by BANKING77 and make row IDs deterministic within each official split.
8. Write a short manifest with source/configuration, filenames, schema, split sizes, number of labels, cleaning steps, validation results, and a note that the test set must remain untouched until final evaluation.
9. Give Person A the processed file paths and a tiny loading example. Ask Person A to confirm that the package loads correctly before proceeding with model training.

**Handoff schema example:**

```csv
example_id,text,normalized_text,label
train-000001,"Original BANKING77 text...","Original BANKING77 text...",cash_withdrawal
```

The example row above is illustrative. `example_id` should identify the split and row, while `label` remains the original intent string. Person A creates a validation split from the training partition if needed and fits all learned transforms using training data only. The official test partition is reserved for final comparison.

**Exit check:** Person A can load both processed files, sees the expected labels and split identifiers, and has enough provenance to reproduce the dataset preparation without manual spreadsheet edits.

### Phase 2 — Flask foundation and SQLite schema (Day 1, first half, in parallel)

1. Create the Flask app and separate route, service, and persistence responsibilities enough to keep handlers small.
2. Add a health endpoint that reports application readiness without exposing secrets or falsely claiming that missing NLP artifacts are loaded.
3. Create database initialization that is safe to run repeatedly and document how to reset local development data.
4. Define a `complaints` table with at least: stable ID, original text, predicted intent, confidence, model name, priority, priority reason, optional summary, source/type marker for demo vs submitted data, and created timestamp.
5. Add a clear schema for related cases if needed; otherwise use complaint IDs as similarity references and query the existing table. Keep schema as small as the MVP allows.
6. Use parameterized SQL and validate user input before storing it. Set a reasonable maximum text length and reject blank messages.
7. Provide a small repository/database layer so routes do not contain ad hoc SQL.

**Exit check:** app starts, database initializes, and a complaint row can be inserted/read using a local development path.

### Phase 3 — Complaint analysis API (Day 1, second half)

Implement and document the core endpoints. Exact paths may follow existing conventions.

**`POST /api/complaints/analyze`**

1. Accept JSON containing a non-empty `text`; optionally accept a supported model name.
2. Return a 400 response for malformed JSON, blank text, excessive length, or unsupported options.
3. Call Person A's classifier once, then priority and similarity components. Do not repeat inference for the same request.
4. Persist the submitted text and returned outputs only after successful analysis, or define/document a deliberate failure policy.
5. Return a stable JSON result containing complaint ID, intent, confidence, model, priority, reason, similar cases, and summary or an explicit unavailable/null status.
6. Return a useful 503/500 error if the model is missing or inference fails; do not return a plausible-looking mock prediction in production mode.

**`GET /api/complaints`**

1. Return recent persisted records with pagination or a simple bounded limit.
2. Include source markers so demo examples can be identified.
3. Do not expose more text or fields than the prototype needs.

**`GET /api/analytics`**

1. Aggregate stored complaint count, intent counts, priority counts, and most common intents from SQLite.
2. State or expose whether demo records are included; use one consistent rule across cards and charts.
3. Return empty arrays/zeroes for a new database instead of chart errors.

**Exit check:** curl or equivalent can submit a query, receive structured analysis, and retrieve the persisted record and analytics.

### Phase 4 — React submission and result flow (Day 2, first half)

1. Create a compact complaint form with text area, character limit, submit state, and clear validation feedback.
2. Connect to Flask using one frontend API module rather than scattering fetch calls across components.
3. Show progress while analysis is running and prevent accidental duplicate submissions while the request is pending.
4. Render intent, model confidence, model name, priority, and the rule reason returned by the API. Label confidence as model confidence.
5. Render similar cases with their similarity scores and clearly label benchmark/demo examples when relevant.
6. Show the summary only when one is actually returned; make unavailable status clear without blocking other results.
7. Show backend errors in actionable plain language and preserve entered text when a request fails.
8. Keep the first workflow linear: submit → inspect result → optionally view related cases. Avoid adding navigation/features outside the proposal before the core flow is stable.

**Exit check:** a user can submit a query in the browser and see the API response without manually refreshing the page.

### Phase 5 — Dashboard and history (Day 2, second half)

1. Build summary cards for total analyzed complaints and priority counts.
2. Add intent distribution and priority breakdown charts from `/api/analytics` response data.
3. Add a concise recent complaints/history list, if time allows, using persisted records.
4. Include useful loading, no-data, and API-error states. Do not ship hard-coded charts as if they came from analysis records.
5. Mark sample/demo records clearly in the dashboard and provide a simple way to distinguish them from user-submitted records.
6. Ensure charts remain readable at the demo viewport and do not obscure the complaint submission flow.

**Exit check:** dashboard values reconcile with the SQLite rows and update after a successful submission.

### Phase 6 — Integration, documentation, and demonstration

1. Integrate Person A's actual module and artifacts. Verify startup behavior when artifacts are present and a clear failure state when they are missing.
2. Walk the full path together: submit text → classify → suggest priority → retrieve related cases → save → render → update analytics.
3. Fix cross-origin/API URL configuration for local development and document exact startup commands for both servers.
4. Document dependencies, Python/Node versions, database creation/reset, dataset/model setup prerequisites, and known optional features.
5. Confirm demo data labeling and ensure screenshots/demo script do not represent sample records as real bank cases.
6. Record any incomplete feature accurately and ensure the UI reports it explicitly.

## API contract to agree with Person A

Illustrative successful response (values are placeholders, not real model output):

```json
{
  "complaint_id": "stable-record-id",
  "intent": "cash_withdrawal",
  "confidence": 0.82,
  "model": "tfidf",
  "priority": "medium",
  "priority_reason": "Rule matched: ...",
  "similar_cases": [],
  "summary": null
}
```

Suggested request:

```json
{
  "text": "I was charged twice for the same purchase.",
  "model": "tfidf"
}
```

Agree exact field names, null/unavailable behavior, error envelope, and similarity case fields with Person A before building UI assumptions into multiple components.

## Database and data rules

- BANKING77 is a labelled intent benchmark, not verified internal complaint history.
- Keep raw source files immutable and processed train/test files separate. Include a preparation script and manifest so Person A can reproduce the handoff.
- General cleaning must preserve meaning and original text. Person A owns the model-specific preprocessing and must fit learned transformations only on training data.
- Never use the official test partition to fit a vocabulary, tune hyperparameters, make a validation split, or choose a model. Use it only for final evaluation after choices are fixed.
- Do not silently drop duplicate examples or alter the dataset labels; record quality checks and any exclusions in the manifest.
- If benchmark rows or hand-authored examples are inserted for the demo, keep a `source` or `is_demo` marker and show that marker in the UI.
- Analytics must describe the rows actually counted and must not imply real bank volumes or operational outcomes.
- Store timestamps consistently (UTC in storage is a good default) and format them for the user in the UI.
- Do not store credentials, payment data, or sensitive identifiers; the proposal does not require banking-system integration.

## Validation checklist

- [ ] BANKING77 source/configuration and preparation steps are documented and repeatable.
- [ ] Official train and test partitions remain separate with text and original intent labels preserved.
- [ ] Null/empty rows, label counts, split sizes, and duplicate texts are checked and reported.
- [ ] Person A confirms that processed files load and can be used for training without manual edits.
- [ ] Flask starts from documented commands and health status accurately reflects readiness.
- [ ] Invalid, blank, too-long, and malformed requests return clear client errors.
- [ ] Valid analysis calls NLP functions once and stores returned values with the complaint.
- [ ] Model/service failures do not yield fake labels or confidence scores.
- [ ] Database access uses parameterized queries and repeatable initialization.
- [ ] List and analytics endpoints work with an empty database and populated records.
- [ ] Demo/benchmark records are distinguishable from submitted complaints.
- [ ] React shows pending, success, no-data, validation, and server-error states.
- [ ] Confidence is labeled as model confidence; priority is labeled as a rule suggestion.
- [ ] A successful submission appears in history/dashboard counts without a page reload.
- [ ] Setup and reset steps are documented, with no secrets committed.

## Time-box and fallback order

1. Acquire and validate BANKING77; deliver split-preserving files to Person A.
2. Flask app + SQLite + complaint analysis endpoint.
3. React submission and analysis result view.
4. Persistence/history and analytics endpoint.
5. Dashboard charts and demo data labels.
6. Summarization UI and visual polish.

If time is tight, deliver the complaint submit → result → persistence path first. Similarity can return an empty list with an explicit not-yet-available state if Person A has not finished its index. Keep the dashboard simple and data-backed; never substitute invented counts or predictions.
