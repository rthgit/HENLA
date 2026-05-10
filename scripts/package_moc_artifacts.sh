#!/usr/bin/env bash
set -e

OUT="henla_moc_scale_run_artifacts_$(date +%Y%m%d_%H%M%S).zip"

zip -r "$OUT" \
  checkpoints \
  .benchmark_runs \
  artifacts \
  logs \
  PROJECT_LOG.md \
  README.md \
  configs \
  scripts \
  requirements-scale.txt \
  Makefile \
  *.py \
  core || true

echo "Created artifact zip: $OUT"
ls -lh "$OUT"
