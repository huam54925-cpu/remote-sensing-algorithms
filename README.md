# 遥感算法容器封装框架 0.3.0

## 操作手册 1.1

详细操作手册共 42 页、12 章，包含配置填写、执行命令、参数说明、终端输出和完成判定。

- [PDF 手册](output/pdf/remote-sensing-operations-manual.pdf)
- [可复制命令的文本版](docs/manual/operations-manual.md)
- [LaTeX 源码及编译说明](docs/manual/README.md)

> 2026-09-08 更新：Kubernetes GPU 调度与实际 CUDA 运算已实测通过。最新结论、剩余项见 [总报告](docs/readiness-report-2026-09-08.md)，复测与启停命令见 [操作手册](docs/commands-gpu-k8s.md)。下文较早状态保留作历史记录。

CPU 批处理示例：MNDWI 双波段指数、基于 scikit-learn 的 KMEANS 多波段聚类，以及 smoke 接口诊断。合成数据测试不替代真实卫星数据和对方算法精度验收。

先读 [部署操作说明](docs/deployment-guide.md)。实施范围见 [准备计划](docs/preparation-plan.md)，实际验证状态见 [部署报告](reports/deployment/README.md)。

## 使用交付包

交付目录包含 image.tar.gz、SHA256SUMS、测试数据、.env.example、源码和运行脚本：

```bash
sha256sum -c SHA256SUMS
gzip -dc image.tar.gz | docker load
cp .env.example .env
# 编辑 .env 的输入、输出、工作目录及任务名称
python3 scripts/env-run.py .env
# 另一个终端停止任务
bash scripts/stop.sh rs-kmeans-001 10
```

当前算法运行禁网，输入只读、输出持久化、根文件系统只读、非 root 和资源限制。结果发布至 OUTPUT_DIR/result/，包含 success.json；0.2.x 的直接输出路径已迁移。运行日志为 stderr JSON，每次任务使用新的输出目录。

## 从源码构建

```bash
export PYTHON_BASE=python:3.13-slim-trixie@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285
PLATFORM=linux/amd64 BUILD_ID=kmeans1 bash scripts/build.sh
export IMAGE=remote-sensing-framework:0.3.0-kmeans1
bash scripts/test-local.sh
bash scripts/test-container.sh
python3 tests/verify_deployment.py
```

构建需要联网。主依赖固定在 requirements.lock，小型间接依赖另固定在 deps/python-transitive.lock，系统依赖见 deps/README.md。源码来源说明见 [K-Means 参考](docs/third-party-kmeans.md)。

生成可离线使用的样本：

```bash
mkdir -p data/input/kmeans-example
docker run --rm --network none --user "$(id -u):$(id -g)" \
  -v "$PWD/data/input/kmeans-example:/fixture" -v "$PWD/tests:/tests:ro" \
  --entrypoint python "$IMAGE" /tests/create_kmeans_fixture.py /fixture
```

## 本地 Kubernetes 和交付

[数据盘 Kubernetes 说明](docs/kubernetes-local.md)介绍 kind 测试集群及存储路径。GPU 容器能力单独记录在验证报告；两个算法示例只使用 CPU。

```bash
PACKAGE_DIR=/mnt/robot_disk/deliveries/rs-0.3.0 IMAGE="$IMAGE" bash scripts/package.sh
```

代码仓库不等同于镜像仓库。镜像包本地分发；以后可推送 GHCR 或甲方指定仓库。未通过无高危门禁时不得标记为正式合规交付。历史报告只对应各自的旧版本，不用作本版本验收证据。
