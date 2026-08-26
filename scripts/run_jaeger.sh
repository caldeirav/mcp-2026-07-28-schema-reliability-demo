#!/usr/bin/env bash
set -euo pipefail
ROOT="$(CDPATH="" cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found; install Docker Desktop (or an equivalent) to run Jaeger" >&2
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  compose=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  compose=(docker-compose)
else
  echo "docker compose not found; install the Docker Compose plugin" >&2
  exit 1
fi

echo "Jaeger UI: http://127.0.0.1:16686" >&2
echo "OTLP gRPC: 127.0.0.1:4317 (agentgateway frontendPolicies.tracing)" >&2
exec "${compose[@]}" -f "${ROOT}/compose.yaml" up --remove-orphans
