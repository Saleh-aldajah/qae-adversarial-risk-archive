# QAE V16 reproducibility container — LEGACY (v16 tree layout).
# For the current release use the v25 Dockerfile at the ARCHIVE ROOT
# (../Dockerfile): the v25 suite references ../comparator and
# ../theory_test_consol, so the build context must be the archive root.
# Build from qae_experiments root:
#   docker build -t qae-v16-reproduce .
# Full reproduction:
#   docker run --rm qae-v16-reproduce python reproduce_all.py
# Fast verification only:
#   docker run --rm qae-v16-reproduce python reproduce_fast.py
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /qae
COPY requirements.txt /qae/requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY . /qae
CMD ["python", "reproduce_fast.py"]
