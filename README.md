# 遥感算法容器封装框架 0.1.0

当前范围：环境检查、附件核对、批处理框架准备。13 项遥感算法尚未实现，未下载卫星影像，未构建镜像。`smoke` 仅对输入文件计算 SHA-256 并写入 JSON，以验证接口和文件流转，不是遥感算法。

## 本地体验

在本项目目录执行：

```bash
bash scripts/test-local.sh
PYTHONPATH=src python3 -m rs_container --help
PYTHONPATH=src python3 -m rs_container --list
PYTHONPATH=src python3 -m rs_container --algorithm smoke --input data/input/smoke.txt --output-dir outputs/local-smoke-001
```

输出目录中若已有 smoke-result.json，程序退出 5，不覆盖结果。请更换输出目录。

## 构建与容器运行（尚未实测）

前提：安装可用的 Docker；明确目标架构；核验官方 Python slim 基础镜像、版本和 digest。框架只用标准库，本机已验证 Python 3.14.4；容器 Python 版本未选定。构建脚本拒绝没有 digest 的基础镜像。

```bash
export PYTHON_BASE='python:<已确认版本>-slim-<发行版>@sha256:<真实64位摘要>'
export PLATFORM='linux/amd64' # 仅示例；须以目标平台为准
export BUILD_ID='<唯一构建编号>'
bash scripts/build.sh
export IMAGE="remote-sensing-framework:0.1.0-${BUILD_ID}"
INPUT_DIR="$PWD/data/input" OUTPUT_DIR="$PWD/outputs/container-smoke-001" bash scripts/run.sh
# 查看镜像内健康检查（只检测框架入口）
docker run --rm --read-only --network none --cap-drop ALL --security-opt no-new-privileges "$IMAGE" --healthcheck
# 导出供 docker load 使用，不替代规范中的仓库交付
EXPORT_FILE="$PWD/outputs/image.tar.gz" bash scripts/export.sh
```

基础镜像包含的系统包由 digest 固定；实际算法依赖接入时补齐版本/hash 锁定、系统包清单及漏洞扫描。当前多阶段构建只是框架入口检查与源码复制，尚无算法构建依赖。

运行脚本以当前普通用户 UID/GID 写入挂载输出目录，输入只读，根文件系统只读，/tmp 使用 64 MiB 内存卷，禁网、移除全部 Linux capabilities。大中间文件应放挂载的输出目录或新增持久化工作卷，不能放入 /tmp。脚本未配置 GPU。

CPU limit 默认 1 核、内存 limit 默认 512 MiB；可用 CPU_LIMIT/MEMORY_LIMIT 覆盖。Kubernetes 模板 requests 为 250m/128Mi、limits 为 1/512Mi，均为框架测试占位值，不是算法性能承诺。

## 文件导航

- docs/environment.md：实测环境。
- docs/compliance.md：逐条规范对照和待确认事项。
- docs/interface.md：接口、退出码与接入约定。
- docs/test-record.md：已执行测试与待执行项目。
- docs/algorithm-intake.md：算法代码/数据接收清单。
- configs/algorithms.json：Excel 13 项原始清单与待接入状态。
- configs/job.template.yaml：Kubernetes Job 模板；替换镜像、PVC 和每次运行的输出子目录后才能使用。

实现参考：[Dockerfile 官方说明](https://docs.docker.com/reference/dockerfile/)、[Docker 运行参数](https://docs.docker.com/engine/containers/run/)、[Kubernetes Job](https://kubernetes.io/docs/concepts/workloads/controllers/job/)。核对日期：2026-09-07。
