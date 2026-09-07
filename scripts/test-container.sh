#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${IMAGE:?请指定已构建镜像}"
[[ $(id -u) != 0 ]] || { echo '请以普通用户执行测试' >&2; exit 2; }
test_root=$(mktemp -d "$PWD/outputs/container-test.XXXXXX")
export INPUT_DIR="$PWD/data/input" OUTPUT_DIR="$test_root/output"
# 只有脚本全部完成才输出 PASS。
bash scripts/run.sh > "$test_root/stdout.txt" 2> "$test_root/stderr.jsonl"
python3 - "$INPUT_DIR/smoke.txt" "$OUTPUT_DIR/smoke-result.json" <<'PY'
import hashlib,json,sys
from pathlib import Path
source=Path(sys.argv[1]).read_bytes()
result=json.loads(Path(sys.argv[2]).read_text())
assert result['sha256']==hashlib.sha256(source).hexdigest()
assert result['bytes']==len(source)
PY
set +e
bash scripts/run.sh --input /data/input/missing > "$test_root/missing.stdout" 2> "$test_root/missing.stderr"
status=$?
set -e
[[ $status == 4 ]] || { echo "错误输入应退出4，实际$status" >&2; exit 1; }
# 独立检查镜像默认 USER、只读根和挂载权限；采用同等运行约束。
docker run --rm --read-only --network none --cap-drop ALL --security-opt no-new-privileges \
 --cpus 1 --memory 512m --pids-limit 64 --tmpfs /tmp:rw,noexec,nosuid,size=64m \
 --entrypoint python "$IMAGE" -c 'import os; assert os.getuid() == 10001; print("default UID verified")'
docker run --rm --read-only --network none --cap-drop ALL --security-opt no-new-privileges \
 --user "$(id -u):$(id -g)" --cpus 1 --memory 512m --pids-limit 64 \
 --tmpfs /tmp:rw,noexec,nosuid,size=64m \
 --mount "type=bind,src=$INPUT_DIR,dst=/data/input,readonly" \
 --mount "type=bind,src=$OUTPUT_DIR,dst=/data/output" \
 --entrypoint python "$IMAGE" -c '
import errno,os
from pathlib import Path
for target in ("/app/forbidden", "/data/input/forbidden"):
    try:
        Path(target).write_text("test")
    except OSError as exc:
        assert exc.errno == errno.EROFS, (target, exc)
    else:
        raise AssertionError("unexpected write: " + target)
for target in ("/tmp/writable", "/data/output/writable"):
    p=Path(target);p.write_text("test");p.unlink()
print("filesystem restrictions verified")'
printf 'PASS: 框架容器检查通过；不是遥感算法验收。记录目录：%s\n' "$test_root"
