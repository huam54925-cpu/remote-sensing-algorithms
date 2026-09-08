#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
node=rs-lab-control-plane
index=nvcr.io/nvidia/k8s-device-plugin@sha256:a61ba9fd8efb82f3a79f877f7580e02c1e8e7593f62473644bc9c79e315c3312
tag=nvcr.io/nvidia/k8s-device-plugin:v0.20.0
amd64=nvcr.io/nvidia/k8s-device-plugin@sha256:1de09dda8d1c179fe84e280f28a48a75c9a1a529d90eefcee1f80c012ac11640
k=${KUBECTL:-/mnt/robot_disk/k8s/bin/kubectl}
config=${KUBECONFIG:-/mnt/robot_disk/k8s/config/kubeconfig}
if ! docker image inspect "$index" >/dev/null 2>&1; then
  docker pull --platform linux/amd64 "$index"
fi
docker tag "$index" "$tag"
# Avoid kind --all-platforms import on a Docker store containing only amd64.
docker image save --platform linux/amd64 "$tag" | \
  docker exec -i "$node" ctr -n k8s.io images import --platform linux/amd64 --digests -
docker exec "$node" ctr -n k8s.io images tag --force "$tag" "$amd64"
"$k" --kubeconfig "$config" apply -f configs/gpu/runtime-class.json -f configs/gpu/device-plugin.json
"$k" --kubeconfig "$config" -n kube-system rollout status ds/nvidia-device-plugin --timeout=120s
python3 - "$k" "$config" <<'PY'
import json,subprocess,sys,time
for _ in range(60):
    node=json.loads(subprocess.check_output([sys.argv[1],'--kubeconfig',sys.argv[2],
        '--request-timeout=10s','get','node','rs-lab-control-plane','-o','json']))
    if int(node['status']['allocatable'].get('nvidia.com/gpu',0))==1:
        print('PASS: nvidia.com/gpu=1');break
    time.sleep(1)
else:raise SystemExit('GPU resource missing; inspect device-plugin logs')
PY
