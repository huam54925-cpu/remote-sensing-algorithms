# 环境检查（2026-09-07）

| 项目 | 实际结果 |
|---|---|
| Linux | Ubuntu 26.04.1 LTS |
| CPU 架构 | x86_64，即 amd64 |
| 内存 | 约 30 GiB，总可用约 24 GiB（采样时） |
| swap | 8 GiB |
| 当前项目所在分区 | /dev/nvme0n1p6，df 显示 98 GiB，剩余约 52 GiB |
| Python | 3.14.4 |
| Git | 2.53.0 |
| Docker / Compose | 命令未找到，服务端未验证 |
| 其他容器运行工具 | 未找到 podman、nerdctl、containerd 命令 |
| 待挂载数据盘 | /dev/sda2，lsblk 显示 931.5 GiB、ext4；最初无挂载点 |
| 已挂载的另一数据盘 | /dev/sdb1，931.5 GiB、NTFS |

这些是开发机信息，不能作为甲方目标环境要求。约 1 TB ext4 分区的挂载/迁移结果另见 storage-status.md。检查期间未安装软件、未格式化分区。
