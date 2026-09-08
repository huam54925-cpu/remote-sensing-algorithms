# 遥感算法容器封装框架 0.2.1

负责算法容器化封装，当前已接入 MNDWI 双波段 GeoTIFF 示例及 smoke 接口测试。其他算法待接入，合成样本验证不替代真实卫星数据与业务精度验收。

已在 Linux amd64 上构建并验证 `remote-sensing-framework:0.2.1-security1`。基础环境为固定摘要的 Python 3.13.15 / Debian 13.6。Trivy 仍报告 47 HIGH、3 CRITICAL，**尚未通过无高危漏洞门禁**，见 [安全更新报告](reports/security/security-update/README.md)。Kubernetes 配置为模板，尚未完成目标平台验证。

## 获取与构建

```bash
git clone --recurse-submodules https://github.com/huam54925-cpu/remote-sensing-algorithms.git
cd remote-sensing-algorithms
export PYTHON_BASE=python:3.13-slim-trixie@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285
PLATFORM=linux/amd64 BUILD_ID=security1 bash scripts/build.sh
export IMAGE=remote-sensing-framework:0.2.1-security1
```

需要 Docker、Bash；本地测试另需 Python 3。构建阶段联网，运行阶段不联网。仓库包含 Expat 官方安装包与校验值，见 [依赖说明](deps/README.md)。Spyndex 子模块用于来源核对，不是运行依赖，遵循其自身许可证。

## 运行与测试

以可使用 Docker 的普通用户执行。每次使用新的输出目录，已有结果不会覆盖。

```bash
export IMAGE=remote-sensing-framework:0.2.1-security1
bash scripts/test-local.sh
bash scripts/test-container.sh
docker run --rm "$IMAGE" --help

# 生成合成测试影像
mkdir -p data/input/mndwi-example
docker run --rm --network none --user "$(id -u):$(id -g)" -v "$PWD/data/input/mndwi-example:/fixture" -v "$PWD/tests/create_mndwi_fixture.py:/create.py:ro" --entrypoint python "$IMAGE" /create.py

export INPUT_DIR="$PWD/data/input/mndwi-example"
export OUTPUT_DIR="$PWD/outputs/example-001"
RS_ALGORITHM=MNDWI RS_INPUT=/data/input/mndwi-input.tif bash scripts/run.sh

docker run --rm --read-only --network none -v "$PWD/outputs/example-001:/result:ro" -v "$PWD/tests/verify_mndwi_output.py:/verify.py:ro" --entrypoint python "$IMAGE" /verify.py
```

运行脚本设置非 root、只读根和输入、可写输出、禁网、移除 capabilities、no-new-privileges。默认限制 1 CPU、512 MiB 内存和 64 MiB 临时目录；CPU_LIMIT/MEMORY_LIMIT 可配置。详见 [接口说明](docs/interface.md)。

## 交付文件

- `src/`、`requirements.lock`、`Dockerfile`、`deps/`：源码、固定依赖与构建文件。
- `scripts/`、`tests/`：运行、导出与自动测试。
- `configs/`：算法清单和平台模板，按目标环境配置。
- `docs/`：接口、接收要求、历史环境和测试记录，历史文档按对应版本解读。
- `reports/security/`：原始扫描、新旧对比、剩余漏洞评估和验证记录。
- `sources/`：第三方参考源码和来源材料。

Docker 镜像包、运行输出、临时文件及实际影像数据不提交 Git。镜像可本地导出，另通过容器仓库或发布附件分发：

```bash
mkdir -p images
export IMAGE=remote-sensing-framework:0.2.1-security1
EXPORT_FILE="$PWD/images/remote-sensing-0.2.1-security1-amd64.tar.gz" bash scripts/export.sh
sha256sum images/remote-sensing-0.2.1-security1-amd64.tar.gz > images/remote-sensing-0.2.1-security1-amd64.tar.gz.sha256
```

导出不代表已通过安全验收。最新状态以安全更新报告为准。
