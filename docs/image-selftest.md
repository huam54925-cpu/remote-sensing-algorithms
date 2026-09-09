# 镜像内置自检与机器验收报告

`0.3.0-selftest1` 基于已通过 Vultr 异机测试的 `0.3.0-kmeans1` 固定 digest 扩展。算法及依赖保持一致，增加自检入口和报告生成能力。该新标签需要在目标服务器重新拉取与验证；旧镜像的通过记录不自动代表新标签的异机验收。

## 完整机器检查（推荐）

服务器需要 Linux amd64、Docker 和 Python 3。镜像为 GHCR 包；无读取权限时先用有 `read:packages` 权限的 classic Token 登录。命令支持 root 或有 Docker 权限的普通用户。root 启动时，算法容器仍使用 UID 10001。

```bash
IMAGE=ghcr.io/huam54925-cpu/remote-sensing-algorithms@sha256:8f3a329de34ddbfbe69a7ec8af6467a28acf33931d4fc72115a5373022ea7836
docker login ghcr.io -u huam54925-cpu
docker pull "$IMAGE"
# 从刚拉取的镜像获取配套脚本，不需要本机传文件。
docker run --rm --network none --read-only --entrypoint cat "$IMAGE" /app/check-host.py > rs-check-host.py
python3 rs-check-host.py "$IMAGE" --output-dir "$PWD/rs-reports"
```

脚本会读取镜像 ID，并用该 ID 启动测试，避免检查期间标签变化。复现时可将 IMAGE 设置为发布报告中的完整 `@sha256:` 引用。

末尾必须输出 `PASS: MACHINE TEST`，命令退出码为 0。失败时输出 FAIL、非零退出码；查看 `host-report.json` 和 `selftest.log`。Docker 无法运行、镜像不存在、架构不匹配也会留下宿主报告。脚本不自动安装或修改 Docker、不重启系统。

每次创建新的 `rs-reports/machine-*/`：

- `SUMMARY.md`：机器测试结论与文件说明。
- `host-report.json`：系统、内核、架构、主机名、可见 CPU 数量、内存、报告盘容量、挂载、cloud-init、重启提示、Docker 版本、镜像 ID/digest 和执行命令。
- `selftest.log`：自检标准输出与错误日志。
- `container/selftest-*/report.json`、`report.md`：逐项 PASS/FAIL、耗时及容器环境和依赖版本。
- `container/selftest-*/commands.jsonl`：算法子进程命令、退出码与原始日志。
- 同目录保留输入 GeoTIFF、KMEANS 合成真值、输出 GeoTIFF、success.json 与 SHA256SUMS。

报告含主机名、磁盘路径等机器信息，分享前可自行检查。脚本不读取 Docker 登录配置、Token、SSH 密钥或全部环境变量。

## 只检查镜像

```bash
docker run --rm --network none --read-only \
  --cap-drop ALL --security-opt no-new-privileges \
  --cpus 1 --memory 1g --pids-limit 128 \
  --tmpfs /tmp:rw,noexec,nosuid,size=128m \
  "$IMAGE" --self-test
```

末尾输出 `PASS: ALL ALGORITHM CHECKS`。默认报告写入容器 `/tmp/rs-reports`，上述 `--rm` 命令退出后删除。要持久化并记录宿主信息，使用前面的完整机器检查命令。

镜像自检也支持 `--report-dir /reports`，将可写宿主目录挂载到 `/reports` 即可保存结果；每次新建唯一子目录，不覆盖旧记录。

## 覆盖范围

1. smoke：文件字节数、SHA256、输出写入。
2. KMEANS：900 个像元的三簇合成数据（899 有效、1 NoData）；与合成真值及独立 sklearn 基准的 ARI 均为 1；输出 dtype/NoData/CRS/仿射变换/尺寸；拒绝覆盖已有结果。
3. MNDWI：0.5、-0.5、分母为零时 NaN；输出 dtype/NoData/空间信息和完成标记。
4. 错误输入：不存在的文件返回 4，不发布结果。

PASS 代表这些检查通过。宿主资源与挂载是状态快照，不等于磁盘健康、所有挂载可写或生产容量保证。CPU 示例不验证 GPU、真实卫星数据业务精度、并发压力或漏洞合规。OOM、取消和重跑另见原有完整部署测试。

## 构建

```bash
docker build -f Dockerfile.selftest -t remote-sensing-framework:0.3.0-selftest1 .
```

该 Dockerfile 直接扩展经过异机验证的固定镜像，避免为增加自检重新解析依赖。主 Dockerfile 同样包含自检模块和宿主检查脚本，可用于完整重建。
