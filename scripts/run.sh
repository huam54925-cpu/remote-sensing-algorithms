#!/usr/bin/env bash
set -euo pipefail
: "${IMAGE:?请指定已构建的镜像标签或 digest}"
: "${INPUT_DIR:?请指定宿主机输入目录}"
: "${OUTPUT_DIR:?请指定新的宿主机输出目录}"
mkdir -p "$OUTPUT_DIR"
work_dir=${WORK_DIR:-"$OUTPUT_DIR/work"}
mkdir -p "$work_dir"
work_dir=$(realpath "$work_dir")
name=${CONTAINER_NAME:-rs-$(date +%s)-$$}
stop_timeout=${STOP_TIMEOUT:-10}
[[ "$stop_timeout" =~ ^[0-9]+$ ]] || { echo "STOP_TIMEOUT 必须为非负整数" >&2; exit 2; }
input_dir=$(realpath "$INPUT_DIR")
output_dir=$(realpath "$OUTPUT_DIR")
[[ -d "$input_dir" ]] || { echo '输入目录不存在' >&2; exit 2; }
# 使用本机普通用户写入挂载卷，避免 chmod 777；镜像默认用户为 10001。
[[ $(id -u) != 0 ]] || { echo '请使用普通用户运行' >&2; exit 2; }
params=${RS_PARAMS-'{}'}
algorithm=${RS_ALGORITHM:-smoke}
input=${RS_INPUT:-/data/input/smoke.txt}
task_id=${RS_TASK_ID:-}
command_args=(--algorithm "$algorithm" --input "$input" --output-dir /data/output --params "$params")
if [[ -n "$task_id" ]]; then
  command_args+=(--task-id "$task_id")
fi
exec docker run --rm --init --name "$name" --stop-timeout "$stop_timeout" --read-only --network none --cap-drop ALL \
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" \
  --cpus "${CPU_LIMIT:-1}" --memory "${MEMORY_LIMIT:-512m}" --pids-limit 128 \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --mount "type=bind,src=$input_dir,dst=/data/input,readonly" \
  --mount "type=bind,src=$output_dir,dst=/data/output" \
  --mount "type=bind,src=$work_dir,dst=/data/work" \
  -e "RS_ALGORITHM=$algorithm" \
  -e "RS_INPUT=$input" \
  -e RS_OUTPUT_DIR=/data/output -e "RS_PARAMS=$params" \
  -e "RS_TASK_ID=$task_id" "$IMAGE" "${command_args[@]}" "$@"
