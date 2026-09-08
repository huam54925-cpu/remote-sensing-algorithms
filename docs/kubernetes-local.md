# 数据盘上的本地 Kubernetes 测试环境

> 2026-09-08 更新：Kubernetes GPU 调度与实际 CUDA 运算已实测通过。最新结论、剩余项见 [总报告](readiness-report-2026-09-08.md)，复测与启停命令见 [操作手册](commands-gpu-k8s.md)。下文较早状态保留作历史记录。

用户指定将 Kubernetes 安装/数据保存在格式化的数据盘。采用 kind 单节点集群 rs-lab；它运行真实 Kubernetes 控制平面，适合本机集成测试，不作为生产集群交付。

| 内容 | 路径 |
|---|---|
| kind / kubectl 工具 | /mnt/robot_disk/k8s/bin |
| 集群配置、访问凭据 | /mnt/robot_disk/k8s/config |
| 宿主 Docker 镜像、容器、卷 | /mnt/robot_disk/docker-engine |
| 宿主 containerd 持久数据 | /mnt/robot_disk/containerd |
| 算法输入、输出 | /mnt/robot_disk/remote_sensing_project/data/input 与 outputs |

kind 节点内部的 /var/lib/containerd、kubelet 等持久状态随 Docker 节点容器/卷位于数据盘。/run 的运行态数据仍使用系统内存。kubeconfig 含访问凭据，不打包、不提交 Git。

kind 固定 v0.33.0，节点固定 kindest/node:v1.36.4@sha256:099e049362a1526b2db71494e1947aae99bd16290d7c895f2b7ea312e3cbfaed。工具下载并核对官方 SHA256。

```bash
export PATH=/mnt/robot_disk/k8s/bin:$PATH
export KUBECONFIG=/mnt/robot_disk/k8s/config/kubeconfig
kubectl get nodes -o wide
kind load docker-image remote-sensing-framework:0.3.0-kmeans1 --name rs-lab
export IMAGE=remote-sensing-framework:0.3.0-kmeans1
python3 scripts/test-k8s.py
```

脚本创建两个独立输出目录的并发 Job，再创建长任务测试 suspend 停止。backoffLimit=0 禁止失败重试，activeDeadlineSeconds=180 限制总时长；Job 使用非 root、只读根、最小能力与资源限制。示例 hostPath 只适合该单节点测试环境；生产部署必须由甲方确认 PVC/对象存储、权限和调度规则。批处理没有服务发现端点，无需为满足形式添加 HTTP 服务。

停止 Job 应先 suspend 或删除 Job；只删除 Pod 会被 Job 控制器补建。Docker 禁网测试独立进行；本 kind 默认网络组件的策略能力未经验证，不宣称 Kubernetes Pod 已禁网。

集群日常暂停（保留本地状态）：

```bash
docker stop rs-lab-control-plane
docker start rs-lab-control-plane
kubectl wait --for=condition=Ready node/rs-lab-control-plane --timeout=120s
```

删除测试集群会丢失集群内部状态；hostPath 输入输出仍留在数据盘。不要在使用 Docker、containerd 或集群时卸载数据盘。

官方资料：[kind 安装](https://kind.sigs.k8s.io/docs/user/quick-start/)、[配置挂载](https://kind.sigs.k8s.io/docs/user/configuration/)、[固定版本镜像](https://github.com/kubernetes-sigs/kind/releases/tag/v0.33.0)。实际完成状态见验证报告。

工具已安装后可用 `bash scripts/create-kind.sh` 在相同数据盘重新创建集群（集群已存在时不会覆盖）。装载算法镜像建议先设置 `export TMPDIR=/mnt/robot_disk/k8s/cache`，让中间归档也落在数据盘。Docker/containerd 已配置 RequiresMountsFor=/mnt/robot_disk。
