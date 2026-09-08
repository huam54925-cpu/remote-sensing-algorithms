# 操作手册 1.1

- 可编辑排版源码：`operations-manual.tex`。
- 可复制指令的文本版：`operations-manual.md`。
- 编译：在项目根目录执行 `bash docs/manual/build.sh`。
- PDF：`output/pdf/remote-sensing-operations-manual.pdf`。
- 校验：在项目根目录执行 `sha256sum -c output/pdf/remote-sensing-operations-manual.pdf.sha256`。

使用本机 XeLaTeX、ctex、fvextra、Noto CJK 和 DejaVu Sans Mono；编译不需要 shell-escape，也不执行文档中的运维命令。中间文件保存在 `tmp/pdfs/manual-build/`，不会改动现有算法、测试或安装脚本。

手册分 12 章，涵盖环境、配置、CPU 示例、日志与停止、Docker GPU、Kubernetes CPU/GPU、维护、扫描与离线交付、Git 推送、排错和真实算法接入。环境结论引用 2026-09-08 已保存的测试证据；本次仅生成文档。

1.1 版按“用途、执行前提、需填写内容、执行命令、参数说明、终端输出、完成判定”组织操作条目；配置、命令和输出分开排版。实测摘录注明来源，示意输出不作为本次重新运行证据。

按用户要求未逐页视觉检查；交付前执行 LaTeX 编译日志检查、全部命令块 Bash 语法检查以及 PDF 文本与目录检查。PDF 自动折行不应作为 shell 命令中的真实换行，复杂命令以源码和现有脚本为准。

当前 `scripts/package.sh` 的固定文档清单未包含此手册；本次没有改打包逻辑、重制旧交付包或推送 Git。
