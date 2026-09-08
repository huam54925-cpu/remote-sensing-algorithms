#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec docker run --rm --init --gpus all --read-only --network none \
 --cap-drop ALL --security-opt no-new-privileges \
 --user "$(id -u):$(id -g)" --cpus 1 --memory 512m --pids-limit 64 \
 --tmpfs /tmp:rw,noexec,nosuid,size=64m \
 --mount "type=bind,src=$PWD/tests/verify_cuda_compute.py,dst=/verify_cuda_compute.py,readonly" \
 --entrypoint python "${IMAGE:-remote-sensing-framework:0.3.0-kmeans1}" /verify_cuda_compute.py
