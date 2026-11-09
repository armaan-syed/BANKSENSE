"""Evaluate both trained pipelines once on the untouched official test split.

Usage (from the repository root):

    python -m backend.nlp.evaluate

Writes JSON/CSV/Markdown reports to `backend/reports/`. This module is the only
place that reads `data/processed/test.csv` after choices are frozen.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)

from backend.nlp.config import (
    DEFAULT_TEXT_FIELD,
    LABEL_CLASSES_NAME,
    MODELS_DIR,
    REPORTS_DIR,
    SBERT_ARTIFACT_NAME,
    SBERT_MODEL_NAME,
    TFIDF_ARTIFACT_NAME,
    TRAINING_METADATA_NAME,
)
from backend.nlp.data import ensure_valid_dataset, load_test
from backend.nlp.encoder import encode_texts
from backend.nlp.preprocess import texts_from_frame


def _load_label_classes() -> list[str]:
    path = MODELS_DIR / LABEL_CLASSES_NAME
    labels = json.loads(path.read_text(encoding="utf-8"))
    return [str(label) for label in labels]


def _load_tfidf():
    artifact = joblib.load(MODELS_DIR / TFIDF_ARTIFACT_NAME)
    return artifact["classifier"], artifact.get("metadata", {})


def _load_sbert():
    artifact = joblib.load(MODELS_DIR / SBERT_ARTIFACT_NAME)
    model_name = artifact.get("embedding_model", SBERT_MODEL_NAME)
    if model_name != SBERT_MODEL_NAME:
        raise RuntimeError(
            f"Artifact uses '{model_name}' but runtime config uses "
            f"'{SBERT_MODEL_NAME}'"
        )
    return artifact["classifier"], artifact.get("metadata", {})


def _metrics(y_true, y_pred, labels: list[str]) -> dict:
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "macro_f1": round(float(f1_score(y_true, y_pred, average="macro")), 4),
        "weighted_f1": round(
            float(f1_score(y_true, y_pred, average="weighted")), 4
        ),
    }


def _write_classification_report(
    y_true, y_pred, labels: list[str], path
) -> None:
    report = classification_report(
        y_true,
        y_pred,
        labels=labels,
        output_dict=True,
        zero_division=0,
    )
    rows = []
    for label in labels:
        entry = report[label]
        rows.append(
            {
                "label": label,
                "precision": round(float(entry["precision"]), 4),
                "recall": round(float(entry["recall"]), 4),
                "f1_score": round(float(entry["f1-score"]), 4),
                "support": int(entry["support"]),
            }
        )
    for average in ("macro avg", "weighted avg"):
        entry = report[average]
        rows.append(
            {
                "label": average,
                "precision": round(float(entry["precision"]), 4),
                "recall": round(float(entry["recall"]), 4),
                "f1_score": round(float(entry["f1-score"]), 4),
                "support": int(entry["support"]),
            }
        )
    rows.append(
        {
            "label": "accuracy",
            "precision": "",
            "recall": "",
            "f1_score": round(float(report["accuracy"]), 4),
            "support": int(len(y_true)),
        }
    )
    pd.DataFrame(rows).to_csv(path, index=False)


def _write_confusion_matrix(y_true, y_pred, labels: list[str], path) -> None:
    matrix = confusion_matrix(y_true, y_pred, labels=labels)
    frame = pd.DataFrame(matrix, index=labels, columns=labels)
    frame.to_csv(path)


def _lowest_f1(report_path, limit: int = 5) -> list[dict]:
    frame = pd.read_csv(report_path)
    frame = frame[
        ~frame["label"].isin(["macro avg", "weighted avg", "accuracy"])
    ]
    frame = frame.sort_values("f1_score").head(limit)
    return [
        {
            "label": row["label"],
            "f1_score": float(row["f1_score"]),
            "support": int(row["support"]),
        }
        for _, row in frame.iterrows()
    ]


def evaluate() -> dict:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    dataset = ensure_valid_dataset()
    frame = load_test()
    texts = texts_from_frame(frame, DEFAULT_TEXT_FIELD)
    y_true = frame["label"].tolist()
    labels = _load_label_classes()

    training_metadata = {}
    metadata_path = MODELS_DIR / TRAINING_METADATA_NAME
    if metadata_path.exists():
        training_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    tfidf, tfidf_meta = _load_tfidf()
    started = time.perf_counter()
    tfidf_predictions = tfidf.predict(texts)
    tfidf_seconds = time.perf_counter() - started

    sbert, sbert_meta = _load_sbert()
    started = time.perf_counter()
    embeddings = encode_texts(texts, batch_size=64)
    encode_seconds = time.perf_counter() - started
    started = time.perf_counter()
    sbert_predictions = sbert.predict(embeddings)
    classify_seconds = time.perf_counter() - started

    tfidf_predictions = [str(label) for label in tfidf_predictions]
    sbert_predictions = [str(label) for label in sbert_predictions]

    tfidf_report = REPORTS_DIR / "classification_report_tfidf.csv"
    sbert_report = REPORTS_DIR / "classification_report_sbert.csv"
    _write_classification_report(y_true, tfidf_predictions, labels, tfidf_report)
    _write_classification_report(y_true, sbert_predictions, labels, sbert_report)
    _write_confusion_matrix(
        y_true, tfidf_predictions, labels, REPORTS_DIR / "confusion_matrix_tfidf.csv"
    )
    _write_confusion_matrix(
        y_true, sbert_predictions, labels, REPORTS_DIR / "confusion_matrix_sbert.csv"
    )

    rows = len(texts)
    comparison = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "train_rows": dataset["split_sizes"]["train"],
            "test_rows": dataset["split_sizes"]["test"],
            "label_count": dataset["label_count"],
            "text_field": DEFAULT_TEXT_FIELD,
            "duplicate_texts_test": dataset["duplicate_texts"]["test"],
        },
        "evaluation_policy": {
            "test_split_used_once": True,
            "validation_split_source": "train.csv only",
            "seed": training_metadata.get("dataset", {}).get("seed"),
        },
        "models": {
            "tfidf": {
                **_metrics(y_true, tfidf_predictions, labels),
                "inference_ms_per_example": round(
                    tfidf_seconds / rows * 1000, 3
                ),
                "config": tfidf_meta.get("config", tfidf_meta)
                if tfidf_meta
                else training_metadata.get("tfidf", {}).get("config", {}),
            },
            "sbert": {
                **_metrics(y_true, sbert_predictions, labels),
                "inference_ms_per_example": round(
                    (encode_seconds + classify_seconds) / rows * 1000, 3
                ),
                "embedding_ms_per_example": round(
                    encode_seconds / rows * 1000, 3
                ),
                "config": sbert_meta or training_metadata.get("sbert", {}),
                "embedding_model": SBERT_MODEL_NAME,
            },
        },
        "lowest_f1_classes": {
            "tfidf": _lowest_f1(tfidf_report),
            "sbert": _lowest_f1(sbert_report),
        },
        "notes": [
            "Confidence is raw predict_proba output and is not calibrated.",
            "Test rows were used only for this final evaluation.",
            "BANKING77 is a benchmark dataset, not production bank traffic.",
            "Priority is a triage hint, not fraud or risk scoring.",
        ],
        "environment": training_metadata.get("sbert", {}).get("environment", {}),
    }
    (REPORTS_DIR / "model_comparison.json").write_text(
        json.dumps(comparison, indent=2), encoding="utf-8"
    )

    _write_manifest(comparison)
    return comparison


def _write_manifest(comparison: dict) -> None:
    tfidf = comparison["models"]["tfidf"]
    sbert = comparison["models"]["sbert"]
    dataset = comparison["dataset"]
    tfidf_cfg = tfidf.get("config", {})
    sbert_cfg = sbert.get("config", {})

    lines = [
        "# Evaluation manifest",
        "",
        f"Generated: {comparison['generated_at']}",
        "",
        "## Split",
        "",
        f"- Training rows: {dataset['train_rows']}",
        f"- Official test rows: {dataset['test_rows']}",
        f"- Labels: {dataset['label_count']}",
        f"- Text field: `{dataset['text_field']}`",
        f"- Validation split: {comparison['evaluation_policy']['validation_split_source']}",
        f"- Seed: {comparison['evaluation_policy']['seed']}",
        "- The test split was used once, after model choices were frozen.",
        "",
        "## Measured results (official test split)",
        "",
        "| Model | Accuracy | Macro-F1 | Weighted-F1 | Inference ms/example |",
        "|---|---:|---:|---:|---:|",
        f"| TF-IDF + LogReg | {tfidf['accuracy']:.4f} | {tfidf['macro_f1']:.4f} | "
        f"{tfidf['weighted_f1']:.4f} | {tfidf['inference_ms_per_example']:.3f} |",
        f"| SBERT + LogReg | {sbert['accuracy']:.4f} | {sbert['macro_f1']:.4f} | "
        f"{sbert['weighted_f1']:.4f} | {sbert['inference_ms_per_example']:.3f} |",
        "",
        "## Selected configurations",
        "",
        f"- TF-IDF: `{tfidf_cfg}`",
        f"- SBERT: `{sbert_cfg}` (embedding model `{sbert['embedding_model']}`)",
        "",
        "## Lowest per-class F1",
        "",
    ]
    for name in ("tfidf", "sbert"):
        lines.append(f"### {name}")
        lines.append("")
        for item in comparison["lowest_f1_classes"][name]:
            lines.append(
                f"- `{item['label']}`: F1 {item['f1_score']:.4f} "
                f"(support {item['support']})"
            )
        lines.append("")
    lines.extend(
        [
            "## Reproduction",
            "",
            "```bash",
            "python -m backend.nlp.train --model all",
            "python -m backend.nlp.evaluate",
            "```",
            "",
            "Artifacts live in `backend/models/` (git-ignored) and reports in "
            "`backend/reports/`. Per-class precision/recall/F1 and raw-count "
            "confusion matrices are in the sibling CSV files.",
            "",
            "## Notes and limitations",
            "",
            "- Confidence is raw `predict_proba` output, not calibrated.",
            "- BANKING77 is a benchmark dataset; production traffic will differ.",
            "- Priority suggestions are triage hints, not fraud/risk scores.",
            "- The summariser is optional; when unavailable the API reports "
            "`summary_status: unavailable`.",
            "",
        ]
    )
    (REPORTS_DIR / "evaluation_manifest.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main() -> None:
    comparison = evaluate()
    for name, metrics in comparison["models"].items():
        print(
            f"{name}: accuracy={metrics['accuracy']:.4f} "
            f"macro-F1={metrics['macro_f1']:.4f} "
            f"weighted-F1={metrics['weighted_f1']:.4f}"
        )
    print(f"Reports written to {REPORTS_DIR}")


if __name__ == "__main__":
    main()
