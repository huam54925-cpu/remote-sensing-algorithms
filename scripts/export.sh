#!/usr/bin/env bash
set -euo pipefail
: "${IMAGE:?请指定已构建镜像}"
: "${EXPORT_FILE:?请指定新导出文件路径，例如 outputs/image.tar.gz}"
[[ ! -e "$EXPORT_FILE" ]] || { echo '导出文件已存在' >&2; exit 2; }
mkdir -p "$(dirname "$EXPORT_FILE")"
tmp=$(mktemp "${EXPORT_FILE}.XXXXXX")
trap 'rm -f "$tmp"' EXIT
docker image save "$IMAGE" | gzip -n > "$tmp"
mv "$tmp" "$EXPORT_FILE"
sha256sum "$EXPORT_FILE" > "${EXPORT_FILE}.sha256"
# 此文件用于 docker load；不是安全扫描报告，也不替代甲方要求的仓库推送。
