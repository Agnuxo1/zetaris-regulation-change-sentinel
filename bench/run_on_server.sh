#!/bin/bash
# Run from the repository mirror on the server that hosts Zetaris (see README).
set -e
ENVFILE=${ZETARIS_ENV_FILE_HOST:-$HOME/sentinel/zetaris-platform/.env}
sudo -n docker run --rm --network sentinel-zetaris_default \
  -v "$(pwd)":/work -v "$ENVFILE":/run/zetaris.env:ro -w /work \
  -e ZETARIS_ENV_FILE=/run/zetaris.env -e ZETARIS_REST_URL=http://api:8888/api/v1.0 \
  -e ZETARIS_LOGIN_URL=http://ui:3000/api/auth/login \
  -e CONTROL_PG_DSN="host=regsentinel-pg dbname=grants user=sentinel_reader" \
  -e CONTROL_CSV=/work/data/processed/paragraphs.csv -e BENCH_RUNS=${BENCH_RUNS:-30} -e BENCH_TAG=${BENCH_TAG:-} \
  python:3.12-slim bash -c "pip install -q -r bench/requirements.txt 2>&1 | tail -1; python bench/benchmark.py"
