#!/usr/bin/env bash
set -euo pipefail
: "${1:?用法：bash scripts/stop.sh 容器名 [宽限秒数]}"
[[ "${2:-10}" =~ ^[0-9]+$ ]] || { echo '宽限时间必须是非负整数' >&2; exit 2; }
docker stop --timeout "${2:-10}" "$1"
