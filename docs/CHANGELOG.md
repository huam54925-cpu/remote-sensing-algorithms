# 变更日志

## 0.2.1 — 2026-09-08

安全更新：固定 Python 3.13.15 / Debian 13.6 基础镜像摘要，升级 Expat 至 2.8.3-1~deb13u1 并保存官方安装包及 SHA-256；运行镜像移除 mount 和 pip。算法逻辑及业务依赖版本不变。本地与镜像内各 11 项 CLI 测试、容器约束和合成 GeoTIFF 回归通过。同库 Trivy HIGH/CRITICAL 从 81 条降至 50 条（47 HIGH、3 CRITICAL），安全门禁仍未通过。详见 reports/security/security-update/README.md。

## 0.2.0 — 2026-09-08

接入 MNDWI 双波段 GeoTIFF 示例，采用分块计算，保留空间信息并处理 nodata 和分母为零。加入 Rasterio/NumPy 固定版本依赖和 libexpat1 运行库；完成数值、空间信息和容器约束测试。

## 0.1.0 — 2026-09-07

首次建立容器接口框架、构建/运行/导出脚本、Kubernetes 模板、规范对照和本地接口测试。未实现遥感指数；未构建或发布容器。
