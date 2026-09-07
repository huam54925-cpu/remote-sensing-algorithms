# 数据盘状态（2026-09-07）

已核验 /dev/sda2：UUID 5e1b0bde-af3d-4485-b404-8a34efac7a21，ext4，挂载到 /mnt/robot_disk，可读写。df 显示总容量约 916 GiB、可用约 870 GiB。

/etc/fstab 已有按此 UUID 挂载的条目，启用 nofail、x-systemd.automount 和 5 秒设备等待。本次未修改挂载配置、分区或格式化磁盘。

项目工作目录：/mnt/robot_disk/remote_sensing_project。源码、输入影像、预期结果、运行输出和项目文档统一放在此目录。已有 robot_data 目录保持原状。

Codex outputs 中保留一份迁移时的交付快照；后续项目开发以数据盘上的目录为准，快照不会自动同步。

Docker 尚未安装。项目目录迁移不会自动迁移将来的 Docker 镜像、构建缓存或容器存储；安装时需另行配置并核验其数据目录。
