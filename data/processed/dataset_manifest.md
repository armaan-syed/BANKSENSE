# BANKING77 dataset manifest

- **Source:** https://huggingface.co/datasets/PolyAI/banking77
- **Upstream files:** https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/ (PolyAI-LDN/task-specific-datasets, `banking_data`)
- **Access date (UTC):** 2026-11-09 11:24 UTC
- **Configuration:** official PolyAI BANKING77 split (single-label intent classification)

## Files

| file | role | notes |
|---|---|---|
| `data/raw/train.csv` | immutable raw download | not edited by hand |
| `data/raw/test.csv` | immutable raw download | not edited by hand |
| `data/raw/categories.json` | label vocabulary | 77 labels |
| `data/processed/train.csv` | model-ready train partition | official split preserved |
| `data/processed/test.csv` | model-ready test partition | reserved for final evaluation |
| `data/processed/prepare_banking77.py` | reproducible preparation | rerun to regenerate |

## Raw checksums (SHA-256)

```text
train.csv       b06e26ac675513959a63135f11b94ea7786ed02da65db93a5650d8838cbc664b
test.csv        d12d6e3bc4c3103966ae786dc435913c0c563dfa328f5a3646d0e62cfeeb474d
categories.json 53261da888122daf2d120d925458631d9619e15d82e56052e7a42e535ce32b63
```

## Processed schema

`example_id,text,normalized_text,label`

- `example_id`: deterministic id scoped to the split (`train-000001`, `test-000001`).
- `text`: original BANKING77 text, unchanged.
- `normalized_text`: trim + collapse repeated whitespace only.
- `label`: exact BANKING77 intent label string.

## Split sizes

| split | rows | expected | labels | distinct texts | duplicate texts | empty text | missing label |
|---|---|---|---|---|---|---|---|
| train | 10003 | 10003 | 77 | 9999 | 4 | 0 | 0 |
| test | 3080 | 3080 | 77 | 3079 | 1 | 0 | 0 |

Differences from expected benchmark counts: none

## Label consistency

- Labels present in both splits: 77
- Labels only in train: none
- Labels only in test: none
- Vocabulary size (`categories.json`): 77

Most frequent train intents: `card_payment_fee_charged` (187), `direct_debit_payment_not_recognised` (182), `balance_not_updated_after_cheque_or_cash_deposit` (181), `wrong_amount_of_cash_received` (180), `cash_withdrawal_charge` (177)
Most frequent test intents: `card_arrival` (40), `card_linking` (40), `exchange_rate` (40), `card_payment_wrong_exchange_rate` (40), `extra_charge_on_statement` (40)

## Cleaning steps

1. Downloaded the official `train.csv`, `test.csv`, and `categories.json` into `data/raw/`.
2. Trimmed leading/trailing whitespace and collapsed internal repeated whitespace into
   `normalized_text`.
3. Kept `text` exactly as supplied; retained punctuation, casing, contractions, and wording.
4. Did **not** remove stop words, did **not** stem/lemmatize, and did **not** delete
   duplicate rows or change labels.

## Split discipline

The official train/test partitions are preserved. The test set must remain untouched
until final evaluation: no vocabulary fitting, hyperparameter tuning, validation
splitting, or model selection may use it. Person A derives any validation split from
`train.csv` only.

## Loading example (Person A)

```python
import pandas as pd

train = pd.read_csv("data/processed/train.csv", dtype=str)
test = pd.read_csv("data/processed/test.csv", dtype=str)

expected = ["example_id", "text", "normalized_text", "label"]
assert list(train.columns) == expected
assert list(test.columns) == expected
assert train["text"].notna().all() and test["text"].notna().all()
assert train["label"].nunique() == 77 and test["label"].nunique() == 77

print(train.shape, test.shape)  # (10003, 4) (3080, 4)
print(sorted(train["label"].unique()) == sorted(test["label"].unique()))
```

## Handoff status

Person B validated the files above (schema, counts, labels, nulls, duplicates) and
they load without manual edits. Person A must independently confirm the package
before training. Any unexpected source difference must be investigated and recorded
here rather than forcing the expected counts.

## Regenerate

```bash
python data/processed/prepare_banking77.py --force-download
```
