# Evaluation manifest

Generated: 2026-11-09T12:50:21.482179+00:00

## Split

- Training rows: 10003
- Official test rows: 3080
- Labels: 77
- Text field: `normalized_text`
- Validation split: train.csv only
- Seed: 42
- The test split was used once, after model choices were frozen.

## Measured results (official test split)

| Model | Accuracy | Macro-F1 | Weighted-F1 | Inference ms/example |
|---|---:|---:|---:|---:|
| TF-IDF + LogReg | 0.8779 | 0.8781 | 0.8781 | 0.017 |
| SBERT + LogReg | 0.9295 | 0.9294 | 0.9294 | 3.615 |

## Selected configurations

- TF-IDF: `{'ngram_range': (1, 2), 'min_df': 1, 'C': 2.0}`
- SBERT: `{'C': 10.0, 'score': 0.9327195370373147, 'seconds': 15.725231174998044, 'fit_seconds': 19.924481572998047, 'embedding_source': 'encoded', 'embedding_dimensions': 384}` (embedding model `sentence-transformers/all-MiniLM-L6-v2`)

## Lowest per-class F1

### tfidf

- `card_not_working`: F1 0.7000 (support 40)
- `balance_not_updated_after_bank_transfer`: F1 0.7111 (support 40)
- `virtual_card_not_working`: F1 0.7302 (support 40)
- `card_payment_not_recognised`: F1 0.7436 (support 40)
- `pending_transfer`: F1 0.7500 (support 40)

### sbert

- `transfer_not_received_by_recipient`: F1 0.7765 (support 40)
- `balance_not_updated_after_bank_transfer`: F1 0.7838 (support 40)
- `pending_transfer`: F1 0.8169 (support 40)
- `declined_transfer`: F1 0.8406 (support 40)
- `direct_debit_payment_not_recognised`: F1 0.8462 (support 40)

## Reproduction

```bash
python -m backend.nlp.train --model all
python -m backend.nlp.evaluate
```

Artifacts live in `backend/models/` (git-ignored) and reports in `backend/reports/`. Per-class precision/recall/F1 and raw-count confusion matrices are in the sibling CSV files.

## Notes and limitations

- Confidence is raw `predict_proba` output, not calibrated.
- BANKING77 is a benchmark dataset; production traffic will differ.
- Priority suggestions are triage hints, not fraud/risk scores.
- The summariser is optional; when unavailable the API reports `summary_status: unavailable`.
