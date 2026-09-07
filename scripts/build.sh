#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${PYTHON_BASE:?请指定已核验的官方 Python slim 镜像 tag@sha256:digest}"
: "${BUILD_ID:?请指定唯一构建编号，建议源码提交 SHA}"
: "${PLATFORM:?请指定目标平台，例如 linux/amd64；不得把本机架构当作甲方要求}"
[[ "$PYTHON_BASE" =~ @sha256:[0-9a-f]{64}$ ]] || { echo '基础镜像必须固定 digest' >&2; exit 2; }
[[ "$BUILD_ID" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || { echo '非法构建编号' >&2; exit 2; }
version=$(cat VERSION)
image="${IMAGE_REPOSITORY:-remote-sensing-framework}:${version}-${BUILD_ID}"
docker build --platform "$PLATFORM" --build-arg "PYTHON_BASE=$PYTHON_BASE" --build-arg "VERSION=$version" --build-arg "BUILD_ID=$BUILD_ID" --tag "$image" .
printf '%s\n' "$image"
