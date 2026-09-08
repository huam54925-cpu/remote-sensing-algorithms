#!/usr/bin/env bash
set -uo pipefail
status=0
uname -sm
for tool in docker python3 sha256sum gzip; do
  command -v "$tool" || status=1
done
docker version --format '{{.Server.Version}}' || status=1
docker info --format 'DockerRootDir={{.DockerRootDir}}' || status=1
df -h "${1:-.}"
if command -v nvidia-smi >/dev/null; then
  nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
fi
if command -v nvidia-container-cli >/dev/null; then
  nvidia-container-cli --version
else
  echo 'GPU_CHECK=NOT_READY: 未找到 NVIDIA Container Toolkit；CPU 示例不受影响'
fi
printf 'CPU_PREREQUISITE_EXIT=%s\n' "$status"
exit "$status"
