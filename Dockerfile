# QAE v25 reproducibility container — build from the ARCHIVE ROOT (this file):
#   docker build -t qae-v25 .
# Quick validation (validators over the shipped artifacts; minutes):
#   docker run --rm qae-v25
# Full offline regeneration (hours; never submits hardware jobs):
#   docker run --rm qae-v25 python qae_experiments/reproduce_all.py
# Dependency pins: qae_experiments/requirements.txt (= environment.yml).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# build tools only as a fallback for any dependency without a cp312 wheel
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /qae
COPY qae_experiments/requirements.txt /qae/qae_experiments/requirements.txt
RUN pip install --upgrade pip && pip install -r qae_experiments/requirements.txt
COPY . /qae

WORKDIR /qae/qae_experiments
CMD ["python", "reproduce_all.py", "--quick"]
