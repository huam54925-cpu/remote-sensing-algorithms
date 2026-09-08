# Docker / Kubernetes GPU 命令操作手册

项目：`/mnt/robot_disk/remote_sensing_project`。适用于这台 Linux amd64、GTX 1650 的本地 kind 环境；生产节点应按平台规范安装驱动与运行时，不直接照搬 kind 的驱动复制方案。

## 1. 日常检查（只读）

```bash
cd /mnt/robot_disk/remote_sensing_project
export PATH=/mnt/robot_disk/k8s/bin:$PATH
export KUBECONFIG=/mnt/robot_disk/k8s/config/kubeconfig
export IMAGE=remote-sensing-framework:0.3.0-kmeans1

nvidia-smi
nvidia-ctk --version
docker info --format '{{json .Runtimes}}'
kubectl get nodes -o wide
kubectl get node rs-lab-control-plane -o jsonpath='{.status.allocatable.nvidia\.com/gpu}{"\n"}'
kubectl -n kube-system get pods -l app=nvidia-device-plugin
```

正常应看到节点 Ready、GPU 数量 1、插件 Running。`allocatable=1` 是节点总可分配数量，不等于当前空闲数量；看当前占用应使用 `kubectl describe node rs-lab-control-plane` 的 Allocated resources 部分。

## 2. 一条命令复测实际 GPU 运算

```bash
bash scripts/test-gpu.sh
```

执行三轮 float32 GPU 向量加法，与 CPU 参考逐项比对。成功输出 `status: PASS`、`cpu_fallback: false`，每轮 `max_absolute_error: 0`。

## 3. 一条命令复测 Kubernetes GPU 调度

```bash
python3 scripts/test-k8s-gpu.py
```

脚本自动创建 `rs-gpu-tests` 命名空间及测试 ConfigMap，依次验证：

1. 不申请 GPU 的普通 Pod 看不到 `/dev/nvidia0`。
2. 申请 1 个 GPU 的 Pod 完成实际 CUDA 计算。
3. 第一个 Pod 保留 GPU 配额时，第二个 1-GPU Job 因 `Insufficient nvidia.com/gpu` 等待。
4. 删除第一个 Pod 后，第二个 Job 获得资源并完成正确计算。
5. 申请 2 个 GPU 的 Pod 无法调度。
6. 20 秒任务时限实际触发 `DeadlineExceeded`。

正常约 1–2 分钟；证据保存在 `reports/k8s-gpu/run-时间戳/`。测试会短暂占用本集群唯一 GPU 配额；确认没有其他 GPU 任务后运行。脚本清理测试占用与无法调度的 Pod，保留完成/超时 Job 和证据用于查看。

## 4. 单独提交一个 GPU 计算 Job

```bash
kubectl create namespace rs-gpu-tests --dry-run=client -o yaml | kubectl apply -f -
kubectl -n rs-gpu-tests create configmap rs-cuda-compute \
  --from-file=verify_cuda_compute.py=tests/verify_cuda_compute.py \
  --dry-run=client -o yaml | kubectl apply -f -

job=$(kubectl create -f configs/gpu/compute-job.json -o jsonpath='{.metadata.name}')
kubectl -n rs-gpu-tests wait --for=condition=complete "job/$job" --timeout=120s
kubectl -n rs-gpu-tests logs "job/$job"
```

Job 使用随机名称避免覆盖旧任务，申请 `nvidia.com/gpu: 1`，使用默认 runc + 原生 CDI；不需要 privileged、显卡 hostPath 或 `runtimeClassName: nvidia-bootstrap`。后者专供设备插件启动。

## 5. 查看日志、排错、停止

```bash
kubectl -n rs-gpu-tests get jobs,pods -o wide
kubectl describe node rs-lab-control-plane
kubectl -n kube-system logs ds/nvidia-device-plugin --tail=100
kubectl -n rs-gpu-tests get events --sort-by=.metadata.creationTimestamp

# 使用第 4 节的 job 变量；如果换了终端，请先 job=实际任务名
kubectl -n rs-gpu-tests describe "job/$job"
kubectl -n rs-gpu-tests logs "job/$job" > "outputs/${job}.log"

# 停止整个 Job，防止控制器重建 Pod
kubectl -n rs-gpu-tests patch "job/$job" --type=merge -p '{"spec":{"suspend":true}}'
```

不要只删除 Job 管理的 Pod 来表达“停止任务”，控制器可能补建。恢复 suspended Job 会重新创建 Pod，不等于算法断点续算。硬件故障、GPU 显存不足、长时间 GPU 内核的协作中止仍需真实算法专项测试。

| 现象 | 首先检查 |
|---|---|
| GPU 数量为空/0 | 插件日志、NVML 访问、设备健康、节点驱动与 CDI 路径 |
| `Insufficient nvidia.com/gpu` | 申请数量与已占用配额；本机只有 1 个 |
| `CreateContainerError` / CDI mount 错误 | `kubectl describe pod`，核对节点 CDI 引用的源文件/设备是否存在 |
| `ErrImageNeverPull` | 对应镜像是否已导入该 kind 节点；Docker 有镜像不代表节点 containerd 有 |
| `DeadlineExceeded` | Job 运行时限，查看执行日志判断是过短时限还是程序卡住 |
| 137 / OOMKilled | 普通内存限制及 OOM 状态；CUDA 显存 OOM 不是同一个错误 |
| 143 | 收到 SIGTERM 后退出；需结合成功标记、日志判断任务状态 |

## 6. 首次配置/复装本地 kind GPU 接入

当前环境已经配置完成。此节用于可复现部署或排错，不必每次运行算法都执行。

**维护时执行：**准备脚本拒绝在存在活动或待调度 GPU Pod 时运行，然后暂时删除设备插件、复制当前宿主驱动文件，重启 kind 节点内的 containerd。不会重启宿主 Docker 或安装宿主内核驱动。驱动版本发生变化时，建议使用新建 kind 节点验证；当前脚本不是生产驱动升级管理器。

```bash
# 前提：Docker / kind 集群正常，宿主 NVIDIA Toolkit 已配置成功。
# 二者的工具、配置及持久数据均位于 /mnt/robot_disk。
python3 scripts/setup-kind-gpu.py
bash scripts/install-kind-device-plugin.sh
python3 scripts/test-k8s-gpu.py
```

首次缺少插件镜像时需要联网。安装脚本固定 NVIDIA v0.20.0 镜像摘要，单独导入 amd64，避免 kind 对缺失其他架构内容执行 `--all-platforms` 导入的错误。算法镜像仍需先在节点中加载（已有时不用重复）：

```bash
export TMPDIR=/mnt/robot_disk/k8s/cache
kind load docker-image "$IMAGE" --name rs-lab
```

kind 节点内部路径：`/opt/nvidia-driver` 为本地驱动文件副本，`/etc/cdi/nvidia-kind.json` 用于设备插件启动，`/run/cdi/` 由设备插件生成任务用 CDI。设备插件通过专用运行时获得初始化用 GPU 访问，再向 kubelet 登记资源；算法 Pod 通过正常资源申请获得设备。

## 7. CPU 算法与离线包仍可使用

```bash
# 有 .env 时先保留自己的配置，不要覆盖。
test -e .env || cp .env.example .env
# 按操作说明编辑 .env，特别是每次使用新的 OUTPUT_DIR。
python3 scripts/env-run.py .env
# 另一终端用 .env 中 CONTAINER_NAME 停止任务：
bash scripts/stop.sh rs-kmeans-001 10
```

原始 `rs-0.3.0-kmeans1-bundle.tar.gz` 是此前的 CPU 算法交付快照；本次报告与 GPU 测试脚本作为补充文件提供，不改动旧包校验值。完整离线 GPU 基础设施安装包尚未制作，不能只凭旧算法镜像包在一台无驱动的新机器上直接完成 GPU 部署。
