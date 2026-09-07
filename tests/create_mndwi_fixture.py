from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

output = Path("/fixture/mndwi-input.tif")
green = np.array([[3000, 2000, 0], [5000, -9999, 1000]], dtype="int16")
swir1 = np.array([[1000, 2000, 0], [1000, 2000, 3000]], dtype="int16")

with rasterio.open(
    output,
    "w",
    driver="GTiff",
    width=3,
    height=2,
    count=2,
    dtype="int16",
    crs="EPSG:32650",
    transform=from_origin(500000, 4000000, 20, 20),
    nodata=-9999,
) as dataset:
    dataset.write(green, 1)
    dataset.write(swir1, 2)
    dataset.set_band_description(1, "green")
    dataset.set_band_description(2, "swir1")
