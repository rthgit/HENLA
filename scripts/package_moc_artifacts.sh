#!/usr/bin/env bash
set -e

OUT="henla_moc_scale_run_artifacts_$(date +%Y%m%d_%H%M%S).zip"

python -c "
import os
import zipfile

out_name = '${OUT}'
folders = ['checkpoints', '.benchmark_runs', 'artifacts', 'logs', 'configs', 'scripts', 'core']
files = ['PROJECT_LOG.md', 'README.md', 'requirements-scale.txt', 'Makefile']
py_files = [f for f in os.listdir('.') if f.endswith('.py')]

with zipfile.ZipFile(out_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for item in files + py_files:
        if os.path.exists(item):
            zipf.write(item)
    for folder in folders:
        if os.path.exists(folder):
            for root, dirs, fnames in os.walk(folder):
                for fname in fnames:
                    fpath = os.path.join(root, fname)
                    zipf.write(fpath)
print(f'Successfully created {out_name}')
"

echo "Created artifact zip: $OUT"
ls -lh "$OUT"
