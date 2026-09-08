#!/usr/bin/env python3
"""Read literal KEY=VALUE configuration; never execute a shell env file."""
import os
from pathlib import Path
import sys

ALLOWED = {'IMAGE', 'INPUT_DIR', 'OUTPUT_DIR', 'WORK_DIR', 'CPU_LIMIT', 'MEMORY_LIMIT',
           'CONTAINER_NAME', 'STOP_TIMEOUT', 'RS_ALGORITHM', 'RS_INPUT', 'RS_PARAMS',
           'RS_TASK_ID'}

def parse(path):
    result = {}
    for number, raw in enumerate(Path(path).read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        key, sep, value = line.partition('=')
        key, value = key.strip(), value.strip()
        if not sep or key not in ALLOWED or key in result:
            raise ValueError(f'第 {number} 行：未知、重复或不合法的变量 {key}')
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        # Values are literals: no interpolation, substitution or inline comments.
        result[key] = value
    return result

if __name__ == '__main__':
    try:
        path = Path(sys.argv[1] if len(sys.argv) > 1 else '.env').resolve()
        env = {**os.environ, **parse(path)}
        for key in ('INPUT_DIR', 'OUTPUT_DIR', 'WORK_DIR'):
            if env.get(key):
                env[key] = str((path.parent / env[key]).resolve())
        script = Path(__file__).resolve().parent / 'run.sh'
        os.execve('/bin/bash', ['bash', str(script), *sys.argv[2:]], env)
    except (OSError, ValueError) as exc:
        print(f'配置错误：{exc}', file=sys.stderr)
        sys.exit(2)
