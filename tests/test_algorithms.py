import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

try:
    import numpy as np
    import rasterio
    from sklearn.cluster import KMeans
    from sklearn.metrics import adjusted_rand_score
    from threadpoolctl import threadpool_limits
    from create_kmeans_fixture import create
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

@unittest.skipUnless(HAS_DEPS, '完整算法测试须在构建镜像中执行')
class AlgorithmTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        create(self.root)
        self.src = self.root/'kmeans-input.tif'
        self.out = self.root/'out'

    def run_cli(self, params='{}', out=None):
        return subprocess.run([sys.executable, '-m', 'rs_container', '--algorithm', 'KMEANS',
            '--input', str(self.src), '--output-dir', str(out or self.out), '--params', params],
            capture_output=True, text=True)

    def test_reference_and_metadata(self):
        p = self.run_cli()
        self.assertEqual(p.returncode, 0, p.stderr)
        with rasterio.open(self.src) as src, rasterio.open(self.out/'result/clusters.tif') as dst:
            features = src.read().reshape(2,-1)[:,1:].T.copy()
            with threadpool_limits(limits=1):
                baseline = KMeans(n_clusters=3, random_state=0, n_init=10, max_iter=100,
                                  algorithm='lloyd').fit_predict(features)
            result = dst.read(1)
            self.assertEqual(adjusted_rand_score(baseline,result.ravel()[1:]),1.0)
            truth = np.load(self.root/'expected-labels.npy').ravel()[1:]
            self.assertEqual(adjusted_rand_score(truth,result.ravel()[1:]),1.0)
            self.assertEqual(dst.crs,src.crs)
            self.assertEqual(dst.transform,src.transform)
            self.assertEqual(dst.nodata,0)
            self.assertEqual(result[0,0],0)
            self.assertEqual(dst.dtypes,('uint16',))
        success=json.loads((self.out/'result/success.json').read_text())
        self.assertEqual(success['valid_pixels'],8099)
        self.assertEqual(success['status'],'completed')
        self.assertEqual(success['device'],'cpu')
        original=(self.out/'result/clusters.tif').read_bytes()
        self.assertEqual(self.run_cli().returncode,5)
        self.assertEqual((self.out/'result/clusters.tif').read_bytes(),original)

    def test_validation_and_no_partial_result(self):
        for params in ('{"clusters":true}', '{"clusters":1}', '{"max_pixels":10}', '{"unexpected":1}'):
            p=self.run_cli(params)
            self.assertEqual(p.returncode,2,p.stderr)
            self.assertFalse((self.out/'result').exists())
            self.assertFalse(list(self.out.glob('.partial-*')))
            self.assertFalse((self.out/'.rs-lock').exists())

    def test_mndwi_values(self):
        from rasterio.transform import from_origin
        with rasterio.open(self.src,'w',driver='GTiff',width=3,height=1,count=2,dtype='float32',
                           crs='EPSG:32650',transform=from_origin(1,1,20,20)) as dst:
            dst.write(np.array([[[3,1,0]],[[1,3,0]]],dtype='float32'))
        p=subprocess.run([sys.executable,'-m','rs_container','--algorithm','MNDWI',
            '--input',str(self.src),'--output-dir',str(self.out)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        with rasterio.open(self.out/'result/mndwi.tif') as dst:
            np.testing.assert_allclose(dst.read(1),[[0.5,-0.5,np.nan]],equal_nan=True)
