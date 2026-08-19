#!/usr/bin/env bash
set -euo pipefail
ROOT="$(CDPATH="" cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ $# -lt 1 ]]; then
  echo "usage: $0 {legacy|strict|both} [prompt-file]" >&2
  exit 1
fi
export PYTHONPATH="${ROOT}/src/agent:${ROOT}/src/mcp${PYTHONPATH:+:$PYTHONPATH}"
exec uv run python -m compare --contract "$1" ${2:+--prompt "$2"}
