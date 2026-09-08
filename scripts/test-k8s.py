#!/usr/bin/env python3
"""Local kind integration only; host paths are deliberately explicit."""
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
KUBECTL=os.environ.get('KUBECTL','/mnt/robot_disk/k8s/bin/kubectl')
CONFIG=os.environ.get('KUBECONFIG','/mnt/robot_disk/k8s/config/kubeconfig')
IMAGE=os.environ['IMAGE']
run_id=str(int(time.time()))
record=ROOT/'reports/deployment'/('k8s-'+run_id)
record.mkdir()

def kubectl(*args):
    p=subprocess.run([KUBECTL,'--kubeconfig',CONFIG,*args],capture_output=True,text=True)
    if p.returncode:
        raise RuntimeError(p.stderr)
    return p.stdout

def manifest(name, large=False):
    output=ROOT/'outputs'/name
    output.mkdir()
    spec={'apiVersion':'batch/v1','kind':'Job','metadata':{'name':name},'spec':{
        'backoffLimit':0,'activeDeadlineSeconds':180,'template':{'spec':{
            'restartPolicy':'Never','terminationGracePeriodSeconds':10,
            'automountServiceAccountToken':False,
            'securityContext':{'runAsUser':os.getuid(),'runAsGroup':os.getgid(),'runAsNonRoot':True},
            'containers':[{'name':'algorithm','image':IMAGE,'imagePullPolicy':'Never',
                'args':['--algorithm','KMEANS','--input','/data/input/kmeans-input.tif',
                        '--output-dir','/data/output','--params',
                        '{"clusters":64,"max_iter":10000}' if large else '{"clusters":3}'],
                'resources':{'requests':{'cpu':'250m','memory':'256Mi'},
                             'limits':{'cpu':'1','memory':'1Gi'}},
                'securityContext':{'allowPrivilegeEscalation':False,'readOnlyRootFilesystem':True,
                                   'capabilities':{'drop':['ALL']},'seccompProfile':{'type':'RuntimeDefault'}},
                'volumeMounts':[{'name':'input','mountPath':'/data/input','readOnly':True},
                                {'name':'output','mountPath':'/data/output'},
                                {'name':'tmp','mountPath':'/tmp'}]}],
            'volumes':[{'name':'input','hostPath':{'path':'/rs-input/'+('kmeans-large' if large else 'kmeans-example'),'type':'Directory'}},
                       {'name':'output','hostPath':{'path':'/rs-output/'+name,'type':'Directory'}},
                       {'name':'tmp','emptyDir':{'medium':'Memory','sizeLimit':'64Mi'}}]}}}}
    path=record/(name+'.json');path.write_text(json.dumps(spec,indent=2))
    return path,output

(record/'nodes.txt').write_text(kubectl('get','nodes','-o','wide'))
# Two separate Jobs, each with its own output, exercise concurrent scheduling.
jobs=[]
for i in range(2):
    name=f'rs-example-{run_id}-{i}'
    path,out=manifest(name)
    kubectl('apply','-f',str(path));jobs.append((name,out))
for name,out in jobs:
    kubectl('wait','--for=condition=complete','job/'+name,'--timeout=180s')
    logs=kubectl('logs','job/'+name)
    (record/(name+'.jsonl')).write_text(logs)
    assert json.loads((out/'result/success.json').read_text())['status']=='completed'
# Suspend the Job so its controller does not recreate a cancelled Pod.
name=f'rs-cancel-{run_id}'
path,out=manifest(name,True)
kubectl('apply','-f',str(path))
deadline=time.monotonic()+90
while not list(out.glob('.partial-*')):
    if time.monotonic()>deadline:
        raise RuntimeError('K8s cancellation workload failed to start')
    time.sleep(.2)
kubectl('patch','job',name,'--type=merge','-p','{"spec":{"suspend":true}}')
deadline=time.monotonic()+30
while json.loads(kubectl('get','pods','-l','job-name='+name,'-o','json'))['items']:
    if time.monotonic()>deadline:
        raise RuntimeError('Suspended job Pods still exist')
    time.sleep(.2)
assert not (out/'result').exists()
assert not list(out.glob('.partial-*'))
assert not (out/'.rs-lock').exists()
(record/'cancel-job.json').write_text(kubectl('get','job',name,'-o','json'))
(record/'pods.json').write_text(kubectl('get','pods','-o','json'))
print(json.dumps({'status':'PASS','records':str(record),'jobs':[x[0] for x in jobs],'cancelled':name}))
