#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${IMAGE:?请指定镜像}"
: "${PACKAGE_DIR:?请指定新的交付包目录}"
[[ ! -e "$PACKAGE_DIR" ]] || { echo '交付目录已存在' >&2; exit 2; }
mkdir -p "$PACKAGE_DIR"
PACKAGE_DIR=$(realpath "$PACKAGE_DIR")
cp -r src scripts tests configs deps "$PACKAGE_DIR/"
mkdir -p "$PACKAGE_DIR/docs" "$PACKAGE_DIR/reports" "$PACKAGE_DIR/data/input/kmeans-example" \
 "$PACKAGE_DIR/outputs" "$PACKAGE_DIR/work"
cp README.md VERSION Dockerfile Dockerfile.selftest requirements.lock .dockerignore .env.example "$PACKAGE_DIR/"
cp docs/image-selftest.md docs/deployment-guide.md docs/kubernetes-local.md docs/preparation-plan.md docs/algorithm-intake.md docs/third-party-kmeans.md docs/CHANGELOG.md "$PACKAGE_DIR/docs/"
cp -r reports/deployment "$PACKAGE_DIR/reports/"
cp data/input/smoke.txt "$PACKAGE_DIR/data/input/"
docker run --rm --network none --user "$(id -u):$(id -g)" \
 -v "$PACKAGE_DIR/data/input/kmeans-example:/fixture" -v "$PWD/tests:/tests:ro" \
 --entrypoint python "$IMAGE" /tests/create_kmeans_fixture.py /fixture
EXPORT_FILE="$PACKAGE_DIR/image.tar.gz" bash scripts/export.sh
rm "$PACKAGE_DIR/image.tar.gz.sha256"
python3 - "$PACKAGE_DIR" <<'PY'
from pathlib import Path
import hashlib,sys
root=Path(sys.argv[1])
# Bytecode is an incidental local build artifact, not part of the delivery.
for p in root.rglob('*.pyc'):p.unlink()
with (root/'SHA256SUMS').open('w') as stream:
    for p in sorted(root.rglob('*')):
        if p.is_file() and p.name!='SHA256SUMS':
            with p.open('rb') as source:
                digest=hashlib.file_digest(source,'sha256').hexdigest()
            stream.write(f'{digest}  {p.relative_to(root)}\n')
PY
printf '交付目录：%s\n' "$PACKAGE_DIR"
