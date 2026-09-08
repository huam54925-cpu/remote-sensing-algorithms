#!/usr/bin/env python3
"""GPU scheduling, contention and actual CUDA correctness in a local kind cluster."""
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
K=os.environ.get('KUBECTL','/mnt/robot_disk/k8s/bin/kubectl')
CONFIG=os.environ.get('KUBECONFIG','/mnt/robot_disk/k8s/config/kubeconfig')
IMAGE=os.environ.get('IMAGE','remote-sensing-framework:0.3.0-kmeans1')
NS='rs-gpu-tests'
RUN=str(int(time.time()))
RECORD=ROOT/'reports/k8s-gpu'/('run-'+RUN);RECORD.mkdir(parents=True)


def k(*args):
    p=subprocess.run([K,'--kubeconfig',CONFIG,'--request-timeout=20s',*args],capture_output=True,text=True)
    if p.returncode:raise RuntimeError(p.stderr)
    return p.stdout


def save(name,value):
    (RECORD/name).write_text(value if isinstance(value,str) else json.dumps(value,indent=2))


def apply(obj):
    path=RECORD/(obj['metadata']['name']+'.json');path.write_text(json.dumps(obj,indent=2))
    k('apply','-f',str(path))


def wait_for(callback, seconds=120):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        value=callback()
        if value:return value
        time.sleep(.5)
    raise TimeoutError('Kubernetes condition timeout; inspect saved objects and events')


def pod(name,gpus,script):
    resources={'requests':{'cpu':'100m','memory':'128Mi'},'limits':{'cpu':'1','memory':'512Mi'}}
    if gpus:
        resources['requests']['nvidia.com/gpu']=gpus
        resources['limits']['nvidia.com/gpu']=gpus
    return {'apiVersion':'v1','kind':'Pod','metadata':{'name':name,'namespace':NS},'spec':{
        'restartPolicy':'Never','terminationGracePeriodSeconds':10,'activeDeadlineSeconds':240,
        'automountServiceAccountToken':False,
        'securityContext':{'runAsUser':os.getuid(),'runAsGroup':os.getgid(),'runAsNonRoot':True},
        'containers':[{'name':'compute','image':IMAGE,'imagePullPolicy':'Never',
            'command':['python','-u','-c',script],'resources':resources,
            'securityContext':{'readOnlyRootFilesystem':True,'allowPrivilegeEscalation':False,
                               'capabilities':{'drop':['ALL']},'seccompProfile':{'type':'RuntimeDefault'}},
            'volumeMounts':[{'name':'test','mountPath':'/test','readOnly':True},
                            {'name':'tmp','mountPath':'/tmp'}]}],
        'volumes':[{'name':'test','configMap':{'name':'gpu-compute-'+RUN}},
                   {'name':'tmp','emptyDir':{'medium':'Memory','sizeLimit':'64Mi'}}]}}


def read(name):
    return json.loads(k('-n',NS,'get','pod',name,'-o','json'))


def pending_gpu(name):
    obj=read(name)
    for c in obj.get('status',{}).get('conditions',[]):
        if c['type']=='PodScheduled' and c['status']=='False' and 'Insufficient nvidia.com/gpu' in c.get('message',''):
            return obj
    return None


def succeeded(name):
    obj=read(name)
    if obj.get('status',{}).get('phase')=='Failed':
        save(name+'-failed.json',obj)
        save(name+'-failed.log',k('-n',NS,'logs',name))
        raise RuntimeError(f'{name} failed')
    return obj if obj.get('status',{}).get('phase')=='Succeeded' else None


nodes=json.loads(k('get','nodes','-o','json'));save('nodes-before.json',nodes)
assert sum(int(n['status'].get('allocatable',{}).get('nvidia.com/gpu',0)) for n in nodes['items'])==1
apply({'apiVersion':'v1','kind':'Namespace','metadata':{'name':NS}})
apply({'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':'gpu-compute-'+RUN,'namespace':NS},
       'data':{'verify_cuda_compute.py':(ROOT/'tests/verify_cuda_compute.py').read_text()}})
compute="import runpy; runpy.run_path('/test/verify_cuda_compute.py',run_name='__main__')"
created=[]
try:
    # No GPU request means no injected CUDA library or device node.
    name='no-gpu-'+RUN
    apply(pod(name,0,"import os,json; assert not os.path.exists('/dev/nvidia0'); print(json.dumps({'status':'PASS','gpu_device_visible':False}))"));created.append(name)
    save('no-gpu-pod.json',wait_for(lambda:succeeded(name)))
    save('no-gpu.log',k('-n',NS,'logs',name))

    # The holder computes first, then holds its allocated K8s resource while idle.
    holder='holder-'+RUN
    hold="import signal,sys; signal.signal(signal.SIGTERM,lambda *_:sys.exit(143));"+compute+"; import time,json; print(json.dumps({'phase':'holding'}),flush=True); time.sleep(180)"
    apply(pod(holder,1,hold));created.append(holder)
    def holding():
        obj=read(holder)
        if obj.get('status',{}).get('phase')=='Failed':
            save('holder-failed.json',obj);save('holder-failed.log',k('-n',NS,'logs',holder));raise RuntimeError('Holder failed')
        if obj.get('status',{}).get('phase')=='Running':
            logs=k('-n',NS,'logs',holder)
            if '"phase": "holding"' in logs:return logs
    save('holder-compute.log',wait_for(holding))
    save('holder-running.json',read(holder))

    # A second 1-GPU Job must wait, not silently share the same GPU.
    queued='queued-'+RUN
    p=pod(queued,1,compute)
    job={'apiVersion':'batch/v1','kind':'Job','metadata':p['metadata'],
         'spec':{'backoffLimit':0,'activeDeadlineSeconds':240,'template':{'spec':p['spec']}}}
    apply(job)
    def queued_name():
        pods=json.loads(k('-n',NS,'get','pods','-l','job-name='+queued,'-o','json'))['items']
        return pods[0]['metadata']['name'] if pods else None
    qp=wait_for(queued_name)
    save('queued-pending.json',wait_for(lambda:pending_gpu(qp)))
    save('queued-events-before.txt',k('-n',NS,'describe','pod',qp))
    released=time.monotonic()
    k('-n',NS,'delete','pod',holder,'--wait=true','--timeout=30s');created.remove(holder)
    done=wait_for(lambda:succeeded(qp))
    seconds=time.monotonic()-released
    save('queued-completed.json',done)
    logs=k('-n',NS,'logs',qp);save('queued-compute.json',logs)
    result=json.loads(logs)
    assert result['status']=='PASS' and result['cpu_fallback'] is False
    assert len(result['runs'])==3 and all(x['max_absolute_error']==0 for x in result['runs'])

    # An impossible 2-GPU request must remain unscheduled even when GPU is free.
    excess='excess-'+RUN
    apply(pod(excess,2,compute));created.append(excess)
    save('excess-pending.json',wait_for(lambda:pending_gpu(excess)))
    save('excess-events.txt',k('-n',NS,'describe','pod',excess))
    # Exercise a real Job deadline, rather than just checking that a YAML field exists.
    deadline_name='deadline-'+RUN
    dp=pod(deadline_name,1,hold)
    dp['spec']['terminationGracePeriodSeconds']=5
    dj={'apiVersion':'batch/v1','kind':'Job','metadata':dp['metadata'],
        'spec':{'backoffLimit':0,'activeDeadlineSeconds':20,'template':{'spec':dp['spec']}}}
    apply(dj)
    def deadline_failed():
        obj=json.loads(k('-n',NS,'get','job',deadline_name,'-o','json'))
        if any(c.get('type')=='Failed' and c.get('status')=='True' and c.get('reason')=='DeadlineExceeded'
               for c in obj.get('status',{}).get('conditions',[])):return obj
    save('deadline-job.json',wait_for(deadline_failed,90))
    deadline_pods=json.loads(k('-n',NS,'get','pods','-l','job-name='+deadline_name,'-o','json'))
    save('deadline-pods.json',deadline_pods)
    for dpod in deadline_pods['items']:
        save('deadline-compute.log',k('-n',NS,'logs',dpod['metadata']['name']))

    save('summary.json',{'status':'PASS','allocatable_gpus':1,'gpu_correctness':True,
                        'exclusive_scheduling':True,'excess_request_unschedulable':True,
                        'no_request_no_device':True,'job_deadline_exceeded_verified':True,'release_to_completion_seconds':seconds,
                        'completed_job':queued,'records':str(RECORD)})
    print((RECORD/'summary.json').read_text())
finally:
    for name in created:
        subprocess.run([K,'--kubeconfig',CONFIG,'-n',NS,'delete','pod',name,'--ignore-not-found','--wait=true','--timeout=30s'],capture_output=True)
    save('events-final.json',k('-n',NS,'get','events','-o','json'))
