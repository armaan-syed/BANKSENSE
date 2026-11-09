"""Train the TF-IDF and Sentence-BERT complaint classifiers.

Usage (from the repository root):

    python -m backend.nlp.train --model all
    python -m backend.nlp.train --model tfidf
    python -m backend.nlp.train --model sbert

A 90/10 stratified validation split is carved out of `train.csv` for the tiny
hyper-parameter search. The official `test.csv` is never touched here; it is
used once by `backend.nlp.evaluate`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from backend.nlp.config import (
    DEFAULT_TEXT_FIELD,
    LABEL_CLASSES_NAME,
    MODELS_DIR,
    RANDOM_SEED,
    REPORTS_DIR,
    SBERT_ARTIFACT_NAME,
    SBERT_MODEL_NAME,
    SBERT_MODEL_NAME_FILE,
    TFIDF_ARTIFACT_NAME,
    TRAINING_METADATA_NAME,
    VALIDATION_SIZE,
)
from backend.nlp.data import ensure_valid_dataset, load_train
from backend.nlp.encoder import encode_texts
from backend.nlp.preprocess import texts_from_frame

TFIDF_CONFIGS = [
    {"ngram_range": (1, 2), "min_df": 2, "C": 1.0},
    {"ngram_range": (1, 1), "min_df": 2, "C": 1.0},
    {"ngram_range": (1, 2), "min_df": 1, "C": 2.0},
]
SBERT_C_GRID = [1.0, 4.0, 10.0]


def _build_tfidf_pipeline(config: dict) -> Pipeline:
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=config["ngram_range"],
                    min_df=config["min_df"],
                    max_df=0.9,
                    sublinear_tf=True,
                    strip_accents="unicode",
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    C=config["C"],
                    max_iter=2000,
                    solver="lbfgs",
                ),
            ),
        ]
    )


def _build_sbert_classifier(C: float) -> LogisticRegression:
    return LogisticRegression(C=C, max_iter=2000, solver="lbfgs")


def _split_indices(labels: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    indices = np.arange(len(labels))
    train_idx, val_idx = train_test_split(
        indices,
        test_size=VALIDATION_SIZE,
        stratify=labels,
        random_state=RANDOM_SEED,
    )
    return train_idx, val_idx


def _train_tfidf(texts: list[str], labels: np.ndarray, train_idx, val_idx):
    best = None
    for config in TFIDF_CONFIGS:
        started = time.perf_counter()
        pipeline = _build_tfidf_pipeline(config)
        pipeline.fit(
            [texts[i] for i in train_idx], labels[train_idx]
        )
        predictions = pipeline.predict([texts[i] for i in val_idx])
        score = f1_score(labels[val_idx], predictions, average="macro")
        elapsed = time.perf_counter() - started
        print(
            f"  tfidf {config} validation macro-F1={score:.4f} ({elapsed:.1f}s)"
        )
        if best is None or score > best["score"]:
            best = {"config": config, "score": float(score), "seconds": elapsed}

    started = time.perf_counter()
    final = _build_tfidf_pipeline(best["config"])
    final.fit(texts, labels)
    best["fit_seconds"] = time.perf_counter() - started
    best["model"] = final
    print(
        f"  selected tfidf {best['config']} (val macro-F1={best['score']:.4f})"
    )
    return best


def _embedding_cache_path(texts: list[str]) -> Path:
    digest = hashlib.sha256()
    digest.update(SBERT_MODEL_NAME.encode("utf-8"))
    digest.update(b"\x1f")
    for text in texts:
        digest.update(text.encode("utf-8"))
        digest.update(b"\x1f")
    key = digest.hexdigest()[:16]
    return MODELS_DIR / "embedding_cache" / f"train_{key}_{len(texts)}.npy"


def _load_or_encode(texts: list[str]) -> tuple[np.ndarray, str]:
    path = _embedding_cache_path(texts)
    if path.exists():
        vectors = np.load(path)
        if vectors.shape[0] == len(texts):
            print(f"  loaded cached SBERT embeddings: {path.name}")
            return vectors, "cache"

    started = time.perf_counter()
    print(f"  encoding {len(texts)} training texts with {SBERT_MODEL_NAME} ...")
    vectors = encode_texts(texts, batch_size=64)
    elapsed = time.perf_counter() - started
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, vectors)
    path.with_suffix(".json").write_text(
        json.dumps(
            {
                "model": SBERT_MODEL_NAME,
                "rows": len(texts),
                "dimensions": int(vectors.shape[1]),
                "seconds": round(elapsed, 2),
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"  cached SBERT embeddings in {elapsed:.1f}s: {path.name}")
    return vectors, "encoded"


def _train_sbert(
    texts: list[str], labels: np.ndarray, train_idx, val_idx
):
    embeddings, source = _load_or_encode(texts)
    best = None
    for C in SBERT_C_GRID:
        started = time.perf_counter()
        classifier = _build_sbert_classifier(C)
        classifier.fit(embeddings[train_idx], labels[train_idx])
        predictions = classifier.predict(embeddings[val_idx])
        score = f1_score(labels[val_idx], predictions, average="macro")
        elapsed = time.perf_counter() - started
        print(f"  sbert C={C} validation macro-F1={score:.4f} ({elapsed:.1f}s)")
        if best is None or score > best["score"]:
            best = {"C": C, "score": float(score), "seconds": elapsed}

    started = time.perf_counter()
    final = _build_sbert_classifier(best["C"])
    final.fit(embeddings, labels)
    best["fit_seconds"] = time.perf_counter() - started
    best["model"] = final
    best["embedding_source"] = source
    best["embedding_dimensions"] = int(embeddings.shape[1])
    print(f"  selected sbert C={best['C']} (val macro-F1={best['score']:.4f})")
    return best


def _environment() -> dict:
    environment = {
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    for name in ("numpy", "pandas", "sklearn", "joblib"):
        try:
            module = __import__(name)
            environment[name] = getattr(module, "__version__", "unknown")
        except Exception:
            environment[name] = "unavailable"
    try:
        import torch

        environment["torch"] = torch.__version__
        environment["torch_cuda"] = bool(torch.cuda.is_available())
    except Exception:
        environment["torch"] = "unavailable"
    try:
        import sentence_transformers

        environment["sentence_transformers"] = sentence_transformers.__version__
    except Exception:
        environment["sentence_transformers"] = "unavailable"
    return environment


def _metadata_path() -> Path:
    return MODELS_DIR / TRAINING_METADATA_NAME


def _update_metadata(section: str, payload: dict) -> None:
    path = _metadata_path()
    metadata = {}
    if path.exists():
        try:
            metadata = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            metadata = {}
    metadata[section] = payload
    metadata["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def _save_label_classes(labels: list[str]) -> None:
    (MODELS_DIR / LABEL_CLASSES_NAME).write_text(
        json.dumps(labels, indent=2), encoding="utf-8"
    )


def train(model_name: str = "all") -> dict:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = ensure_valid_dataset()
    (REPORTS_DIR / "data_validation.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    frame = load_train()
    texts = texts_from_frame(frame, DEFAULT_TEXT_FIELD)
    labels = np.asarray(frame["label"].tolist(), dtype=object)
    train_idx, val_idx = _split_indices(labels)

    results: dict = {
        "dataset": report["split_sizes"],
        "label_count": report["label_count"],
        "split": {
            "train": int(len(train_idx)),
            "validation": int(len(val_idx)),
            "seed": RANDOM_SEED,
            "validation_size": VALIDATION_SIZE,
        },
        "text_field": DEFAULT_TEXT_FIELD,
    }

    if model_name in ("all", "tfidf"):
        print("Training TF-IDF + Logistic Regression ...")
        best = _train_tfidf(texts, labels, train_idx, val_idx)
        pipeline = best.pop("model")
        joblib.dump(
            {"classifier": pipeline, "metadata": best},
            MODELS_DIR / TFIDF_ARTIFACT_NAME,
            compress=3,
        )
        _save_label_classes([str(label) for label in pipeline.classes_])
        _update_metadata(
            "tfidf",
            {
                **best,
                "artifact": TFIDF_ARTIFACT_NAME,
                "trained_at": datetime.now(timezone.utc).isoformat(),
                "text_field": DEFAULT_TEXT_FIELD,
                "seed": RANDOM_SEED,
                "split": results["split"],
            },
        )
        results["tfidf"] = {
            "config": best["config"],
            "validation_macro_f1": best["score"],
        }
        print(f"Saved {MODELS_DIR / TFIDF_ARTIFACT_NAME}")

    if model_name in ("all", "sbert"):
        print("Training Sentence-BERT + Logistic Regression ...")
        best = _train_sbert(texts, labels, train_idx, val_idx)
        classifier = best.pop("model")
        joblib.dump(
            {
                "classifier": classifier,
                "embedding_model": SBERT_MODEL_NAME,
                "metadata": best,
            },
            MODELS_DIR / SBERT_ARTIFACT_NAME,
            compress=3,
        )
        (MODELS_DIR / SBERT_MODEL_NAME_FILE).write_text(
            SBERT_MODEL_NAME, encoding="utf-8"
        )
        _save_label_classes([str(label) for label in classifier.classes_])
        _update_metadata(
            "sbert",
            {
                **best,
                "embedding_model": SBERT_MODEL_NAME,
                "artifact": SBERT_ARTIFACT_NAME,
                "trained_at": datetime.now(timezone.utc).isoformat(),
                "text_field": DEFAULT_TEXT_FIELD,
                "seed": RANDOM_SEED,
                "split": results["split"],
                "environment": _environment(),
            },
        )
        results["sbert"] = {
            "C": best["C"],
            "validation_macro_f1": best["score"],
            "embedding_source": best["embedding_source"],
        }
        print(f"Saved {MODELS_DIR / SBERT_ARTIFACT_NAME}")

    _update_metadata(
        "dataset",
        {
            "train_rows": report["split_sizes"]["train"],
            "test_rows": report["split_sizes"]["test"],
            "label_count": report["label_count"],
            "text_field": DEFAULT_TEXT_FIELD,
            "seed": RANDOM_SEED,
        },
    )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model", choices=("all", "tfidf", "sbert"), default="all"
    )
    args = parser.parse_args()
    results = train(args.model)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
