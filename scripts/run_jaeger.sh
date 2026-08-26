#!/usr/bin/env bash
set -euo pipefail
ROOT="$(CDPATH="" cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Podman Desktop installs here; it is often missing from non-login PATH.
PATH="/opt/podman/bin:/opt/homebrew/bin:/usr/local/bin:${PATH}"

IMAGE="jaegertracing/all-in-one:1.76.0"
NAME="mcp-demo-jaeger"

find_engine() {
  local candidate
  for candidate in podman docker; do
    if command -v "${candidate}" >/dev/null 2>&1; then
      command -v "${candidate}"
      return 0
    fi
  done
  for candidate in /opt/podman/bin/podman /opt/homebrew/bin/podman /usr/local/bin/podman \
    /opt/homebrew/bin/docker /usr/local/bin/docker; do
    if [[ -x "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  return 1
}

# macOS/Windows Podman talks to a Linux VM. A stopped VM looks like
# "dial tcp 127.0.0.1:… connection refused".
ensure_podman_vm() {
  local engine="$1"
  if [[ "$(basename "${engine}")" != "podman" ]]; then
    return 0
  fi
  if "${engine}" info >/dev/null 2>&1; then
    return 0
  fi

  echo "Podman VM is not running; starting it (podman machine start)…" >&2
  if ! "${engine}" machine list --format '{{.Name}}' 2>/dev/null | grep -q .; then
    echo "No Podman machine found; running podman machine init…" >&2
    "${engine}" machine init
  fi
  "${engine}" machine start

  local i
  for i in $(seq 1 60); do
    if "${engine}" info >/dev/null 2>&1; then
      echo "Podman VM is ready." >&2
      return 0
    fi
    sleep 2
  done
  echo "Podman VM did not become reachable. Try: podman machine start" >&2
  echo "Then re-run ./scripts/run_jaeger.sh" >&2
  exit 1
}

if ! engine="$(find_engine)"; then
  echo "podman not found; install Podman (https://podman.io/) to run Jaeger" >&2
  echo "Docker is accepted as a fallback if it is already on PATH." >&2
  exit 1
fi

echo "Using container engine: ${engine}" >&2
echo "Jaeger UI: http://127.0.0.1:16686" >&2
echo "OTLP gRPC: 127.0.0.1:4317 (agentgateway frontendPolicies.tracing)" >&2

ensure_podman_vm "${engine}"

# Same image and loopback ports as compose.yaml. Prefer `podman run` so Compose
# is not required. --replace is Podman-only; Docker gets an explicit rm.
if [[ "$(basename "${engine}")" == "podman" ]]; then
  exec "${engine}" run --rm --replace --name "${NAME}" \
    -e COLLECTOR_OTLP_ENABLED=true \
    -p 127.0.0.1:16686:16686 \
    -p 127.0.0.1:4317:4317 \
    -p 127.0.0.1:4318:4318 \
    "${IMAGE}"
fi

"${engine}" rm -f "${NAME}" >/dev/null 2>&1 || true
exec "${engine}" run --rm --name "${NAME}" \
  -e COLLECTOR_OTLP_ENABLED=true \
  -p 127.0.0.1:16686:16686 \
  -p 127.0.0.1:4317:4317 \
  -p 127.0.0.1:4318:4318 \
  "${IMAGE}"
