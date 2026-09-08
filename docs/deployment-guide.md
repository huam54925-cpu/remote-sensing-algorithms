# 0.3.0 本地与离线部署操作说明

本交付是 CPU 算法封装测试版，接入 MNDWI 与 KMEANS。KMEANS 参考 scikit-learn 官方 K-Means 示例，改为多波段 GeoTIFF；不是地物语义分类或对方真实算法。镜像适用 linux/amd64。本机实测和未完成项见 reports/deployment/README.md。

## 离线使用

运行需要 Linux amd64、Docker Engine、Bash、Python 3（仅标准库）及普通用户的 Docker 访问权限。无需宿主机安装 numpy、GDAL 或 scikit-learn。建议为示例预留 1 CPU、1 GiB 内存；机器运行 Docker/K8s 还需要额外资源。

从交付包目录执行：

```bash
sha256sum -c SHA256SUMS
bash scripts/check-environment.sh .
gzip -dc image.tar.gz | docker load
cp .env.example .env
# 编辑 .env，填写宿主机目录；样本可直接使用随包 data/input/kmeans-example
python3 scripts/env-run.py .env
```

.env 按字面 KEY=VALUE 读取，不作为 shell 执行。不支持变量展开和行尾注释。相对路径以 .env 所在目录为基准；支持中文和空格。配置文件覆盖继承的同名环境变量，CLI 算法参数最后覆盖配置值。

| 变量 | 示例或默认值 | 用途 |
|---|---|---|
| IMAGE | remote-sensing-framework:0.3.0-kmeans1 | 已加载的镜像标签，可改为仓库 digest |
| INPUT_DIR | ./data/input/kmeans-example | 宿主机输入目录，容器只读 |
| OUTPUT_DIR | ./outputs/kmeans-001 | 每次新建的输出目录 |
| WORK_DIR | ./work/kmeans-001 | 宿主机大型中间文件目录；当前两个示例尚不使用 |
| CONTAINER_NAME | rs-kmeans-001 | 停止、查询任务使用的容器名 |
| CPU_LIMIT | 1 | CPU 限制 |
| MEMORY_LIMIT | 1g | 内存限制，超限可能 OOMKilled |
| STOP_TIMEOUT | 10 | docker stop 默认宽限秒数 |
| RS_ALGORITHM | KMEANS | KMEANS / MNDWI / smoke |
| RS_INPUT | /data/input/kmeans-input.tif | 容器内输入路径 |
| RS_PARAMS | {"clusters":3,"seed":0,"max_iter":100,"max_pixels":1000000} | 算法 JSON 参数 |
| RS_TASK_ID | kmeans-001 | 日志关联 ID |

不需要密钥或服务端地址。当前两个算法运行禁网，也没有 HTTP 监听端口。以后接入联网算法时须增加明确的网络配置与测试。

## 结果、日志、停止

KMEANS 输出 OUTPUT_DIR/result/clusters.tif；MNDWI 输出 OUTPUT_DIR/result/mndwi.tif。两者都包含 result/success.json。只有完整计算后才发布 result 目录。**0.3.0 改变了 0.2.x 的直接输出路径**，调用方需同步更新。

结构化日志写 stderr，可重定向为宿主机日志。查看运行中任务：

```bash
docker ps
docker logs -f rs-kmeans-001
docker stats rs-kmeans-001
# 另一个终端请求停止；10 秒内未退出则 Docker 强制终止
bash scripts/stop.sh rs-kmeans-001 10
```

运行脚本使用 --rm；容器退出后 docker logs 不再可用。需要留存日志时使用：

```bash
mkdir -p logs
python3 scripts/env-run.py .env > logs/stdout.txt 2> logs/task.jsonl
```

SIGTERM/SIGINT 在 Python 获得执行控制时清理临时结果并退出；原生计算库可能延迟处理信号，不能保证毫秒级停止。强制终止、OOM 或断电可能留下 .partial-* 和 .rs-lock；使用新的 OUTPUT_DIR 重跑，保留旧目录用于排错。没有断点续跑能力。完成发布与停止存在竞争时，以完整 success.json 和进程退出状态共同判断，不把退出非零描述为成功。

| 退出码 | 含义 |
|---|---|
| 0 | 成功或帮助/列表检查成功 |
| 1 | 未处理错误 |
| 2 | 参数、输入内容或示例规模限制不符合要求 |
| 3 | 算法未接入 |
| 4 | 输入不存在、不可读，或算法输出 I/O 错误 |
| 5 | 结果已存在、目录被占用，或 smoke 输出失败 |
| 130 / 143 | SIGINT / SIGTERM 协作中止 |
| 137 | 强制终止；用 docker inspect 的 OOMKilled 区分 OOM（仅对保留容器） |
| 125 / 126 / 127 | Docker 启动失败或入口执行错误 |

## 算法参数与限制

KMEANS 使用全部波段的原始数值，不自动标准化；各波段单位/尺度不一致时不能直接赋予业务意义。输出 uint16，0 为 NoData，1..K 是任意聚类编号。固定 seed=0、n_init=10、单线程；默认 K=3、max_iter=100、max_pixels=1000000，上限 10000000 像元、32 波段。它是内存型示例，上限不代表配置内存一定够用。NoData 和非有限值排除；有效或不同像元不足 K 时拒绝执行。跨平台比较采用聚类一致性指标，不只比较编号。

MNDWI 参数：green_band=1、swir1_band=2、output_name=mndwi.tif；输出 float32，分母为零与无效像元输出 NaN。输入空间参考保留。算法精度验收另需真实影像和对方基准。

## 自动验证与重建

```bash
export IMAGE=remote-sensing-framework:0.3.0-kmeans1
bash scripts/test-container.sh
python3 tests/verify_deployment.py
```

第二条会生成约百万像元数据测试取消，占用额外磁盘与时间。结果保存在 outputs/deployment-*。
构建需要联网及固定基础镜像，参见 README；离线运行不下载模型、库或数据。安全扫描数据库更新需要联网。
