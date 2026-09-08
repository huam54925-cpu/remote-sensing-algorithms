#!/usr/bin/env python3
"""Local kind-only CDI preparation; copies the installed host driver into its node.

Does not install/change a host kernel driver. Re-run after a host driver upgrade.
The kind node's /var and writable container layer live on the data disk.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import stat

ROOT=Path(__file__).resolve().parents[1]
NODE='rs-lab-control-plane'
WORK=ROOT/'work/k8s-gpu';WORK.mkdir(parents=True,exist_ok=True)
RECORD=ROOT/'reports/k8s-gpu';RECORD.mkdir(parents=True,exist_ok=True)

def run(*args):
    return subprocess.run(args,check=True,capture_output=True,text=True).stdout

run('docker','inspect',NODE)
k=os.environ.get('KUBECTL','/mnt/robot_disk/k8s/bin/kubectl')
kubeconfig=os.environ.get('KUBECONFIG','/mnt/robot_disk/k8s/config/kubeconfig')
pods=json.loads(run(k,'--kubeconfig',kubeconfig,'get','pods','-A','-o','json'))
for pod in pods['items']:
    if pod.get('status',{}).get('phase') in ('Succeeded','Failed'):
        continue
    containers=pod['spec'].get('containers',[])+pod['spec'].get('initContainers',[])
    if any(int(c.get('resources',{}).get('limits',{}).get('nvidia.com/gpu',0))>0 for c in containers):
        raise RuntimeError('GPU Pod still active or pending; finish/cancel it before node preparation')
run(k,'--kubeconfig',kubeconfig,'-n','kube-system','delete','ds','nvidia-device-plugin','--ignore-not-found=true','--wait=true')
spec=json.loads(run('nvidia-ctk','cdi','generate','--format=json'))
# A Unix daemon socket cannot be copied to a nested kind node. CUDA compute does
# not use the host persistence-daemon RPC socket; omit just that optional mount.
mounts=spec['containerEdits']['mounts']
skipped=[m['hostPath'] for m in mounts if stat.S_ISSOCK(Path(m['hostPath']).stat().st_mode)]
spec['containerEdits']['mounts']=[m for m in mounts if m['hostPath'] not in skipped]
paths={m['hostPath'] for m in spec['containerEdits']['mounts']}
for edit in [spec['containerEdits'],*[d.get('containerEdits',{}) for d in spec['devices']]]:
    paths.update(h['path'] for h in edit.get('hooks',[]))
records=[]
for source in sorted(paths):
    path=Path(source)
    if not path.is_file():raise ValueError(f'Unsupported source: {source}')
    run('docker','exec',NODE,'mkdir','-p',str(path.parent))
    run('docker','cp','-L',source,f'{NODE}:{source}')
    with path.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    records.append({'path':source,'sha256':digest,'bytes':path.stat().st_size})
run('docker','exec',NODE,'ldconfig')
# Explicit driver root prevents regenerated CDI specs from confusing a container
# destination (e.g. /etc/vulkan) with the node's real driver source path.
run('docker','exec',NODE,'mkdir','-p','/opt/nvidia-driver/etc')
for source in sorted(paths):
    if source != '/usr/bin/nvidia-cdi-hook':
        run('docker','exec',NODE,'cp','--parents',source,'/opt/nvidia-driver')
run('docker','exec',NODE,'ldconfig','-r','/opt/nvidia-driver')
run('docker','exec',NODE,'ln','-sfn','/dev','/opt/nvidia-driver/dev')
run('docker','exec',NODE,'mkdir','-p','/etc/cdi')
local=WORK/'nvidia-kind.json';local.write_text(json.dumps(spec,indent=2))
run('docker','cp',str(local),f'{NODE}:/etc/cdi/nvidia-kind.json')
(RECORD/'driver-copy.json').write_text(json.dumps({'files':records,'omitted_sockets':skipped},indent=2))
(RECORD/'node-nvidia-smi.txt').write_text(run('docker','exec',NODE,'nvidia-smi'))
run('docker','cp','/usr/bin/nvidia-container-runtime',f'{NODE}:/usr/bin/nvidia-container-runtime')
run('docker','exec',NODE,'mkdir','-p','/etc/nvidia-container-runtime')
run('docker','cp',str(ROOT/'configs/gpu/nvidia-runtime.toml'),f'{NODE}:/etc/nvidia-container-runtime/config.toml')
config=run('docker','exec',NODE,'cat','/etc/containerd/config.toml')
marker='# Local kind: NVIDIA runtime is used only to bootstrap the device plugin.'
if marker in config:
    config=config.split(marker)[0]
elif 'runtimes.nvidia-bootstrap' in config:
    raise RuntimeError('Existing foreign nvidia-bootstrap runtime: inspect before replacing')
backup=WORK/'containerd-before-setup.toml'
if not backup.exists():backup.write_text(config)
new=WORK/'containerd-ready.toml'
new.write_text(config+'\n'+(ROOT/'configs/gpu/bootstrap-runtime.toml').read_text())
run('docker','cp',str(new),f'{NODE}:/etc/containerd/config.toml')
run('docker','exec',NODE,'systemctl','restart','containerd')
print('PASS: kind driver root, CDI and bootstrap runtime prepared')
