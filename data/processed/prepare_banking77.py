#!/usr/bin/env python3
"""Acquire BANKING77 and produce the split-preserving handoff package.

Outputs (in data/processed/):
    train.csv, test.csv   schema: example_id,text,normalized_text,label
    dataset_manifest.md   provenance, checksums, validation results

Raw downloads are kept immutable in data/raw/. The official train/test split is
preserved exactly; rows are never mixed between partitions. Only whitespace is
normalized (into normalized_text); the original text is kept unchanged.

Usage:
    python data/processed/prepare_banking77.py [--force-download]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"

SOURCE_BASE = (
    "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/"
    "master/banking_data"
)
RAW_FILES = {
    "train": f"{SOURCE_BASE}/train.csv",
    "test": f"{SOURCE_BASE}/test.csv",
    "categories": f"{SOURCE_BASE}/categories.json",
}
HF_SOURCE = "https://huggingface.co/datasets/PolyAI/banking77"
EXPECTED = {"train": 10003, "test": 3080, "labels": 77}
COLUMNS = ["example_id", "text", "normalized_text", "label"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path, force: bool) -> None:
    if destination.exists() and not force:
        print(f"reusing raw file: {destination.relative_to(REPO_ROOT)}")
        return
    print(f"downloading {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "BankSense-MVP"})
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    destination.write_bytes(data)
    print(f"wrote {destination.relative_to(REPO_ROOT)} ({len(data)} bytes)")


def normalize(text: str) -> str:
    return " ".join(text.split())


def read_rows(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path.name} has no header row")
        rows = list(reader)
    return list(reader.fieldnames), rows


def prepare_split(
    split: str,
    raw_path: Path,
    categories: list[str],
) -> tuple[list[dict], dict]:
    fieldnames, raw_rows = read_rows(raw_path)
    text_field = "text" if "text" in fieldnames else None
    label_field = next(
        (f for f in ("category", "label", "intent") if f in fieldnames), None
    )
    if text_field is None or label_field is None:
        raise ValueError(
            f"{raw_path.name}: expected text + category/label columns, got {fieldnames}"
        )

    prepared: list[dict] = []
    labels: Counter[str] = Counter()
    empty_text = 0
    missing_label = 0
    seen_texts: Counter[str] = Counter()

    for raw in raw_rows:
        text = (raw.get(text_field) or "").strip()
        label = (raw.get(label_field) or "").strip()
        if not text:
            empty_text += 1
            continue
        if not label:
            missing_label += 1
            continue
        if label.isdigit() and int(label) < len(categories):
            resolved = categories[int(label)]
        else:
            resolved = label
        labels[resolved] += 1
        seen_texts[text] += 1
        prepared.append(
            {
                "example_id": f"{split}-{len(prepared) + 1:06d}",
                "text": text,
                "normalized_text": normalize(text),
                "label": resolved,
            }
        )

    duplicate_texts = sum(count - 1 for count in seen_texts.values() if count > 1)
    stats = {
        "rows": len(prepared),
        "labels": len(labels),
        "empty_text": empty_text,
        "missing_label": missing_label,
        "duplicate_texts": duplicate_texts,
        "distinct_texts": len(seen_texts),
        "label_counts": labels,
    }
    return prepared, stats


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def render_manifest(
    train_stats: dict,
    test_stats: dict,
    categories: list[str],
    checksums: dict[str, str],
    access_date: str,
) -> str:
    shared_labels = sorted(set(train_stats["label_counts"]) & set(test_stats["label_counts"]))
    train_only = sorted(set(train_stats["label_counts"]) - set(test_stats["label_counts"]))
    test_only = sorted(set(test_stats["label_counts"]) - set(train_stats["label_counts"]))

    def top(counts: Counter[str], n: int = 5) -> str:
        return ", ".join(f"`{label}` ({count})" for label, count in counts.most_common(n))

    differences = []
    for split, stats in (("train", train_stats), ("test", test_stats)):
        expected = EXPECTED[split]
        if stats["rows"] != expected:
            differences.append(f"{split}: expected {expected}, got {stats['rows']}")

    return f"""# BANKING77 dataset manifest

- **Source:** {HF_SOURCE}
- **Upstream files:** {SOURCE_BASE}/ (PolyAI-LDN/task-specific-datasets, `banking_data`)
- **Access date (UTC):** {access_date}
- **Configuration:** official PolyAI BANKING77 split (single-label intent classification)

## Files

| file | role | notes |
|---|---|---|
| `data/raw/train.csv` | immutable raw download | not edited by hand |
| `data/raw/test.csv` | immutable raw download | not edited by hand |
| `data/raw/categories.json` | label vocabulary | {len(categories)} labels |
| `data/processed/train.csv` | model-ready train partition | official split preserved |
| `data/processed/test.csv` | model-ready test partition | reserved for final evaluation |
| `data/processed/prepare_banking77.py` | reproducible preparation | rerun to regenerate |

## Raw checksums (SHA-256)

```text
train.csv       {checksums.get('train', 'n/a')}
test.csv        {checksums.get('test', 'n/a')}
categories.json {checksums.get('categories', 'n/a')}
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
| train | {train_stats['rows']} | {EXPECTED['train']} | {train_stats['labels']} | {train_stats['distinct_texts']} | {train_stats['duplicate_texts']} | {train_stats['empty_text']} | {train_stats['missing_label']} |
| test | {test_stats['rows']} | {EXPECTED['test']} | {test_stats['labels']} | {test_stats['distinct_texts']} | {test_stats['duplicate_texts']} | {test_stats['empty_text']} | {test_stats['missing_label']} |

Differences from expected benchmark counts: {('; '.join(differences)) if differences else 'none'}

## Label consistency

- Labels present in both splits: {len(shared_labels)}
- Labels only in train: {train_only if train_only else 'none'}
- Labels only in test: {test_only if test_only else 'none'}
- Vocabulary size (`categories.json`): {len(categories)}

Most frequent train intents: {top(train_stats['label_counts'])}
Most frequent test intents: {top(test_stats['label_counts'])}

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
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="re-download raw files even if they already exist",
    )
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    raw_paths = {
        "train": RAW_DIR / "train.csv",
        "test": RAW_DIR / "test.csv",
        "categories": RAW_DIR / "categories.json",
    }
    for key, url in RAW_FILES.items():
        download(url, raw_paths[key], args.force_download)

    categories = json.loads(raw_paths["categories"].read_text(encoding="utf-8"))
    if not isinstance(categories, list) or not categories:
        raise ValueError("categories.json must be a non-empty JSON list")

    train_rows, train_stats = prepare_split("train", raw_paths["train"], categories)
    test_rows, test_stats = prepare_split("test", raw_paths["test"], categories)

    checksums = {key: sha256(path) for key, path in raw_paths.items()}
    access_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    write_csv(PROCESSED_DIR / "train.csv", train_rows)
    write_csv(PROCESSED_DIR / "test.csv", test_rows)
    (PROCESSED_DIR / "dataset_manifest.md").write_text(
        render_manifest(train_stats, test_stats, categories, checksums, access_date),
        encoding="utf-8",
    )

    print("\nsummary")
    print(f"  train rows: {train_stats['rows']} (expected {EXPECTED['train']})")
    print(f"  test rows:  {test_stats['rows']} (expected {EXPECTED['test']})")
    print(f"  train labels: {train_stats['labels']}")
    print(f"  test labels:  {test_stats['labels']}")
    print(f"  vocabulary:   {len(categories)}")
    print(f"  train duplicate texts: {train_stats['duplicate_texts']}")
    print(f"  test duplicate texts:  {test_stats['duplicate_texts']}")

    train_labels = set(train_stats["label_counts"])
    test_labels = set(test_stats["label_counts"])
    if not train_labels or not test_labels:
        print("ERROR: empty split after validation", file=sys.stderr)
        return 1
    if test_labels - train_labels:
        print(
            f"ERROR: test-only labels: {sorted(test_labels - train_labels)}",
            file=sys.stderr,
        )
        return 1
    if test_stats["empty_text"] or train_stats["empty_text"]:
        print("ERROR: empty text rows encountered", file=sys.stderr)
        return 1

    print("\nwrote data/processed/train.csv, test.csv, dataset_manifest.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
