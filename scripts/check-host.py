#!/usr/bin/env python3
"""Run on the HOST with Python stdlib; never mount the Docker socket in a container."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description='Host installation inventory and image self-test')
p.add_argument('image', help='Prefer a ghcr.io image pinned to @sha256:...')
p.add_argument('--output-dir', default='rs-reports')
a = p.parse_args()
parent = Path(a.output_dir).resolve()
parent.mkdir(parents=True, exist_ok=True)
root = Path(tempfile.mkdtemp(prefix='machine-', dir=parent))
root.chmod(0o755)
report = {'schema_version': 1, 'status': 'FAIL', 'image_requested': a.image,
          'time': datetime.now(timezone.utc).isoformat(), 'system': platform.system(),
          'architecture': platform.machine(), 'kernel': platform.release(),
          'hostname': platform.node(), 'cpu_count': os.cpu_count(), 'commands': {},
          'scope': 'Host inventory plus synthetic CPU image checks; not hardware health or production certification.'}
for source, key in [('/etc/os-release','os_release'),('/proc/meminfo','memory'),('/proc/loadavg','load')]:
    try: report[key] = Path(source).read_text()
    except OSError: report[key] = 'unavailable'
usage = shutil.disk_usage(root)
report['report_disk_bytes'] = dict(total=usage.total, used=usage.used, free=usage.free)

def command(key, args):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=30)
        value = {'exit_code': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr}
    except (OSError, subprocess.TimeoutExpired) as exc:
        value = {'exit_code': None, 'error': str(exc)}
    report['commands'][key] = value
    return value

def save():
    (root/'host-report.json').write_text(json.dumps(report, indent=2) + '\n')

code = 1
try:
    command('mounts', ['findmnt','-rn','-o','TARGET,SOURCE,FSTYPE,OPTIONS'])
    command('cloud_init', ['cloud-init','status'])
    report['reboot_required'] = Path('/var/run/reboot-required').exists()
    docker = command('docker_version', ['docker','version','--format','{{json .}}'])
    if docker['exit_code'] != 0:
        raise RuntimeError('Docker unavailable; see host-report.json')
    inspect = command('image', ['docker','image','inspect',a.image,'--format',
        '{"id":{{json .Id}},"digests":{{json .RepoDigests}},"os":{{json .Os}},"architecture":{{json .Architecture}}}'])
    if inspect['exit_code'] != 0:
        raise RuntimeError('Image unavailable; run docker pull first')
    image = json.loads(inspect['stdout'])
    if platform.system() != 'Linux' or platform.machine() != 'x86_64' or image['architecture'] != 'amd64':
        raise RuntimeError('This test requires native Linux amd64')
    uid = os.getuid() or 10001
    gid = os.getgid() if os.getuid() else 10001
    output = root/'container'; output.mkdir(mode=0o755)
    if os.getuid() == 0: os.chown(output, uid, gid)
    # Pin the run to the image ID inspected above, even if a mutable tag changes.
    cmd = ['docker','run','--rm','--network','none','--read-only','--cap-drop','ALL',
           '--security-opt','no-new-privileges','--cpus','1','--memory','1g','--pids-limit','128',
           '--user',f'{uid}:{gid}','--tmpfs','/tmp:rw,noexec,nosuid,size=128m',
           '--mount',f'type=bind,src={output},dst=/reports',image['id'],
           '--self-test','--report-dir','/reports']
    report['test_command'] = cmd
    save()
    with (root/'selftest.log').open('w') as log:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            print(line, end='', flush=True); log.write(line); log.flush()
        code = process.wait()
    report['test_exit_code'] = code
    report['status'] = 'PASS' if code == 0 else 'FAIL'
except Exception as exc:
    report['error'] = f'{type(exc).__name__}: {exc}'
    print(report['error'], file=sys.stderr)
finally:
    save()
    (root/'SUMMARY.md').write_text(f"# Machine test: {report['status']}\n\n"
        f"Image: {a.image}\n\nHost inventory: host-report.json\n\n"
        'Execution log: selftest.log\n\nAlgorithm reports, fixtures and results: container/selftest-*/\n\n'
        + report['scope'] + '\n')
    print(f"{report['status']}: MACHINE TEST; reports={root}")
sys.exit(code)
