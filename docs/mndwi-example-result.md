# MNDWI 示例封装记录（2026-09-08）

## 来源

- 参考实现：spyndex 0.12.0，MIT License。
- Git 提交：`3158e588fc9db707533363988d51f36cef5b6344`。
- 本地源码：`sources/spyndex-0.12.0`，保留完整 LICENSE。
- 标准公式：`(G - S1) / (G + S1)`；参考文献 DOI：10.1080/01431160600589179。
- Spyndex 容器交叉检查结果：输入 `[G: 0.3, 0.2, 0.0]`、`[S1: 0.1, 0.2, 0.0]` 得到 `[0.5, 0.0, NaN]`，通过独立期望值检查。

## 镜像

- 标签：`remote-sensing-framework:0.2.0-mndwi3`
- 本地镜像 ID：`sha256:edac1a22f20b1e349f3c0a19e7e6ddb6e5dc8e5f08c158e015d5f466314e3bdf`
- Docker inspect 大小：105,331,824 bytes（约 100.45 MiB）
- 基础镜像：`python@sha256:20080e807bfc404f8450b185cf0fc95d553462673598549613735f70a5b4d5d0`
- Python 依赖：Rasterio 1.5.1、NumPy 2.5.3 及 requirements.lock 中固定的直接/间接依赖。
- 系统依赖：libexpat1 2.5.0-1+deb12u3。

## 测试输入与输出

输入为 3×2 像元、2 波段的人工 GeoTIFF；波段 1 是 Green，波段 2 是 SWIR1。它用于可复现的数值和边界测试，不是真实卫星数据。

- 输入：`data/input/mndwi-example/mndwi-input.tif`
- 输入 SHA-256：`5402538d3a8955a4917e74303a4956978298cfeed04914c1ab9e5e6282b55009`
- 输出：`outputs/mndwi-example-001/mndwi.tif`
- 输出 SHA-256：`c97da791ed6a192d6a2581336afdcd8c395d519be457e201f94c46b2af9d19ec`
- 输出数值：`[[0.5, 0.0, NaN], [0.6666667, NaN, -0.5]]`
- 有效像元：4；无效像元：2（分母为零或输入 nodata）。
- CRS：EPSG:32650；像元大小、仿射变换、范围均与输入一致。
- 输出类型：单波段 float32 GeoTIFF，nodata 为 NaN，DEFLATE 压缩。
- 容器日志耗时：1.838 秒；进程峰值 RSS：75,920 KiB。该结果来自极小测试文件，不作为真实影像性能基准。

## 容器约束验证

只读根文件系统、只读输入挂载、可写输出和 `/tmp`、默认非 root 用户 10001、禁网、移除全部 capabilities、禁止权限提升均通过。框架测试记录目录：`outputs/container-test.8FXVxl`。

下一步仍需使用真实 Sentinel-2 地表反射率影像验证。Sentinel-2 B03 是 Green，B11 是 SWIR1，二者原始空间分辨率不同，必须明确重采样或预处理规则后才能作为正式案例。
