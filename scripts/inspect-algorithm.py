#!/usr/bin/env python3
"""Read-only intake hints. Does not import/execute received source or print secrets."""
import argparse
import json
from pathlib import Path
import re

p=argparse.ArgumentParser(description='只读扫描算法目录，输出入口/依赖/GPU/联网/路径/信号处理线索；不执行代码')
p.add_argument('directory',type=Path)
a=p.parse_args()
if not a.directory.is_dir(): p.error('目录不存在')
patterns={
    'gpu':r'\b(cuda|cupy|tensorflow|torch|onnxruntime|device)\b',
    'network':r'\b(requests|urllib|httpx|socket|boto3|download|https?)\b',
    'entrypoint':r'__main__|argparse|click\.command|typer|FastAPI|Flask',
    'subprocess':r'\b(subprocess|Popen|os\.system|multiprocessing)\b',
    'stop':r'SIGTERM|SIGINT|signal\.|KeyboardInterrupt|cancel',
    'file_io':r'\b(open|imwrite|to_csv|save|rasterio\.open)\s*\(',
}
result={'root':str(a.directory.resolve()),'warning':'静态线索不是实际运行证据；未执行源代码',
        'dependencies':[],'hints':[],'skipped':[]}
for path in a.directory.rglob('*'):
    if any(x in ('.git','.venv','node_modules','__pycache__') for x in path.relative_to(a.directory).parts):continue
    if path.is_symlink() or not path.is_file():continue
    rel=str(path.relative_to(a.directory))
    if path.name in ('Dockerfile','pyproject.toml','environment.yml','requirements.txt','requirements.lock','package.json'):
        result['dependencies'].append(rel)
    if path.suffix not in ('.py','.sh','.cpp','.cu','.c','.h','.yml','.yaml','.toml'):continue
    if path.stat().st_size>2*1024*1024:
        result['skipped'].append(rel);continue
    try: lines=path.read_text().splitlines()
    except (UnicodeError,OSError):continue
    for number,line in enumerate(lines,1):
        for category,regex in patterns.items():
            if re.search(regex,line,re.I):
                result['hints'].append({'file':rel,'line':number,'category':category})
print(json.dumps(result,ensure_ascii=False,indent=2))
