# 遥感算法封装准备与 Kubernetes GPU 验证总报告

日期：2026-09-08。项目：`/mnt/robot_disk/remote_sensing_project`。

**结论：本机 CPU 封装、Docker GPU 实际计算和 Kubernetes GPU 调度链路已验证；可以继续做真实算法接入准备，但尚不满足正式安全交付和目标平台验收。** 此报告更新此前“GPU 容器未打通 / Kubernetes GPU 未测”的状态；历史报告、原始日志及旧交付包仍保留原始时间点的记录。

完整可复制操作命令见 [命令手册](commands-gpu-k8s.md)。CPU 部署参数及退出码见 [部署说明](deployment-guide.md)。

## 1. 本次实际验证了什么

| 项目 | 结果 | 证据/边界 |
|---|---|---|
| kind 节点 GPU 资源登记 | PASS，`nvidia.com/gpu: 1` | NVIDIA 官方设备插件登记到 kubelet，未手工伪造节点资源 |
| Kubernetes GPU 计算 | PASS | Pod 显式申请 1 个 GPU，执行真实 CUDA 内核并下载结果；不是只运行 nvidia-smi |
| 数值正确性 | PASS | 每次三轮，每轮 1048583 个 float32 元素；与 CPU 参考逐项一致，最大绝对误差 0，无 CPU 回退 |
| 同一 GPU 的排队 | PASS | 第一个 Pod 保留 GPU 配额时，第二个 1-GPU Job 出现 `Insufficient nvidia.com/gpu`，未偷用或共享同一配额 |
| 释放后继续调度 | PASS | 删除占用 Pod 后，排队 Job 获得 GPU 并完成计算 |
| 超量申请 | PASS | 在只有 1 个 GPU 的节点上申请 2 个，任务无法调度 |
| 未申请设备的普通 Pod | PASS | 采用相同算法镜像但不申请 GPU，容器中没有 `/dev/nvidia0`；不是多租户对抗性安全测试 |
| 真实超时 | PASS | Job 配置 20 秒时限后实际出现 `DeadlineExceeded`，不只检查 YAML 字段 |
| 复装可重复性 | PASS | 使用整理后的准备/安装脚本复装设备插件，再完整复测 |
| 原 CPU 封装能力 | 已有实测通过 | MNDWI/KMEANS、数值与空间元数据、env、中文路径、读写权限、OOM、SIGTERM、重跑、Docker 断网与离线加载；见此前 reports/deployment |

本次使用的 GPU 持有 Pod 先完成计算，再等待以保留调度配额。因此“停止释放”验证的是 Pod/调度资源生命周期，**不等于验证了运行中的长 CUDA 内核能立即安全取消，也不等于断点续跑**。

算法 Pod 以非 root、只读根、移除 capabilities、禁止提权方式运行，未挂载显卡 hostPath，也未使用 privileged。设备插件属于基础设施，使用专用 `nvidia-bootstrap` 运行时完成初始化；实际算法使用默认 runc + 原生 CDI 资源注入。

## 2. 环境与存储

| 项目 | 实测配置 |
|---|---|
| 宿主 | Ubuntu 26.04.1，Linux amd64，i7-9750H，约 30 GiB 内存 |
| GPU | NVIDIA GeForce GTX 1650，4096 MiB，驱动 595.84 |
| Toolkit | NVIDIA Container Toolkit 1.20.0 |
| Docker | 29.1.3；默认运行时保留 runc |
| Kubernetes | kind 0.33.0，Kubernetes 1.36.4，节点内 containerd 2.3.4 |
| 设备插件 | NVIDIA k8s-device-plugin v0.20.0，固定 amd64 manifest digest |
| 算法镜像 | remote-sensing-framework:0.3.0-kmeans1；本次未改变算法镜像 |
| 工具与 kubeconfig | /mnt/robot_disk/k8s/bin、/mnt/robot_disk/k8s/config |
| Docker / 宿主 containerd 持久数据 | /mnt/robot_disk/docker-engine、/mnt/robot_disk/containerd |
| kind 驱动/运行状态 | 节点内 /opt/nvidia-driver、/etc/cdi、/run/cdi；驱动副本与节点持久层落在数据盘 |

kind 是嵌套容器环境。本次复制宿主当前 NVIDIA 驱动文件到节点，并建立显式驱动目录及设备路径，避免插件把容器内目标路径当作节点源路径。安装脚本只适用于该本地测试集群；生产节点应采用平台批准的驱动/Toolkit 安装和维护方式。宿主驱动升级、重建节点后需要重新准备和验证，不能把复制的驱动副本当成自动升级机制。

Kubernetes 的 GPU 独占配额只约束本集群调度。宿主桌面和其他 Docker GPU 程序仍可能使用同一块显卡；`nvidia.com/gpu: 1` 不代表隔离出全部 4 GiB 显存，也不代表 GPU 性能独占。

复测结束时节点 Ready、设备插件 Running（0 次重启）。数据盘 `/dev/sdb2` 以 ext4 挂载在 `/mnt/robot_disk`，容量约 916 GiB、可用约 858 GiB；现场记录见 `reports/k8s-gpu/disk-mount-final.txt`。

## 3. 安全门禁：仍未通过

| 组件 | HIGH | CRITICAL | 状态 |
|---|---:|---:|---|
| 算法镜像 0.3.0-kmeans1 | 47 | 3 | 引用同日既有扫描；镜像未变。50 条软件包-漏洞记录，18 个不同编号，当时记录未列修复版本 |
| 新增设备插件 v0.20.0 | 2 | 0 | 本次扫描。两条均为 CVE-2026-14456，涉及 libssl3t64、openssl-provider-fips；扫描器列出 3.5.7-1~deb13u2 修复版本 |

扫描器 Trivy 0.74.0；插件原始扫描报告为 `reports/k8s-gpu/plugin-security.json`。没有隐藏高危项或作安全豁免。应优先采用修复后的官方插件镜像，或另行建立可审查的修复镜像并重扫；本次没有擅自改造官方插件二进制/加密组件。

镜像漏洞扫描也不能覆盖所有运行时注入的宿主驱动文件。驱动副本的文件清单与 SHA256 保存在 `driver-copy.json`，仍需按目标安全要求审查宿主驱动、Toolkit、Kubernetes 基础组件及完整运行环境。

## 4. 对照原计划：还有什么没完成

以下是明确的剩余项，不把“已提供配置”写成“已验证”。

| 优先级 | 剩余项 | 现在的证据与下一步 |
|---|---|---|
| 正式交付前必须 | 清除高危/严重漏洞并获得安全验收 | 算法镜像仍有 50 条，插件新发现 2 条；选择修复版本、重扫，保存报告 |
| 正式交付前必须 | 第二台机器/干净虚拟机/甲方环境验收 | 当前离线加载与 kind 都在同一宿主机，尚未证明异机迁移、多架构、目标 K8s 兼容性 |
| 收到代码后必须 | 真实输入、输出及数值基准 | 目前是合成样本；需对方标准数据、预期结果、误差容限、波段/缩放/NoData/CRS 约定 |
| 收到代码后必须 | CUDA 框架、模型与显存需求 | 已验证驱动 JIT 计算；未验证对方 PyTorch/TensorFlow/ONNX、CUDA 扩展、模型权重及显存峰值 |
| 收到代码后必须 | 实际算法启动与外部依赖 | 入口、权重下载、授权、数据库/对象存储、外部服务、是否必须联网仍待确认 |
| 下一轮可提前做 | 子进程树、强杀、长 GPU 内核与重启恢复 | 当前完成 CPU SIGTERM、OOM、Job 超时、调度配额释放；尚未专项测孙进程残留、GPU 运行中取消、驱动故障和断点续跑 |
| 下一轮可提前做 | 大文件、磁盘满、并发写入、异常断电 | 权限失败与重复结果已测；ENOSPC、海量影像、共享输出并发、断电恢复尚未专项测试 |
| 目标平台确认后 | Kubernetes 网络隔离 | Docker --network none 已测；kind 网络策略执行能力未验证，不能只加 NetworkPolicy YAML 就声称 Pod 禁网 |
| 目标平台确认后 | 生产持久化与调度 | 当前使用单节点 hostPath；PVC/对象存储、多节点数据可达性、UID/GID、回收策略和容量告警需单独验证 |
| 接口明确后 | 服务 API/健康检查/指标 | 当前为批处理，无常驻服务；若需服务类，再补 OpenAPI、/health、/metrics、鉴权和服务启停验收 |
| 下一轮可提前做 | 日志保留、结构化 schema 与调试信息 | 有 JSON 日志和退出码；Docker --rm 后日志消失，需宿主重定向；完整日志 schema、脱敏堆栈、K8s 日志保留策略仍需补充 |
| 下一轮可提前做 | 性能基线和资源分档 | 当前只有小样本与异常测试现场数据；尚无多规模、多次重复、无竞争环境下的性能报告和 SLA |
| 发布前 | 发布仓库/离线基础设施包 | 原 CPU 离线包已测；未推送 GHCR/甲方仓库，尚未制作完整离线 GPU/K8s 安装包和新版本交付包 |
| 接收/发布前 | 许可证、权重许可、Secrets、标准 SBOM | 已有来源说明和依赖清单；真实代码/数据/权重许可、密钥注入、标准 SPDX/CycloneDX 清单及供应链校验需补齐 |

`strace` 已在宿主机存在；静态线索工具为 `scripts/inspect-algorithm.py`。它们还没有对未收到的真实算法给出运行行为结论。后续用标准样本做动态文件/网络/子进程跟踪，再决定适配方式。

## 5. 建议下一步

1. 先解决已知安全门禁，并在干净机器或目标测试服务器重跑交付验收；这两项不依赖对方算法代码。
2. 补存储异常、日志保留和子进程/强杀测试，明确任务失败后的清理与重跑约定。
3. 收到代码后依次完成：原始程序复现、依赖/联网/GPU 实测、封装适配、容器与原始结果比对、目标平台资源与停止验收。

可以把当前成果交给对方作为“接入规范与测试模板”，但不能作为其业务算法精度或正式安全合规证明。

## 6. 来源与证据

- [NVIDIA 官方设备插件](https://github.com/NVIDIA/k8s-device-plugin)：设备资源登记、cdi-cri 和运行时配置依据。
- [NVIDIA CDI 说明](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/cdi-support.html)：设备/驱动注入与升级后配置更新依据。
- [CUDA Driver API](https://docs.nvidia.com/cuda/cuda-driver-api/group__CUDA__EXEC.html)：实际 GPU 内核启动接口。
- 最终复装后完整测试：[summary.json](../reports/k8s-gpu/run-1788868434/summary.json)。全部 PASS；释放占用 Pod 到排队 Job 完成约 11.31 秒（包含调度、启动、运算与轮询，并非单独调度延迟）。
- 复装证据：[准备日志](../reports/k8s-gpu/setup-replay.log)、[插件安装日志](../reports/k8s-gpu/install-replay.log)。
- 操作手册第 4 节也已独立执行成功：[手动 Job 运算日志](../reports/k8s-gpu/manual-job.log)，三轮误差均为 0。
- 本次原始记录：`reports/k8s-gpu/`。包含失败尝试用于排错，最终结论以以上完整复测为准。
- 前序 CPU、Docker GPU 与离线演练记录：`reports/deployment/`、`reports/deployment/gpu-followup/`。
