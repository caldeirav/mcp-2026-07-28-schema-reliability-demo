#!/usr/bin/env bash
set -euo pipefail
ROOT="$(CDPATH="" cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if ! command -v agentgateway >/dev/null 2>&1; then
  echo "agentgateway not found; run ./scripts/install_agentgateway.sh" >&2
  exit 1
fi
exec agentgateway -f "${ROOT}/src/gateway/config.yaml"
