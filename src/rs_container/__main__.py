"""Batch interface scaffold. smoke is a wiring check, not a spectral index."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import tempfile
import shutil
import sys
import time
import uuid
from datetime import datetime, timezone
from . import __version__

ALGORITHMS = ("kNDVI", "EVI", "SAVI", "MNDWI", "AWEI", "NDBI", "NBR", "BSI", "NDMI", "LSWI", "FVC", "NDSI", "NDGI")

def log(level, task_id, message, **fields):
    print(json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level, "module": "rs_container", "task_id": task_id,
        "message": message, **fields}, ensure_ascii=False), file=sys.stderr, flush=True)

class Cancelled(BaseException):
    def __init__(self, signum):
        self.signum = signum

def cancel(signum, frame):
    raise Cancelled(signum)

class InvalidArguments(Exception):
    pass

class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise InvalidArguments(message)

def main(argv=None):
    task_id = os.getenv("RS_TASK_ID") or str(uuid.uuid4())
    started = time.perf_counter()
    p = Parser(description="遥感批处理接口；已接入 MNDWI、KMEANS 示例，smoke 仅验证文件流转。CLI 优先于环境变量。")
    p.add_argument("--algorithm", default=os.getenv("RS_ALGORITHM"), help="算法名 / RS_ALGORITHM；当前支持 MNDWI、KMEANS 和 smoke")
    p.add_argument("--input", default=os.getenv("RS_INPUT"), help="输入文件路径 / RS_INPUT")
    p.add_argument("--output-dir", default=os.getenv("RS_OUTPUT_DIR"), help="输出目录 / RS_OUTPUT_DIR")
    p.add_argument("--params", default=os.getenv("RS_PARAMS", "{}"), help="JSON 对象 / RS_PARAMS；smoke 只接受空对象")
    p.add_argument("--task-id", default=task_id, help="任务 ID / RS_TASK_ID；默认生成 UUID")
    p.add_argument("--list", action="store_true", help="列出接入状态")
    p.add_argument("--healthcheck", action="store_true", help="仅检查 Python 和入口；不代表算法或挂载健康")
    p.add_argument("--version", action="version", version=__version__)
    try:
        args = p.parse_args(argv)
        task_id = args.task_id
        if args.list:
            status = dict.fromkeys(ALGORITHMS, "not_implemented")
            status["MNDWI"] = "implemented_example"
            status["KMEANS"] = "implemented_example"
            print(json.dumps({"smoke": "diagnostic_only", **status}, ensure_ascii=False))
            return 0
        if args.healthcheck:
            log("INFO", task_id, "framework_health_ok", version=__version__)
            return 0
        if not all((args.algorithm, args.input, args.output_dir)):
            raise InvalidArguments("必须提供 algorithm、input、output-dir（命令行或对应环境变量）")
        try:
            params = json.loads(args.params)
        except (ValueError, TypeError) as exc:
            raise InvalidArguments("params 必须为 JSON 对象") from exc
        if not isinstance(params, dict):
            raise InvalidArguments("params 必须为 JSON 对象")
        src = Path(args.input)
        if not src.is_file():
            log("ERROR", task_id, "输入文件不存在或不是普通文件")
            return 4
        out = Path(args.output_dir)
        if args.algorithm in ("MNDWI", "KMEANS"):
            staging = None
            try:
                if args.algorithm == "MNDWI":
                    from .mndwi import calculate
                else:
                    from .kmeans import calculate
                # Reserve the output directory exclusively. Existing mount root is allowed,
                # but every algorithm publishes into a dedicated result subdirectory.
                final = out / "result"
                out.mkdir(parents=True, exist_ok=True)
                if final.exists() or final.is_symlink():
                    raise FileExistsError("result 已存在，请使用新的输出目录")
                lock = out / ".rs-lock"
                try:
                    lock.mkdir()
                except FileExistsError:
                    raise FileExistsError("输出目录正在使用或曾异常终止；请使用新目录")
                try:
                    staging = Path(tempfile.mkdtemp(prefix=".partial-", dir=out))
                    log("INFO", task_id, "algorithm_started", algorithm=args.algorithm)
                    result = calculate(src, staging, params)
                    result["output"] = str(final / Path(result["output"]).name)
                    (staging / "success.json").write_text(json.dumps({
                        "status": "completed", "task_id": task_id,
                        "algorithm": args.algorithm, **result}, ensure_ascii=False, indent=2))
                    staging.rename(final)
                    staging = None
                finally:
                    if staging is not None:
                        shutil.rmtree(staging, ignore_errors=True)
                    lock.rmdir()
            except (ValueError, FileExistsError) as exc:
                log("ERROR", task_id, str(exc), algorithm=args.algorithm)
                return 2 if isinstance(exc, ValueError) else 5
            except OSError as exc:
                log("ERROR", task_id, "输入或输出文件错误", algorithm=args.algorithm,
                    error_type=type(exc).__name__)
                return 4
            log("INFO", task_id, "algorithm_completed", algorithm=args.algorithm,
                elapsed_seconds=time.perf_counter()-started,
                process_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                **result)
            return 0
        if args.algorithm != "smoke":
            log("ERROR", task_id, "算法未接入或名称未知", algorithm=args.algorithm)
            return 3
        if params:
            raise InvalidArguments("smoke 不接受算法参数")
        digest = hashlib.sha256()
        size = 0
        try:
            with src.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
                    size += len(chunk)
        except OSError:
            log("ERROR", task_id, "输入文件不可读")
            return 4
        result = {"kind": "framework_smoke_only", "algorithm": "smoke", "task_id": task_id,
                  "sha256": digest.hexdigest(), "bytes": size}
        try:
            out.mkdir(parents=True, exist_ok=True)
            # Exclusive creation avoids replacing previous results or following an existing symlink.
            with (out / "smoke-result.json").open("x", encoding="utf-8") as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
        except OSError:
            log("ERROR", task_id, "输出不可写或 smoke-result.json 已存在；请使用新的输出目录")
            return 5
        log("INFO", task_id, "framework_smoke_completed", elapsed_seconds=time.perf_counter()-started,
            process_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, **{"bytes": size})
        return 0
    except InvalidArguments as exc:
        log("ERROR", task_id, str(exc))
        return 2
    except Cancelled as exc:
        log("WARNING", task_id, "task_cancelled", signal=exc.signum)
        return 128 + exc.signum
    except KeyboardInterrupt:
        log("ERROR", task_id, "任务被中断")
        return 130
    except Exception as exc:
        log("ERROR", task_id, "未处理错误", error_type=type(exc).__name__)
        return 1

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, cancel)
    signal.signal(signal.SIGINT, cancel)
    sys.exit(main())
