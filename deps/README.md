# 系统依赖锁定（2026-09-08）

目标为本机验证平台 linux/amd64，不代表已确定交付平台。

基础镜像：`python:3.13-slim-trixie@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285`。
实际 Python 3.13.15、Debian 13.6。在该镜像中通过官方 Debian APT 源更新索引，下载已验证签名索引所指向的软件包。APT dist-upgrade 模拟/下载结果为无待升级包。

额外依赖：`libexpat1 2.8.3-1~deb13u1 amd64`，来自 `debian-security trixie-security/main`。
安装包保存在 `deps/debs/`，SHA-256 见 `SHA256SUMS`。构建时校验并离线安装该文件，不从浮动 APT 源选择版本。交付构建源码时须包含此安装包和校验文件。

运行镜像通过包管理器删除 `mount` 和 Python `pip`，不删除漏洞扫描元数据，不使用忽略规则。构建阶段仍使用 pip 安装 requirements.lock。

重建命令（项目根目录执行）：

```bash
PYTHON_BASE=python:3.13-slim-trixie@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285 \
PLATFORM=linux/amd64 BUILD_ID=security1 bash scripts/build.sh
```

更新基础镜像摘要或系统依赖时，必须重新下载对应架构的官方包、更新校验值，并重新测试及扫描。Python 依赖固定版本但尚未锁定 wheel 哈希；完整供应链可复现性仍有改进空间。
