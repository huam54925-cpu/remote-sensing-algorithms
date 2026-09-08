"""Host-side integration checks, using an already built image with no network."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
IMAGE=os.environ['IMAGE']
RECORD=Path(tempfile.mkdtemp(prefix='deployment-',dir=ROOT/'outputs'))

def run(args, expected=0, **kwargs):
    p=subprocess.run(args,capture_output=True,text=True,**kwargs)
    if p.returncode != expected:
        raise AssertionError(f'{args}: expected {expected}, got {p.returncode}\n{p.stderr}')
    return p

def docker_base(name, inp, out):
    return ['docker','run','--name',name,'--init','--read-only','--network','none',
            '--cap-drop','ALL','--security-opt','no-new-privileges',
            '--user',f'{os.getuid()}:{os.getgid()}','--memory','1g','--cpus','1',
            '--pids-limit','128','--tmpfs','/tmp:rw,noexec,nosuid,size=64m',
            '--mount',f'type=bind,src={inp},dst=/data/input,readonly',
            '--mount',f'type=bind,src={out},dst=/data/output']

# Image-side tests include independent sklearn result and spatial metadata checks.
p=run(['docker','run','--rm','--network','none','--read-only','--tmpfs','/tmp:size=128m',
       '--mount',f'type=bind,src={ROOT}/tests,dst=/tests,readonly','--entrypoint','python',IMAGE,
       '-m','unittest','discover','-s','/tests','-v'])
(RECORD/'algorithm-tests.txt').write_text(p.stdout+p.stderr)

inp=RECORD/'中文 输入';inp.mkdir()
run(['docker','run','--rm','--network','none','--user',f'{os.getuid()}:{os.getgid()}',
     '-v',f'{inp}:/fixture','-v',f'{ROOT}/tests:/tests:ro','--entrypoint','python',IMAGE,
     '/tests/create_kmeans_fixture.py','/fixture'])
out=RECORD/'中文 输出'
work=RECORD/'中文 工作'
env_file=RECORD/'test.env'
env_file.write_text(f'IMAGE={IMAGE}\nINPUT_DIR={inp}\nOUTPUT_DIR={out}\nWORK_DIR={work}\n'
                    'RS_ALGORITHM=KMEANS\nRS_INPUT=/data/input/kmeans-input.tif\n'
                    'RS_PARAMS={"clusters":3,"seed":0}\nMEMORY_LIMIT=1g\n')
p=run(['python3',str(ROOT/'scripts/env-run.py'),str(env_file)])
(RECORD/'success.jsonl').write_text(p.stderr)
assert (out/'result/success.json').exists()
for line in p.stderr.splitlines(): json.loads(line)
run(['python3',str(ROOT/'scripts/env-run.py'),str(env_file)],expected=5)
run(['python3',str(ROOT/'scripts/env-run.py'),str(env_file),'--input','/data/input/missing'],expected=4)

# Denied output permission: run as the ordinary mapped user, not root.
readonly=RECORD/'readonly';readonly.mkdir();readonly.chmod(0o555)
name=f'rs-permission-{os.getpid()}'
try:
    p=run(docker_base(name,inp,readonly)+[IMAGE,'--algorithm','KMEANS','--input',
          '/data/input/kmeans-input.tif','--output-dir','/data/output'],expected=4)
    (RECORD/'permission.jsonl').write_text(p.stderr)
finally:
    subprocess.run(['docker','rm','-f',name],capture_output=True)
    readonly.chmod(0o755)

# Deterministic resource exhaustion confined to a small diagnostic container.
name=f'rs-oom-{os.getpid()}'
try:
    run(docker_base(name,inp,readonly)+['--memory','32m','--memory-swap','32m',
        '--entrypoint','python',IMAGE,'-c','x=bytearray(256*1024*1024)'],expected=137)
    state=json.loads(run(['docker','inspect',name,'--format','{{json .State}}']).stdout)
    assert state['OOMKilled'], state
    (RECORD/'oom-state.json').write_text(json.dumps(state,indent=2))
finally:
    subprocess.run(['docker','rm','-f',name],capture_output=True)

# A real, long KMeans workload. Wait for work to begin, then exercise docker stop.
large=RECORD/'large';large.mkdir()
run(['docker','run','--rm','--network','none','--user',f'{os.getuid()}:{os.getgid()}',
     '-v',f'{large}:/fixture','-v',f'{ROOT}/tests:/tests:ro','--entrypoint','python',IMAGE,
     '/tests/create_kmeans_fixture.py','/fixture','1000'])
cancelled=RECORD/'cancelled';cancelled.mkdir()
name=f'rs-cancel-{os.getpid()}'
logfile=(RECORD/'cancel.jsonl').open('w')
p=subprocess.Popen(docker_base(name,large,cancelled)+[IMAGE,'--algorithm','KMEANS',
    '--input','/data/input/kmeans-input.tif','--output-dir','/data/output',
    '--params','{"clusters":64,"max_iter":10000}'],stdout=logfile,stderr=logfile)
try:
    deadline=time.monotonic()+60
    while not list(cancelled.glob('.partial-*')):
        if p.poll() is not None or time.monotonic()>deadline:
            raise AssertionError('Cancellation workload did not start')
        time.sleep(0.1)
    time.sleep(1)
    started=time.monotonic()
    run(['bash',str(ROOT/'scripts/stop.sh'),name,'10'])
    code=p.wait(timeout=20)
    elapsed=time.monotonic()-started
    state=json.loads(run(['docker','inspect',name,'--format','{{json .State}}']).stdout)
    assert code == 143, (code,state)
    assert not (cancelled/'result').exists()
    assert not list(cancelled.glob('.partial-*'))
    assert not (cancelled/'.rs-lock').exists()
    (RECORD/'stop-result.json').write_text(json.dumps({'exit_code':code,'seconds':elapsed,
                                                   'state':state},indent=2))
finally:
    subprocess.run(['docker','rm','-f',name],capture_output=True)
    p.wait(timeout=20)
    logfile.close()
# Same output can be retried after cooperative cancellation.
retry={**os.environ,'IMAGE':IMAGE,'INPUT_DIR':str(inp),'OUTPUT_DIR':str(cancelled),
       'RS_ALGORITHM':'KMEANS','RS_INPUT':'/data/input/kmeans-input.tif','MEMORY_LIMIT':'1g'}
run(['bash',str(ROOT/'scripts/run.sh')],env=retry)
print(json.dumps({'status':'PASS','records':str(RECORD)},ensure_ascii=False))
