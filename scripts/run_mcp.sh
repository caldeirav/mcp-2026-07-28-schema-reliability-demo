#!/usr/bin/env bash
set -euo pipefail
ROOT="$(CDPATH="" cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}/src/mcp${PYTHONPATH:+:$PYTHONPATH}"
uv run python "${ROOT}/src/mcp/server_strict.py" &
uv run python "${ROOT}/src/mcp/server_legacy.py" &
wait
