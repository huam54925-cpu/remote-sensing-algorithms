"""Offline synthetic fixture; make_blobs follows the official sklearn example."""
from pathlib import Path
import sys
import numpy as np
import rasterio
from rasterio.transform import from_origin
from sklearn.datasets import make_blobs


def create(root, side=90):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    features, truth = make_blobs(n_samples=side*side, centers=[[-8,-8],[0,8],[8,-2]],
                               cluster_std=0.25, random_state=0)
    data = features.T.reshape(2,side,side).astype('float32')
    data[:,0,0] = -9999
    with rasterio.open(root/'kmeans-input.tif', 'w', driver='GTiff', width=side, height=side,
                       count=2, dtype='float32', crs='EPSG:32650',
                       transform=from_origin(500000,4000000,20,20), nodata=-9999) as dst:
        dst.write(data)
    np.save(root/'expected-labels.npy', truth.reshape(side,side))

if __name__ == '__main__':
    create(sys.argv[1] if len(sys.argv)>1 else '/fixture', int(sys.argv[2]) if len(sys.argv)>2 else 90)
