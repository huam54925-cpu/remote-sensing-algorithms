# 容器安全更新与剩余漏洞评估

日期：2026-09-08。项目根目录：`/mnt/robot_disk/remote_sensing_project`。

## 结论

已构建 `remote-sensing-framework:0.2.1-security1`，保留旧镜像 `0.2.0-mndwi3`。
新镜像功能回归通过，但安全门禁未通过。Trivy 扫描仍以 2 退出，不得宣称无高危漏洞或完整安全验收通过。

| 同一漏洞库、HIGH/CRITICAL 范围 | 原镜像 | 新镜像 |
|---|---:|---:|
| HIGH 软件包—漏洞记录 | 72 | 47 |
| CRITICAL 软件包—漏洞记录 | 9 | 3 |
| 合计 | 81 | 50 |
| 不重复漏洞编号 | 36 | 18 |

记录数按软件包与漏洞组合计数，同一源码包漏洞可重复出现在多个二进制包上。新镜像这 50 条均未列出 FixedVersion；这不等于上游没有修复，也不等于不存在风险。扫描没有隐藏未修复项、没有设置忽略列表。Python 包在最终镜像中无本次等级范围的告警，不代表所有等级或所有随附原生库均安全。

## 已实施变更

- 基础环境从 Python 3.13.11 / Debian 12.13 更新为 Python 3.13.15 / Debian 13.6，固定官方镜像摘要，见 `base-image.json` 和项目 `deps/README.md`。
- 新基础环境包含更新后的 OpenSSL、libcap、util-linux 等系统包；APT 检查无额外待升级包。额外安装 Expat 2.8.3-1~deb13u1，官方安装包与 SHA-256 随项目保存。
- 删除不需要的 mount 软件包。容器挂载由宿主机 Docker 完成，不依赖容器内 mount 命令。
- 卸载最终镜像中的 pip 及其随附组件；构建阶段保留 pip。候选基础镜像扫描曾报告随附 msgpack / setuptools 告警，最终镜像扫描已不再报告这两项。
- 保持算法计算逻辑和 Python 业务依赖版本，版本号更新为 0.2.1。增加构建时 rasterio、numpy、ssl、sqlite3 实际导入检查。
- 保留非 root、只读根文件系统、离线运行、挂载输入只读、输出可写、资源限制和结构化日志。

## 剩余漏洞适用性与处置

以下为基于供应商公告、已安装组件与当前入口的评估，不是已批准的豁免，也没有从原始报告扣除任何记录。所有链接均为对应供应商跟踪依据。

| 漏洞 | 核实结果与后续处置 |
|---|---|
| [CVE-2026-42496](https://security-tracker.debian.org/tracker/CVE-2026-42496)、[CVE-2026-42497](https://security-tracker.debian.org/tracker/CVE-2026-42497)、[CVE-2026-9538](https://security-tracker.debian.org/tracker/CVE-2026-9538) | 涉及 Perl Archive::Tar；运行镜像中该模块加载失败，未安装。基于当前镜像内容判断缺少受影响组件；后续安装 Perl 扩展后须重新评估。 |
| [CVE-2026-48962](https://security-tracker.debian.org/tracker/CVE-2026-48962) | 涉及 IO::Compress；运行镜像中该模块未安装。保留扫描告警及组件证据。 |
| [CVE-2026-57433](https://security-tracker.debian.org/tracker/CVE-2026-57433) | 涉及 Storable；运行镜像中该模块未安装。保留扫描告警及组件证据。 |
| [CVE-2026-8376](https://security-tracker.debian.org/tracker/CVE-2026-8376) | 公告限定 32 位 Perl 构建；实测本镜像 Perl ptrsize=8，为 64 位。此适用性结论仅针对当前 amd64 镜像，不能推广到其他架构。 |
| [CVE-2026-16742](https://security-tracker.debian.org/tracker/CVE-2026-16742) | 涉及 systemd-homed；镜像保留 libsystemd0/libudev1，但没有运行该服务，未发现 systemd-homed 命令。当前服务攻击路径不具备；不能称库包已经打补丁。 |
| [CVE-2026-13221](https://security-tracker.debian.org/tracker/CVE-2026-13221)、[CVE-2026-57432](https://security-tracker.debian.org/tracker/CVE-2026-57432) | Perl 解释器存在，不能判为不受影响；当前应用源码没有调用 Perl，降低可达性但不构成修复。继续跟踪 Debian 更新。前者仍是扫描中的 CRITICAL。 |
| [CVE-2026-11822](https://security-tracker.debian.org/tracker/CVE-2026-11822)、[CVE-2026-11824](https://security-tracker.debian.org/tracker/CVE-2026-11824) | SQLite FTS5 问题；Python sqlite3 与地理数据相关原生依赖可能使用 SQLite，不做无影响结论，不直接卸载。当前合成 GeoTIFF 用例不能证明恶意 SQLite 输入安全。 |
| [CVE-2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720) | 受影响位置为 infocmp 命令；算法入口不调用，但镜像保留 ncurses。保留待修复状态，不以业务未调用替代漏洞修复。 |
| [CVE-2026-41992](https://security-tracker.debian.org/tracker/CVE-2026-41992) | gzip 的 LZH 解压路径；当前入口不调用 gzip，软件包仍存在，不能宣布消除。 |
| [CVE-2026-54369](https://security-tracker.debian.org/tracker/CVE-2026-54369) | libacl 路径符号链接问题依赖特权调用者与可控路径。非 root、去除 capabilities、只读输入降低风险；libacl 是基础依赖，保留并跟踪补丁。 |
| [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642)、[CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409)、[CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) | 涉及特权挂载功能。已删除 mount 软件包，但 libmount 与其他 util-linux 组件仍保留，不能将所有关联告警算作修复。运行配置不授予特权或 CAP_SYS_ADMIN。 |
| [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408) | nsenter 仍安装；当前入口不调用，不提供 root/cgroup 特权。保留待修复项；不得改用 privileged 运行并沿用该风险判断。 |

原镜像 zlib 的 [CVE-2023-45853](https://security-tracker.debian.org/tracker/CVE-2023-45853) 涉及 MiniZip，Debian 对旧发行版说明对应受影响代码没有构建进其二进制包；新镜像的发行版版本已标记 fixed。此结论不覆盖第三方 wheel 私有打包的库。

逐项原始版本、修复字段、新旧对比与跟踪链接见 `vulnerability-comparison.csv`。供应商页面快照在 `debian-tracker/`；运行组件实测见 `runtime-inventory.txt`。

## 进一步精简方案评估

已选择 Debian 13 slim，兼容现有 manylinux wheel 且取得补丁收益。直接移除 libacl、libsystemd 等会破坏基础包依赖；APT 模拟输出见 `removal-simulation.txt`，未强制执行。

如验收坚持扫描 HIGH/CRITICAL 必须为零，可另做精简运行镜像原型，仅带 Python 和实际需要的原生库，排除 Perl/系统工具。但这会改变当前 /bin/sh 健康检查及运行维护约定，需要重新核对平台规范、列举共享库依赖并完整回归，不能靠删除 dpkg 数据库或漏洞元数据达到零告警。更换到 Alpine 等不同 libc 基础环境也需重新核验原生 wheel 兼容性；本次未实施。当前镜像继续等待供应商补丁，或由验收方基于逐项证据审批例外，不自行认定豁免。

## 测试与范围

- 本地 CLI 单元测试与新镜像内 CLI 单元测试：分别 11 项。
- 容器启动、正常任务、错误输入退出码 4、默认 UID 10001、只读根/输入、可写输出与临时目录检查。
- 原算法合成 GeoTIFF 回归：数值容差 rtol=1e-6，零分母与 NoData、CRS、transform、波段数、float32 和波段说明检查。
- 日志：`test-local.log`、`test-cli-container.log`、`test-container.log`、`test-mndwi.log`、`mndwi.stderr.jsonl`。

仅验证 linux/amd64 与现有合成样本；未开展真实卫星业务精度验收、Kubernetes 平台验证、渗透测试或全部原生库的独立安全审计。

## 扫描复现

本次 Trivy 0.74.0 使用与旧扫描一致的缓存数据库，元数据见 `db-metadata.json`，使用 `--skip-db-update` 确保对比口径。正式交付前应刷新漏洞库再扫描。

```bash
cd /mnt/robot_disk/remote_sensing_project
TRIVY_CACHE_DIR=/mnt/robot_disk/cache/trivy TMPDIR=/mnt/robot_disk/tmp/trivy \
/mnt/robot_disk/tools/trivy-0.74.0/trivy image \
  --image-src docker --scanners vuln --skip-db-update \
  --severity HIGH,CRITICAL --exit-code 2 --timeout 20m \
  --format json --output reports/security/security-update/trivy-security1.json \
  remote-sensing-framework:0.2.1-security1
echo "扫描退出码：$?"
```

旧镜像和原始扫描报告保留；本次未覆盖旧镜像导出包。新版本如需交付，应在剩余风险处理结论明确后单独导出并生成 SHA-256。

## 后续算法接入要求

接收算法组代码时明确目录规范、输入输出、接口与数据传输约定，先核实 GPU 等硬件依赖；本地资源不足时再安排云端硬件验证。该项为接入要求，不代表外部算法已完成验收。
