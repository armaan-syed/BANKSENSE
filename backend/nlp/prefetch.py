"""Validate and pre-fetch the SBERT encoder named by the trained artifact.

This runs during `docker build`, after the five model artifacts and the Python
dependencies are present. It deliberately reads `sbert_model_name.txt` directly
so the encoder baked into the image is always the one recorded by training.
"""

from __future__ import annotations

import json
import sys

from backend.nlp.config import (
    MODELS_DIR,
    SBERT_ARTIFACT_NAME,
    SBERT_MODEL_NAME_FILE,
    TRAINING_METADATA_NAME,
    validate_sbert_model_name,
)


def _fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def main() -> int:
    model_name_path = MODELS_DIR / SBERT_MODEL_NAME_FILE
    if not model_name_path.is_file():
        return _fail(f"required SBERT model name artifact is missing: {model_name_path}")

    try:
        model_name = validate_sbert_model_name(
            model_name_path.read_text(encoding="utf-8"), str(model_name_path)
        )
    except (OSError, ValueError) as exc:
        return _fail(f"invalid SBERT model name artifact {model_name_path}: {exc}")

    artifact_path = MODELS_DIR / SBERT_ARTIFACT_NAME
    try:
        import joblib

        artifact = joblib.load(artifact_path)
    except Exception as exc:
        return _fail(f"could not load {artifact_path} to verify its encoder: {exc}")

    artifact_model = (
        artifact.get("embedding_model") if isinstance(artifact, dict) else None
    )
    if artifact_model and artifact_model != model_name:
        return _fail(
            f"{artifact_path.name} was trained with {artifact_model!r}, but "
            f"{model_name_path.name} names {model_name!r}"
        )

    try:
        from sentence_transformers import SentenceTransformer

        SentenceTransformer(model_name)
    except Exception as exc:
        return _fail(f"could not pre-fetch SBERT encoder {model_name!r}: {exc}")

    metadata_path = MODELS_DIR / TRAINING_METADATA_NAME
    if metadata_path.is_file():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            environment = metadata.get("sbert", {}).get("environment")
        except Exception:
            environment = None
        if environment:
            print(
                "Recorded training environment: "
                f"{json.dumps(environment, sort_keys=True)}"
            )

    print(f"Pre-fetched SBERT encoder from {model_name_path.name}: {model_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
