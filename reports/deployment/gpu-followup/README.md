# GPU 配置后复测

> 2026-09-08 更新：Kubernetes GPU 调度与实际 CUDA 运算已实测通过。最新结论、剩余项见 [总报告](../../../docs/readiness-report-2026-09-08.md)，复测与启停命令见 [操作手册](../../../docs/commands-gpu-k8s.md)。下文较早状态保留作历史记录。

用户安装 NVIDIA Container Toolkit CLI 1.20.0，执行 runtime configure 并重启 Docker 后复测。

- 现有 0.3.0 镜像通过 `--gpus all` 成功运行 nvidia-smi，识别 GTX 1650、4096 MiB 显存、驱动 595.84。
- 同一镜像在非 root、只读根、禁网、移除 capabilities 和 no-new-privileges 条件下成功加载 libcuda.so.1，cuInit 返回 0，发现 1 个 CUDA 设备。
- Docker 重启后 kind 节点 rs-lab-control-plane 为 Ready。

已进一步完成真实 CUDA 计算内核测试：三轮 float32 向量加法，每轮 1048583 个元素，GPU 结果与 CPU 参考逐项一致，最大绝对误差为 0，没有 CPU 回退。通过驱动 JIT 编译 PTX 并启动 GPU 内核，覆盖显存分配、上传、计算、同步、下载和释放，总显存分配约 12 MiB。真实业务 GPU 算法仍需单独验收。nvidia-smi 的 CUDA Version 是驱动支持能力，不证明镜像安装了同版本 CUDA Toolkit。当前 MNDWI/KMEANS 仍为 CPU 示例，现有 run.sh 不请求 GPU；后续 GPU 算法需另加启动配置和测试。kind 的 GPU 调度/设备插件也未验证。

本次仅追加环境验证记录；先前导出的交付包保持原始内容与校验值，其 GPU 状态是交付时的历史记录。

## 实际计算复测

在项目目录执行：

```bash
bash scripts/test-gpu.sh
```

默认使用现有 0.3.0 镜像，测试脚本只读挂载，无需重新构建或下载 CUDA Toolkit。PTX 目标为 sm_75（本机 GTX 1650），不承诺适用于更早架构。

原始结果：compute-result.json；退出码：compute.exit（0）；stderr：compute-stderr.log（空）。三次内核启动与同步墙钟时间约 3.71、2.47、4.92 ms，不包含数据传输、JIT 和容器启动，不用于证明整体加速比。

方法参考：[CUDA 内核启动 API](https://docs.nvidia.com/cuda/cuda-driver-api/group__CUDA__EXEC.html)、[模块与 PTX 加载 API](https://docs.nvidia.com/cuda/cuda-driver-api/group__CUDA__MODULE.html)。
