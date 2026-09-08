"""Bounded, CPU-only GeoTIFF adaptation of scikit-learn's K-Means example.

Reference: https://scikit-learn.org/stable/auto_examples/cluster/plot_mini_batch_kmeans.html
Cluster IDs are arbitrary categories, not land-cover semantic classes.
"""
from pathlib import Path
import numpy as np
import rasterio
from sklearn.cluster import KMeans
from threadpoolctl import threadpool_limits


def calculate(input_path: Path, output_dir: Path, params: dict) -> dict:
    unknown = set(params) - {"clusters", "seed", "max_iter", "max_pixels"}
    if unknown:
        raise ValueError(f"KMEANS 未知参数: {', '.join(sorted(unknown))}")
    values = {}
    for name, default, low, high in [("clusters", 3, 2, 255), ("seed", 0, 0, 2**32-1),
                                      ("max_iter", 100, 1, 10000),
                                      ("max_pixels", 1000000, 1, 10000000)]:
        v = params.get(name, default)
        if isinstance(v, bool) or not isinstance(v, int) or not low <= v <= high:
            raise ValueError(f"{name} 必须是 {low}..{high} 的整数")
        values[name] = v
    with rasterio.open(input_path) as src:
        if src.width * src.height > values['max_pixels'] or src.count > 32:
            raise ValueError("示例限制：像元数超出 max_pixels 或超过 32 波段；大影像须另做分块适配")
        data = src.read(masked=True).astype('float32')
        valid = (~np.ma.getmaskarray(data).any(axis=0)
                 & np.isfinite(data.filled(np.nan)).all(axis=0))
        samples = data.data[:, valid].T.copy()
        if len(samples) < values['clusters']:
            raise ValueError("有效像元数小于 clusters")
        if len(np.unique(samples, axis=0)) < values['clusters']:
            raise ValueError("不同像元值的数量小于 clusters")
        with threadpool_limits(limits=1):
            model = KMeans(n_clusters=values['clusters'], random_state=values['seed'],
                           n_init=10, max_iter=values['max_iter'], algorithm='lloyd')
            labels = model.fit_predict(samples)
        result = np.zeros(valid.shape, dtype='uint16')
        result[valid] = labels + 1
        profile = src.profile.copy()
        profile.update(driver='GTiff', count=1, dtype='uint16', nodata=0, compress='deflate', predictor=1)
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / 'clusters.tif'
        with rasterio.open(output, 'w', **profile) as dst:
            dst.write(result, 1)
            dst.update_tags(algorithm='KMEANS', seed=values['seed'], clusters=values['clusters'])
    return {'output': str(output), 'valid_pixels': int(valid.sum()),
            'invalid_pixels': int(valid.size-valid.sum()), 'device': 'cpu',
            'iterations': int(model.n_iter_), 'inertia': float(model.inertia_),
            'centers': model.cluster_centers_.tolist(), 'parameters': values}
