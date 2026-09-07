"""Windowed MNDWI processing for a two-band GeoTIFF."""

from pathlib import Path

import numpy as np
import rasterio


def calculate(input_path: Path, output_dir: Path, params: dict) -> dict:
    allowed = {"green_band", "swir1_band", "output_name"}
    unknown = set(params) - allowed
    if unknown:
        raise ValueError(f"MNDWI 未知参数: {', '.join(sorted(unknown))}")

    green_band = params.get("green_band", 1)
    swir1_band = params.get("swir1_band", 2)
    output_name = params.get("output_name", "mndwi.tif")
    if not isinstance(green_band, int) or isinstance(green_band, bool) or green_band < 1:
        raise ValueError("green_band 必须是从 1 开始的整数")
    if not isinstance(swir1_band, int) or isinstance(swir1_band, bool) or swir1_band < 1:
        raise ValueError("swir1_band 必须是从 1 开始的整数")
    if not isinstance(output_name, str) or Path(output_name).name != output_name:
        raise ValueError("output_name 必须是输出目录内的普通文件名")
    if not output_name.lower().endswith((".tif", ".tiff")):
        raise ValueError("output_name 必须使用 .tif 或 .tiff 扩展名")

    output_path = output_dir / output_name
    if output_path.exists():
        raise FileExistsError(f"输出已存在: {output_name}")

    with rasterio.open(input_path) as source:
        if max(green_band, swir1_band) > source.count:
            raise ValueError(
                f"输入只有 {source.count} 个波段，无法读取波段 "
                f"{green_band} 和 {swir1_band}"
            )
        profile = source.profile.copy()
        profile.update(
            driver="GTiff",
            count=1,
            dtype="float32",
            nodata=np.nan,
            compress="deflate",
            predictor=3,
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        valid_pixels = 0
        invalid_pixels = 0
        with rasterio.open(output_path, "w", **profile) as target:
            target.set_band_description(1, "MNDWI")
            target.update_tags(
                algorithm="MNDWI",
                formula="(G-S1)/(G+S1)",
                green_band=green_band,
                swir1_band=swir1_band,
            )
            for _, window in source.block_windows(green_band):
                green = source.read(green_band, window=window, masked=True).astype(
                    "float32"
                )
                swir1 = source.read(swir1_band, window=window, masked=True).astype(
                    "float32"
                )
                green_data = green.filled(np.nan)
                swir1_data = swir1.filled(np.nan)
                denominator = green_data + swir1_data
                valid = (
                    ~np.ma.getmaskarray(green)
                    & ~np.ma.getmaskarray(swir1)
                    & np.isfinite(green_data)
                    & np.isfinite(swir1_data)
                    & (denominator != 0)
                )
                result = np.full(green.shape, np.nan, dtype="float32")
                np.divide(green_data - swir1_data, denominator, out=result, where=valid)
                target.write(result, 1, window=window)
                valid_pixels += int(valid.sum())
                invalid_pixels += int(valid.size - valid.sum())

    return {
        "output": str(output_path),
        "valid_pixels": valid_pixels,
        "invalid_pixels": invalid_pixels,
        "formula": "(G-S1)/(G+S1)",
    }
