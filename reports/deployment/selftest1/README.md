# 0.3.0-selftest1 发布验证

日期：2026-09-09。为现有 CPU 算法镜像增加内置自检与持久化报告。

镜像：`ghcr.io/huam54925-cpu/remote-sensing-algorithms:0.3.0-selftest1`

固定引用：`ghcr.io/huam54925-cpu/remote-sensing-algorithms@sha256:8f3a329de34ddbfbe69a7ec8af6467a28acf33931d4fc72115a5373022ea7836`

本机构建成功；容器回归 17 项，16 通过，1 宿主配置测试跳过。新增失败测试故意注入算法失败，检查 FAIL 报告、非零退出码以及重复运行不覆盖旧文件；这是预期失败路径，不是发布失败。

完整宿主脚本运行通过，smoke、KMEANS、MNDWI、错误输入通过。生成的 JSON 状态、GeoTIFF 等持久化文件和 SHA256SUMS 已核验。镜像不存在的诊断路径已验证返回 1，并留下宿主 FAIL 报告。

本机完整报告：`outputs/selftest-release/machine-kzh55ys8/`。该目录含本机状态与测试数据；本记录不复制全部机器信息到发布说明。

推送 GHCR 成功。该版本未在 Vultr 重新运行；旧版异机证据见 ../vultr-20260909.md。安全依赖继承旧镜像，未声称通过新的漏洞扫描或生产验收。
