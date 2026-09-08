#!/usr/bin/env bash
set -euo pipefail
: "${IMAGE:?请指定镜像}"
: "${TRIVY:?请指定已安装且核验过的 Trivy 路径}"
: "${SCAN_DIR:?请指定扫描输出目录}"
mkdir -p "$SCAN_DIR"
"$TRIVY" --version > "$SCAN_DIR/tool-version.txt"
# 默认尝试更新数据库。显式 TRIVY_SKIP_DB_UPDATE=true 可复用已有库，必须在报告说明库时间。
"$TRIVY" image --scanners vuln --format json --output "$SCAN_DIR/scan.json" \
  --severity HIGH,CRITICAL --exit-code 2 "$IMAGE"
