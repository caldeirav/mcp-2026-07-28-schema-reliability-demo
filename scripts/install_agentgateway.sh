#!/usr/bin/env bash
set -euo pipefail
ROOT="$(CDPATH="" cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

set -a
if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  source .env
fi
set +a

VERSION="${AGENTGATEWAY_VERSION:-1.4.1}"

if command -v agentgateway >/dev/null 2>&1; then
  echo "agentgateway already on PATH: $(command -v agentgateway)"
  agentgateway --version || true
  exit 0
fi

echo "Installing agentgateway ${VERSION} via agentgateway.dev/install"
curl -sL https://agentgateway.dev/install | bash -s -- --version "${VERSION}"
agentgateway --version
