"""Offline synthetic acceptance checks with durable, machine-readable evidence."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from . import __version__


def require(value, message):
    if not value:
        raise RuntimeError(message)


def run(report_dir):
    started = time.monotonic()
    root = Path(report_dir).resolve()
    try:
        root.mkdir(parents=True, exist_ok=True)
        # Never overwrite a previous report, even when rerunning the same command.
        root = Path(__import__('tempfile').mkdtemp(prefix='selftest-', dir=root))
    except OSError as exc:
        print(f'FAIL: report directory is not writable: {exc}', file=sys.stderr)
        return 4
    report = {
        'schema_version': 1, 'status': 'FAIL', 'version': __version__,
        'started_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'Synthetic CPU checks; not real satellite accuracy, GPU or production certification.',
        'environment_scope': 'Container view; kernel is shared with host. Host details require check-host.sh.',
        'environment': {'system': platform.system(), 'kernel': platform.release(),
                        'architecture': platform.machine(), 'python': platform.python_version(),
                        'uid': os.getuid(), 'cpu_count_visible': os.cpu_count()},
        'checks': [],
    }
    for name in ('cpu.max', 'memory.max', 'pids.max'):
        path = Path('/sys/fs/cgroup') / name
        report['environment'][name] = path.read_text().strip() if path.exists() else 'unavailable'
    for name in ('numpy', 'rasterio', 'scikit-learn'):
        try:
            report['environment'][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            report['environment'][name] = 'missing'

    def check(name, fn):
        before = time.monotonic()
        try:
            details = fn()
            item = {'name': name, 'status': 'PASS', 'details': details}
        except Exception as exc:
            item = {'name': name, 'status': 'FAIL', 'error': f'{type(exc).__name__}: {exc}'}
        item['elapsed_seconds'] = round(time.monotonic() - before, 4)
        report['checks'].append(item)
        print(f"{item['status']}: {name}", flush=True)

    def cli(algorithm, source, output, expected=0):
        args = [sys.executable, '-m', 'rs_container', '--algorithm', algorithm,
                '--input', str(source), '--output-dir', str(output)]
        p = subprocess.run(args, capture_output=True, text=True, timeout=120)
        with (root / 'commands.jsonl').open('a') as stream:
            stream.write(json.dumps({'argv': args, 'exit_code': p.returncode,
                                     'stdout': p.stdout, 'stderr': p.stderr}) + '\n')
        require(p.returncode == expected, f'expected exit {expected}, got {p.returncode}: {p.stderr}')
        return output / 'result'

    def smoke():
        source = root / 'smoke.txt'
        source.write_bytes(b'remote machine test\n')
        cli('smoke', source, root / 'smoke-output')
        result = json.loads((root / 'smoke-output/smoke-result.json').read_text())
        require(result['bytes'] == source.stat().st_size, 'byte count mismatch')
        require(result['sha256'] == hashlib.sha256(source.read_bytes()).hexdigest(), 'SHA256 mismatch')
        return {'bytes': result['bytes'], 'sha256': result['sha256']}

    def fixture(name, data, nodata=None):
        import rasterio
        from rasterio.transform import from_origin
        path = root / name
        with rasterio.open(path, 'w', driver='GTiff', height=data.shape[1],
                           width=data.shape[2], count=data.shape[0], dtype='float32',
                           crs='EPSG:32650', transform=from_origin(500000,4000000,20,20),
                           nodata=nodata) as ds:
            ds.write(data.astype('float32'))
        return path

    def metadata(ds, source):
        import rasterio
        with rasterio.open(source) as src:
            require(ds.crs == src.crs and ds.transform == src.transform, 'spatial metadata mismatch')
            require(ds.width == src.width and ds.height == src.height and ds.count == 1, 'shape mismatch')

    def success(result):
        manifest = json.loads((result / 'success.json').read_text())
        require(manifest['status'] == 'completed', 'missing completed status')
        return manifest

    def kmeans():
        import numpy as np
        import rasterio
        from sklearn.datasets import make_blobs
        from sklearn.cluster import KMeans
        from sklearn.metrics import adjusted_rand_score
        from threadpoolctl import threadpool_limits
        x, truth = make_blobs(n_samples=900, centers=[[-8,-8],[0,8],[8,-2]],
                             cluster_std=0.25, random_state=0)
        data = x.T.reshape(2,30,30).astype('float32')
        data[:,0,0] = -9999
        source = fixture('kmeans-input.tif', data, -9999)
        np.save(root / 'kmeans-truth.npy', truth.reshape(30,30))
        result = cli('KMEANS', source, root / 'kmeans-output')
        manifest = success(result)
        with rasterio.open(result / 'clusters.tif') as ds:
            labels = ds.read(1)
            score = adjusted_rand_score(truth[1:], labels.ravel()[1:])
            with threadpool_limits(limits=1):
                baseline = KMeans(n_clusters=3, random_state=0, n_init=10,
                                  max_iter=100, algorithm='lloyd').fit_predict(data.reshape(2,-1)[:,1:].T.copy())
            reference_score = adjusted_rand_score(baseline, labels.ravel()[1:])
            require(score == 1.0 and reference_score == 1.0, 'clustering mismatch')
            require(labels[0,0] == 0 and ds.nodata == 0, 'NoData mismatch')
            require(ds.dtypes == ('uint16',), 'dtype mismatch')
            metadata(ds, source)
        require(manifest['valid_pixels'] == 899 and manifest['invalid_pixels'] == 1, 'pixel count mismatch')
        before = hashlib.sha256((result / 'clusters.tif').read_bytes()).hexdigest()
        cli('KMEANS', source, root / 'kmeans-output', expected=5)
        require(before == hashlib.sha256((result / 'clusters.tif').read_bytes()).hexdigest(), 'existing result changed')
        return {'truth_ari': score, 'reference_ari': reference_score, 'valid_pixels': 899,
                'invalid_pixels': 1, 'overwrite_rejected': True}

    def mndwi():
        import numpy as np
        import rasterio
        source = fixture('mndwi-input.tif', np.array([[[3,1,0]],[[1,3,0]]]))
        result = cli('MNDWI', source, root / 'mndwi-output')
        success(result)
        with rasterio.open(result / 'mndwi.tif') as ds:
            np.testing.assert_allclose(ds.read(1), [[0.5,-0.5,np.nan]], equal_nan=True)
            require(ds.dtypes == ('float32',) and np.isnan(ds.nodata), 'dtype/NoData mismatch')
            metadata(ds, source)
        return {'expected_values': [0.5, -0.5, 'NaN'], 'spatial_metadata': 'PASS'}

    def missing_input():
        cli('MNDWI', root / 'missing.tif', root / 'missing-output', expected=4)
        require(not (root / 'missing-output/result').exists(), 'unexpected result')
        return {'expected_exit_code': 4}

    for name, fn in [('smoke', smoke), ('KMEANS', kmeans), ('MNDWI', mndwi), ('missing_input', missing_input)]:
        check(name, fn)
    report['status'] = 'PASS' if all(c['status'] == 'PASS' for c in report['checks']) else 'FAIL'
    report['elapsed_seconds'] = round(time.monotonic() - started, 4)
    (root / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    lines = [f"# Image self-test: {report['status']}", '', report['scope'], '',
             '| Check | Result |', '|---|---|']
    lines += [f"| {c['name']} | {c['status']} |" for c in report['checks']]
    lines += ['', 'See report.json for environment and details; commands.jsonl for execution logs.',
              'Input GeoTIFFs, clustering truth and output results are retained in this directory.']
    (root / 'report.md').write_text('\n'.join(lines) + '\n')
    with (root / 'SHA256SUMS').open('w') as stream:
        for path in sorted(root.rglob('*')):
            if path.is_file() and path.name != 'SHA256SUMS':
                stream.write(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + str(path.relative_to(root)) + '\n')
    print(f"{report['status']}: ALL ALGORITHM CHECKS; report={root}", flush=True)
    return 0 if report['status'] == 'PASS' else 1
