#!/usr/bin/env bash
set -euo pipefail
# This local environment is deliberately pinned to the user's ext4 data disk.
root=/mnt/robot_disk/k8s
project=$(cd "$(dirname "$0")/.." && pwd)
mountpoint -q /mnt/robot_disk || { echo '数据盘未挂载' >&2; exit 2; }
[[ $(docker info --format '{{.DockerRootDir}}') == /mnt/robot_disk/* ]] || {
 echo 'Docker 数据目录不在指定数据盘；请先配置存储' >&2; exit 2;
}
clusters=$("$root/bin/kind" get clusters)
while IFS= read -r existing; do
  [[ "$existing" != rs-lab ]] || { echo 'rs-lab 已存在；保留当前集群和配置' >&2; exit 2; }
done <<< "$clusters"
mkdir -p "$root/config" "$root/cache" "$project/data/input" "$project/outputs"
export TMPDIR="$root/cache"
# Python JSON output is also valid YAML and correctly escapes unusual paths.
python3 - "$project" "$root/config/kind.yaml" <<'PY'
import json,sys
from pathlib import Path
project=Path(sys.argv[1])
config={'kind':'Cluster','apiVersion':'kind.x-k8s.io/v1alpha4',
 'networking':{'apiServerAddress':'127.0.0.1'},'nodes':[{'role':'control-plane',
 'image':'kindest/node:v1.36.4@sha256:099e049362a1526b2db71494e1947aae99bd16290d7c895f2b7ea312e3cbfaed',
 'extraMounts':[{'hostPath':str(project/'data/input'),'containerPath':'/rs-input','readOnly':True},
                {'hostPath':str(project/'outputs'),'containerPath':'/rs-output'}]}]}
Path(sys.argv[2]).write_text(json.dumps(config,indent=2))
PY
"$root/bin/kind" create cluster --name rs-lab --config "$root/config/kind.yaml" \
 --kubeconfig "$root/config/kubeconfig" --wait 120s
