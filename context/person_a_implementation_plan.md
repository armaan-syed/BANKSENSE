# Person A — NLP and ML Implementation Plan

## Mission

Build and hand off the reproducible NLP components for BankSense: intent classification, measured model comparison, semantic similarity, rule-assisted priority, and (if time allows) complaint summaries. Person A owns model code, training/evaluation artifacts, and the service-facing Python interface. Person B owns the Flask/SQLite application, React UI, and dashboard.

The proposal describes a two-day MVP. Prioritize a working classifier and end-to-end handoff first; similarity comes next. Summarisation and model-comparison polish are stretch work if the core path is not complete.

## Outcomes and deliverables

- A reproducible training workflow that consumes Person B's documented, split-preserving BANKING77 data package.
- TF-IDF + Logistic Regression and Sentence-BERT embeddings + Logistic Regression classifiers, trained and evaluated on the same official split.
- Saved model artifacts and a small Python inference interface that Person B can call without knowing model internals.
- Evaluation results including accuracy, macro-F1, weighted-F1, per-class precision/recall/F1, and confusion-matrix data.
- A semantic retrieval component over the stored complaint examples available to the application.
- Explicit, documented priority rules; these are triage suggestions, not a fraud/risk score.
- Optional concise summary function, with a documented fallback or unavailable status if a pretrained summarizer/API cannot be used in the time available.
- Setup notes, artifact locations, limitations, and a handoff checklist for Person B.

## Ownership boundaries

Person A owns:

- Loading and validating Person B's prepared dataset package; model-specific preprocessing, validation split creation, test-set discipline, training, evaluation, and saved model artifacts.
- NLP inference functions for intent, confidence, and top alternatives if exposed.
- Text embedding and similarity ranking logic.
- Priority rule definitions and summary-generation logic.

Person B owns:

- Acquiring BANKING77, preserving its official train/test partitions, performing conservative general-purpose cleaning and quality checks, and handing over labeled files plus a dataset manifest.
- Flask routes and request validation, orchestration, persistence, frontend, dashboard, and application-level error responses.
- Calling Person A's stable Python interface from the backend and rendering the returned data.

Both people own confirming that the data handoff is usable, the API contract, integration walkthrough, end-to-end validation, and final limitations/demo notes. Person A should not reacquire or manually alter the source dataset, and should not create a separate web server or database.

## Suggested module and artifact layout

Adapt to the repository once implementation starts; avoid duplicating an existing structure.

```text
data/
  processed/              # prepared by Person B
    train.csv
    test.csv
    dataset_manifest.md
backend/
  nlp/
    data.py
    train.py
    evaluate.py
    predictor.py
    similarity.py
    priority.py
    summarizer.py          # optional
  models/
    tfidf_logreg.joblib
    sbert_logreg.joblib
    label_encoder.json     # only if needed by the chosen implementation
  reports/
    model_comparison.json
    confusion_matrix_*.csv # or another documented machine-readable format
```

Keep large artifacts out of source control if repository policy or size makes that impractical. Document how to regenerate them and where the application expects them.

## Detailed implementation sequence

### Phase 0 — Agree on contract and inspect the repo (first 30–45 minutes)

1. Check the existing repository, Python version, dependency manager, and any established naming or configuration patterns before creating files.
2. Agree with Person B on the prepared data location and schema (`example_id`, original `text`, optional `normalized_text`, and original `label`) as well as the callable interface and response fields below.
3. Ask Person B to provide the separate official train/test files and dataset manifest. Confirm the source/configuration and agree that no rows move between the partitions.
4. Create a minimal dependency list for the NLP side, pinning versions where feasible. Avoid adding a heavyweight summarization dependency to the required path.

**Exit check:** Person B can import the planned predictor module and knows the artifact-loading path and output schema; Person A knows where the prepared train/test files and manifest will be delivered.

### Phase 1 — Dataset and baseline classifier (Day 1, first half)

1. Load Person B's `data/processed/train.csv` and `test.csv`, and read `dataset_manifest.md`. Confirm the official partition identity, required columns, label strings, and row counts (proposal expectation: 10,003 train and 3,080 test across 77 labels; investigate and record any source/configuration difference).
2. Validate the handoff: inspect missing/empty text, duplicate counts, per-label distribution, and that train/test contain the expected label set. Report issues to Person B; do not silently change labels or remove duplicate rows.
3. Keep the official test partition untouched for final evaluation. Create any validation split only from the training partition, with a fixed random seed and stratification where practical. Do not use test results to select or tune models.
4. Use the original `text` or Person B's `normalized_text` consistently and record which field each model uses. Person B's cleaning is intentionally conservative; apply model-specific steps here. For TF-IDF, place the vectorizer and classifier in one scikit-learn pipeline so vocabulary fitting happens only on training data and both are saved together.
5. Train the baseline `TfidfVectorizer + LogisticRegression` model. Set deterministic random seeds where applicable and document meaningful parameters.
6. Evaluate on the training-derived validation split to catch implementation issues. Save a baseline artifact that can already serve predictions while the embedding path is in progress.

**Exit check:** the handoff files load without manual edits, split/label checks are recorded, and the baseline model loads from disk and returns a BANKING77 label plus a confidence value for a sample query.

### Phase 2 — Embedding classifier and fair comparison (Day 1, second half)

1. Generate sentence embeddings for training text using a documented Sentence-BERT model (for example, a compact sentence-transformers model that fits the available machine).
2. Cache embeddings or make preprocessing reproducible so repeated training does not needlessly re-encode all texts.
3. Train Logistic Regression on those embeddings, using the same official train partition as the baseline.
4. Evaluate both approaches on the same untouched official test partition once model choices are fixed.
5. Record accuracy, macro-F1, weighted-F1, and per-class precision, recall, and F1. Save confusion-matrix values in a machine-readable artifact. Report measured values only; do not claim one model is better without evidence.
6. Note any resource constraints, model download requirement, and inference latency observed during development.

Use the same official training partition and preprocessing choice as agreed for the baseline. Fit Logistic Regression only on training embeddings; use validation data for decisions and reserve official test data for the final comparison.

**Exit check:** both models and their label mappings can be loaded from a clean process; metrics identify the data split and model configuration used.

### Phase 3 — Stable inference interface (Day 2, first half)

Implement a small Python interface along these lines (final names are agreed with Person B):

```python
predict(text: str, model_name: str = "tfidf") -> dict
# {"intent": str, "confidence": float, "model": str}

predict_top_k(text: str, model_name: str = "tfidf", k: int = 3) -> list[dict]
# [{"intent": str, "confidence": float}, ...]
```

1. Load models once at application startup or through a cached loader, not once per request.
2. Validate empty/whitespace input and define predictable errors for invalid model names or missing artifacts.
3. Ensure confidence comes from the selected classifier's actual `predict_proba` output. State that it is model confidence, not a calibrated probability of a real-world outcome.
4. Keep label decoding in one place and use the exact label strings from BANKING77.
5. Return plain Python values that Flask can serialize. Do not apply an extra label-ID offset or invent confidence values.
6. Provide a short usage example and sample result for Person B.

**Exit check:** Person B can call the predictor for a string and insert its result into an API response without accessing internal model objects.

### Phase 4 — Similar complaint retrieval and priority rules (Day 2, second half)

**Similarity**

1. Define the retrieval source with Person B: submitted/previous SQLite complaints, plus optional clearly labelled demo examples. BANKING77 is a benchmark dataset, not verified bank complaint history.
2. Implement query and stored-text embeddings with the same Sentence-BERT model and cosine similarity.
3. Return ranked matches with similarity score and stable record identifier/text fields supplied by the caller. Do not silently present a dataset benchmark example as a real customer case.
4. Handle an empty corpus and return an empty match list instead of failing.
5. Keep persistence and database queries in Person B's layer; provide similarity as a pure or narrowly scoped service function.

**Priority**

1. Define a small, reviewable mapping from intents and explicit text conditions to `low`, `medium`, `high`, or `critical` (or another shared agreed scale).
2. Include a short reason string for every suggestion so the UI can explain the result.
3. Cover at least an unauthorized transaction/card case and common lower-urgency informational intents, while avoiding unsupported assumptions about actual SLAs.
4. Make clear in code and UI-facing text that this is a configurable rule suggestion, not a validated fraud detector or risk score.

**Optional summarization**

1. Add a small summarizer only after classification, retrieval, and integration work. Use a locally available pretrained model or an approved available API; do not make core submission depend on an API key.
2. If the dependency/model is unavailable, return an explicit unavailable result or a clearly identified extractive fallback. Never return a fabricated summary.
3. Tell Person B the expected latency and whether the feature is enabled.

**Exit check:** similarity and priority can be called independently by Person B. Optional summary status is explicit.

### Phase 5 — Integration, documentation, and handoff

1. Pair with Person B on one end-to-end API call: submitted text → intent/confidence → priority/reason → similar cases → persisted record → UI result.
2. Resolve import, path, model-loading, serialization, and dependency mismatches together.
3. Document clean setup, how to consume/recreate Person B's prepared dataset package, training/evaluation commands, artifact locations, and how to choose the inference model. Do not describe Person A's model-specific preprocessing as part of Person B's general cleaning step.
4. Share the final metrics with split details and the known limitations. Keep results consistent across the README, dashboard, and demo.
5. If something is incomplete, mark it as incomplete and give Person B a safe disabled state or fallback behavior.

## Handoff contract to Person B

Agree the final names together. The backend should receive structured values equivalent to:

```json
{
  "intent": "cash_withdrawal",
  "confidence": 0.82,
  "model": "tfidf",
  "priority": "medium",
  "priority_reason": "Rule matched: ...",
  "similar_cases": [],
  "summary": null
}
```

The values above are illustrative only, not measured outputs. Person A provides the prediction, rule, and retrieval functions; Person B validates the HTTP contract and persists the complete API result.

## Validation checklist

- [ ] Person B's manifest and processed train/test files are present, loadable, and consistent with the documented source/configuration.
- [ ] Partition sizes, 77 labels, missing/empty rows, and duplicate counts are recorded; any discrepancies are resolved or documented.
- [ ] Official train/test partitions are preserved; validation is derived only from train and no test leakage occurs during fitting or tuning.
- [ ] Model-specific preprocessing is documented and fitted only on training data where it learns vocabulary/statistics.
- [ ] Both pipelines use the same train/test split and label set.
- [ ] Metrics are generated from actual model predictions and saved with configuration details.
- [ ] Model artifacts reload and inference returns a known label and finite confidence in `[0, 1]`.
- [ ] Empty input, missing artifact, and unknown model selection have defined behavior.
- [ ] Similarity ranks by cosine score and returns no fabricated case for an empty corpus.
- [ ] Priority output includes the matched rule/reason and avoids risk/fraud claims.
- [ ] Optional summarization failure is visible and does not break complaint submission.
- [ ] Person B has a working import example and knows which features are ready.

## Time-box and fallback order

1. TF-IDF classifier + stable inference interface.
2. Flask integration with Person B and complaint result display.
3. Sentence-BERT classifier and honest model comparison.
4. Similarity retrieval.
5. Priority explanations and optional summarization polish.

If compute or model downloads block Sentence-BERT, deliver the working baseline and report the blocker precisely. Do not imply that the second model was trained or evaluated if it was not.
