FROM python:3.12-slim

# Keep the image CPU-only, offline at request time, and self-contained.
# Fly.io runs this image on a 2 GB shared-cpu-2x machine and routes to port 8080.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_RETRIES=10 \
    PIP_TIMEOUT=60 \
    PIP_RESUME_RETRIES=10 \
    HF_HOME=/opt/hf-cache \
    SENTENCE_TRANSFORMERS_HOME=/opt/hf-cache \
    BANKSENSE_MODELS_DIR=/app/backend/models \
    BANKSENSE_ENABLE_SUMMARY=0 \
    HOME=/tmp \
    PORT=8080

# libgomp1 is required by the CPU PyTorch / scikit-learn wheels.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Fail fast if the five model artifacts were not supplied at build time.
# They are gitignored and must be placed in backend/models/ before deploying.
COPY models /app/backend/models
RUN test -s /app/backend/models/tfidf_logreg.joblib \
    && test -s /app/backend/models/sbert_logreg.joblib \
    && test -s /app/backend/models/label_classes.json \
    && test -s /app/backend/models/sbert_model_name.txt \
    && test -s /app/backend/models/training_metadata.json

# Install CPU-only torch first so pip never resolves the CUDA wheel.
COPY requirements.txt /tmp/backend-requirements.txt
COPY nlp/requirements.txt /tmp/nlp-requirements.txt
RUN pip install --upgrade pip \
    && pip install --retries 10 --timeout 60 --resume-retries 10 \
        --index-url https://download.pytorch.org/whl/cpu "torch>=2.0" \
    && pip install --retries 10 --timeout 60 --resume-retries 10 \
        -r /tmp/backend-requirements.txt -r /tmp/nlp-requirements.txt

# Application code. The models were copied above, so this does not duplicate
# the model directory (the old `COPY . /app/backend` copied it twice).
COPY __init__.py app.py auth.py config.py env.py errors.py schemas.py /app/backend/
COPY db /app/backend/db
COPY nlp /app/backend/nlp
COPY routes /app/backend/routes
COPY services /app/backend/services

# Pre-fetch exactly the encoder named by backend/models/sbert_model_name.txt.
# The helper fails the build if the file is missing/invalid or if the SBERT
# artifact records a different embedding model. This needs network access.
RUN python -m backend.nlp.prefetch

# The encoder is baked in; never download models during a request.
ENV TRANSFORMERS_OFFLINE=1 \
    HF_HUB_OFFLINE=1

# Run as an unprivileged numeric UID. A numeric UID avoids adding a user
# management package to the slim base image. The app and HF cache are readable
# by the runtime user; /tmp is writable for any incidental temporary files.
RUN chown -R 10001:10001 /app /opt/hf-cache
USER 10001:10001

EXPOSE 8080

# Fly.io routes traffic to the internal port declared in fly.toml (8080).
# Keep one worker: a second worker would load the models into memory twice.
CMD ["sh", "-c", "uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
