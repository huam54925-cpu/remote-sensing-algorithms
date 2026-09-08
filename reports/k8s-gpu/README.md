# Kubernetes GPU 验证证据索引

最终结论：PASS。完整说明见 [总报告](../../docs/readiness-report-2026-09-08.md)，命令见 [操作手册](../../docs/commands-gpu-k8s.md)。

- 最终复装：setup-replay.log、install-replay.log。
- 最终全套测试：run-1788868434/summary.json；同目录含计算结果、排队事件、超时状态。
- 手册独立 Job：manual-job.log、manual-job.json。
- 驱动副本清单：driver-copy.json；CDI 路径校验：cdi-path-check.json。
- 新插件漏洞扫描：plugin-security.json，2 HIGH / 0 CRITICAL，尚未修复。

较早运行和排错日志保留原状，不作为最终成功结论。目录不含 kubeconfig、访问令牌或驱动二进制。当前算法镜像及此前 CPU 离线包未改变；这些文件是补充报告和复测配置，不是完整离线 GPU 安装包。
