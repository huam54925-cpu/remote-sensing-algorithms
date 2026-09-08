import numpy as np
import rasterio
from rasterio.transform import from_origin

with rasterio.open("/result/result/mndwi.tif") as dataset:
    result = dataset.read(1)
    expected = np.array([[0.5, 0.0, np.nan], [2 / 3, np.nan, -0.5]], dtype="float32")
    np.testing.assert_allclose(result, expected, rtol=1e-6, equal_nan=True)
    assert dataset.crs.to_epsg() == 32650
    assert dataset.transform == from_origin(500000, 4000000, 20, 20)
    assert dataset.count == 1
    assert dataset.dtypes == ("float32",)
    assert np.isnan(dataset.nodata)
    assert dataset.descriptions == ("MNDWI",)
print("MNDWI GeoTIFF values and spatial metadata verified")
