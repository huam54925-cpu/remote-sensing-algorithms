# 0.3.0 接口说明

当前完整参数、结果目录、日志与停止行为见 [部署操作说明](deployment-guide.md)。以下为 0.1.x 历史接口草案，其中未接入 GeoTIFF 的描述已被后续实现取代。

# 批处理接口草案

| CLI | 环境变量 | 默认 |
|---|---|---|
| --algorithm | RS_ALGORITHM | 无，处理任务必填 |
| --input | RS_INPUT | 无，普通输入文件必填 |
| --output-dir | RS_OUTPUT_DIR | 无，处理任务必填 |
| --params | RS_PARAMS | {}，JSON 对象 |
| --task-id | RS_TASK_ID | 自动 UUID |

CLI 优先于环境变量。--help/-h、--list、--healthcheck、--version 是信息操作；无算法计算。run.sh 给 smoke 提供默认环境变量，直接调用 Python 无这些默认路径。大影像按文件路径传入，不能嵌入 RS_PARAMS 或长命令行。

smoke 流式读取文件，在输出卷写 smoke-result.json：kind、algorithm、task_id、sha256、bytes。输入不会复制到结果目录。框架不识别 GeoTIFF，也未校验地理坐标或像元值。实际算法接口须在接入时定义输入波段清单/反射率缩放/nodata/输出 CRS 等。

| 退出码 | 含义 |
|---|---|
| 0 | 本次操作成功（信息操作或 smoke，不表示指数已实现） |
| 1 | 未处理运行错误 |
| 2 | 缺少/非法参数，params 不是 JSON 对象或 smoke 收到非空参数 |
| 3 | 算法名称未知或尚未接入 |
| 4 | 输入不存在、不是文件或不可读 |
| 5 | 输出不可写或结果已存在 |
| 130 | 用户中断 |

容器启动失败可能由 Docker 返回 125/126/127；被 SIGKILL/SIGTERM 终止常见为 137/143，需联合 Docker/Kubernetes 状态判断，不能只凭 137 判定 OOM。进程峰值 RSS 单位 KiB，当前基于 Linux resource.getrusage，不包含子进程、缓存和整个容器 cgroup 内存。

框架以 exec 形式启动 Python，终止信号能到达进程；未实现算法取消/断点恢复。禁止把健康检查的成功视作数据可用或核心算法健康。服务类接入时需另行实现规范要求的优雅终止。
