#!/usr/bin/env bash
set -euo pipefail

REPORT_DIR="htmlcov"

echo "Running test coverage..."
uv run pytest \
  --cov=src \
  --cov-report=html:"$REPORT_DIR" \
  --cov-report=term-missing \
  --cov-config=pyproject.toml \
  --ignore=tests/algorithms/others/test_anyburl_parsing.py \
  --ignore=tests/test_metrics_validation.py \
  -q \
  "$@"

echo ""
echo "HTML report: $REPORT_DIR/index.html"
