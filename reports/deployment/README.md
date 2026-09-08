# 0.3.0 部署验证记录

日期：2026-09-08。本机 Ubuntu 26.04.1 / Linux amd64、i7-9750H、约 30 GiB 内存；Docker 29.1.3。源码分支 codex/kmeans-deployment。本报告只覆盖封装示例与本地环境，不代表真实业务算法、目标集群或 GPU 已验收。

## 已完成

| 检查 | 结果与证据 |
|---|---|
| 固定依赖镜像构建 | PASS；build.log、image-inspect.json、python-inventory.json |
| 宿主接口/配置测试 | 15 项发现，12 项通过，3 项算法测试在容器执行；local-tests.log |
| 镜像内接口/算法测试 | 15 项发现，14 项通过，1 项宿主配置测试跳过；docker-integration/algorithm-tests.txt |
| KMEANS 数值 | 与独立 sklearn 调用及合成真值的 adjusted_rand_score 均为 1.0；CRS/变换/NoData/类型检查通过 |
| MNDWI 回归 | 合成像元 0.5、-0.5、NaN 验证通过；结果路径更新为 result/ |
| Docker 运行约束 | 默认非 root、输入及根只读、输出与 tmp 可写；container-checks.log |
| env、路径、失败 | 字面 env、中文/空格路径、错误输入、拒绝覆盖、输出无权限均通过；integration.log |
| 运行断网 | 所有 Docker 算法测试使用 --network none，依赖/数据无需运行时下载 |
| OOM | 32 MiB 限额内分配 256 MiB 的独立诊断进程，退出 137 且 OOMKilled=true；docker-integration/oom-state.json |
| 停止与重跑 | 百万像元、64 簇任务请求停止后约 6.747 秒退出 143；临时文件和锁清理，无成功结果，重跑通过；docker-integration/stop-result.json |
| Kubernetes | kind v0.33.0 / Kubernetes v1.36.4，单节点 Ready；两个并发 Job 成功；长任务 suspend 后 Pod 删除、无成功结果、无锁残留；k8s-integration.log |
| 数据盘存储 | kind 节点 /var 持久卷实际位于 /mnt/robot_disk/docker-engine/volumes；输入输出为数据盘 bind mount；kind-mounts.json |
| 离线镜像导出/加载 | PASS；SHA256 全部核对后 docker load 成功，只用交付包脚本/样本断网运行成功；offline-load.log、offline-run.jsonl（同一宿主机，不是异机测试） |

Docker 实测小样本 90×90、两波段、8099 有效像元：进程总耗时约 6.448 秒（含导入），峰值 RSS 165900 KiB，1 CPU / 1 GiB 限制。现场同时存在构建/扫描/集群活动，仅为环境参考，不是无竞争性能基线，也不是大影像资源承诺。百万像元任务用于中断测试，没有以完整运行时间作为基准。

## 安全与 GPU 限制

**后续更新：用户安装 Toolkit 1.20.0 并配置 Docker 后，容器 nvidia-smi、CUDA 驱动初始化、设备枚举及三轮真实 GPU 向量加法已通过（每轮 1048583 元素，误差为 0）；Kubernetes 节点仍为 Ready。详见 gpu-followup/README.md。下文 GPU 失败记录描述首次交付时状态。**

Trivy 0.74.0，扫描库更新时间 2026-09-07 19:06 UTC，扫描时尚未到 NextUpdate。报告仍有 47 HIGH、3 CRITICAL（50 条软件包-漏洞记录、18 个不同漏洞编号），此次记录均未给 FixedVersion；扫描退出 2，无忽略规则。与旧版记录数量相同不等于安全。原始报告见 security/scan.json；不得标记为无高危或正式合规交付。

宿主 GTX 1650 / 4 GiB / 驱动 595.84 可被 nvidia-smi 识别；Docker --gpus all 实测失败：无法选择具备 GPU 能力的设备驱动，见 gpu-probe.txt。本次未安装 NVIDIA Container Toolkit，GPU 运算尚未验证。两个示例只使用 CPU。

## 适用范围

本机 kind 集群提供额外的独立 containerd 运行环境，但不等同于另一台实体机或甲方生产集群。仅测批处理 Job，不声称验证了服务接口、服务发现、HPA、多节点 PVC 或集群网络策略。新算法、真实数据、GPU/驱动组合、生产网络和存储须在收到代码或平台参数后另行验收。

交付测试版只保存在本地，未推送 GitHub/GHCR。历史 security-update/README.md 原有未提交改动保持不动。

## 交付定位

镜像：`remote-sensing-framework:0.3.0-kmeans1`。离线包目录：`/mnt/robot_disk/deliveries/rs-0.3.0-kmeans1`。

镜像归档大小：166752617 字节；SHA256：`ca22eeeb8d844708900a580b0c4d5070a33d018c553db57c782e51cd3d1cec63`。完整交付包另附 .sha256，目录内 SHA256SUMS 校验每个交付文件。
