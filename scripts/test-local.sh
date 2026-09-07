#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1
exec python3 -m unittest discover -s tests -v
