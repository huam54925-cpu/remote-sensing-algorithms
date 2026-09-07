#!/usr/bin/env bash
# Fresh Ubuntu installation only. Preserves project files and existing disk data.
set -Eeuo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
[[ $EUID == 0 ]] || { echo '请使用 sudo bash 执行本脚本' >&2; exit 2; }
owner=${SUDO_USER:-xialain}
[[ "$owner" == xialain ]] || { echo '本脚本为 xialain 准备，请从该用户的终端用 sudo 执行' >&2; exit 2; }
disk=/mnt/robot_disk
uuid=5e1b0bde-af3d-4485-b404-8a34efac7a21
# Trigger existing systemd automount, then verify actual filesystem identity.
ls "$disk" >/dev/null
[[ $(findmnt -rn -t ext4 -T "$disk" -o UUID) == "$uuid" ]] || { echo '目标盘 UUID 或文件系统不符，停止' >&2; exit 2; }
for pkg in docker.io docker-ce containerd containerd.io; do
  if dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -qx 'install ok installed'; then
    echo "已存在 $pkg，请先检查现有安装；本脚本仅用于首次安装。" >&2; exit 2
  fi
done
for path in /etc/docker/daemon.json /etc/containerd/config.toml "$disk/docker-engine" "$disk/containerd"; do
  [[ ! -e "$path" ]] || { echo "已存在 $path，停止以免覆盖" >&2; exit 2; }
done
for unit in docker.service docker.socket containerd.service; do
  [[ ! -e /etc/systemd/system/$unit && ! -L /etc/systemd/system/$unit ]] || { echo "已有 $unit 永久覆盖配置，需先核查" >&2; exit 2; }
  runtime="/run/systemd/system/$unit"
  if [[ -e "$runtime" || -L "$runtime" ]]; then
    [[ -L "$runtime" && $(readlink "$runtime") == /dev/null ]] || { echo "已有未知 $unit 临时配置，停止" >&2; exit 2; }
  fi
done
log_dir="$disk/docker-install-records/$(date -u +%Y%m%dT%H%M%SZ)-$$"
install -d -m 0755 "$log_dir"
exec > >(tee "$log_dir/install.log") 2>&1
masked=0
if [[ $(readlink /run/systemd/system/docker.service 2>/dev/null || true) == /dev/null ]]; then masked=1; fi
trap 'rc=$?; echo "安装中断，退出码 $rc。记录：$log_dir/install.log"; if (( masked )); then echo "为避免误用系统盘，Docker/containerd 的临时服务屏蔽保留；请发回错误记录后继续处理。"; fi; exit "$rc"' ERR
# Only Ubuntu repositories are needed for these distribution packages.
# Keep unrelated package sources and their cached indexes unchanged.
[[ -f /etc/apt/sources.list.d/ubuntu.sources ]] || { echo '缺少 Ubuntu deb822 软件源文件'; false; }
apt_options=(-o Dir::Etc::sourcelist=/etc/apt/sources.list.d/ubuntu.sources
  -o Dir::Etc::sourceparts=- -o APT::Get::List-Cleanup=false
  -o Acquire::Retries=0 -o Acquire::http::Timeout=15 -o Acquire::https::Timeout=15)
apt-get "${apt_options[@]}" -o APT::Update::Error-Mode=any update
# Prevent package post-install scripts from starting engines on the system disk.
systemctl mask --runtime docker.service docker.socket containerd.service
masked=1
apt-get "${apt_options[@]}" install -y --no-install-recommends docker.io docker-compose-v2 docker-buildx
install -d -m 0700 "$disk/docker-engine" "$disk/containerd"
install -d -m 0755 /etc/docker /etc/containerd /etc/systemd/system/docker.service.d /etc/systemd/system/containerd.service.d
[[ ! -e /etc/docker/daemon.json ]] || { echo '安装过程产生了 daemon.json，需先检查后再配置'; false; }
cat > /etc/docker/daemon.json <<'JSON'
{
  "data-root": "/mnt/robot_disk/docker-engine",
  "log-driver": "local",
  "log-opts": {"max-size": "10m", "max-file": "3"}
}
JSON
if [[ -f /etc/containerd/config.toml ]]; then
  cp -a /etc/containerd/config.toml "$log_dir/containerd-config.before.toml"
fi
# Use the installed containerd's own defaults to match its configuration version.
containerd config default > "$log_dir/containerd-default.toml"
python3 - "$log_dir/containerd-default.toml" <<'PY'
from pathlib import Path
import sys,re
text=Path(sys.argv[1]).read_text()
text,count=re.subn(r'^root\s*=.*$', 'root = "/mnt/robot_disk/containerd"',text,count=1,flags=re.M)
assert count==1, 'containerd default root not found'
Path('/etc/containerd/config.toml').write_text(text)
PY
for unit in docker containerd; do
cat > "/etc/systemd/system/$unit.service.d/data-disk.conf" <<'UNIT'
[Unit]
RequiresMountsFor=/mnt/robot_disk
[Service]
ExecStartPre=/usr/bin/mountpoint -q /mnt/robot_disk
UNIT
done
dockerd --validate --config-file /etc/docker/daemon.json
containerd --config /etc/containerd/config.toml config dump > "$log_dir/containerd-effective.toml"
systemctl daemon-reload
systemctl unmask --runtime docker.service docker.socket containerd.service
masked=0
systemctl enable --now containerd.service docker.service
[[ $(docker info --format '{{.DockerRootDir}}') == "$disk/docker-engine" ]]
python3 - "$log_dir/containerd-effective.toml" <<'PY'
import sys,tomllib
with open(sys.argv[1],'rb') as f: config=tomllib.load(f)
assert config['root']=='/mnt/robot_disk/containerd'
PY
usermod -aG docker "$owner"
# A fresh process receives the new group membership without altering this terminal.
runuser -u "$owner" -- docker info > "$log_dir/docker-info.txt"
docker version > "$log_dir/docker-version.txt"
docker compose version
docker buildx version
findmnt -T "$disk/docker-engine"
findmnt -T "$disk/containerd"
trap - ERR
if runuser -u "$owner" -- docker run --rm hello-world > "$log_dir/hello-world.txt" 2>&1; then
  echo '安装、数据目录检查及普通用户 hello-world 测试通过。'
else
  echo 'Docker 已配置并启动；hello-world 测试失败，请检查下方错误（可能涉及镜像下载网络）：'
  cat "$log_dir/hello-world.txt"
  echo "记录目录：$log_dir"
  exit 10
fi
echo "记录目录：$log_dir"
echo '当前已打开的终端需注销重新登录，或执行 newgrp docker，才能直接使用新用户组权限。'
echo 'Docker 程序本体和系统服务文件在系统分区；镜像、容器和默认构建缓存位于数据盘。'
