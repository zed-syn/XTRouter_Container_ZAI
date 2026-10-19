#!/usr/bin/env bash
# Load WORKER_ID from .env, install xzglm bridge to /tmp.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source ./.env
  set +a
fi

if [[ -z "${WORKER_ID:-}" ]]; then
  echo "Missing WORKER_ID. Copy .env.example to .env and set WORKER_ID (e.g. glm-pool-1)." >&2
  exit 1
fi

case "$WORKER_ID" in
  glm-pool-1|glm-pool-2|glm-pool-3) ;;
  *)
    echo "Invalid WORKER_ID=$WORKER_ID (allowed: glm-pool-1, glm-pool-2, glm-pool-3)." >&2
    exit 1
    ;;
esac

ARCH=""
case "$(uname -m 2>/dev/null || echo unknown)" in
  x86_64|amd64) ARCH=amd64 ;;
  aarch64|arm64) ARCH=arm64 ;;
esac
if [[ -n "$ARCH" && ! -f "$ROOT/build/xzglm-linux-$ARCH" ]]; then
  echo "Missing $ROOT/build/xzglm-linux-$ARCH — use an operator-baked release." >&2
  exit 1
fi

if [[ -z "${CONTEXT_SESSION:-}" ]]; then
  if command -v openssl >/dev/null 2>&1; then
    CONTEXT_SESSION="$(openssl rand -base64 18 | tr -d '/+=' | head -c 32)"
  else
    CONTEXT_SESSION="$(head -c 24 /dev/urandom | base64 | tr -d '/+=' | head -c 32)"
  fi
  printf '\nCONTEXT_SESSION=%s\n' "$CONTEXT_SESSION" >> .env
  export CONTEXT_SESSION
fi

export WORKER_ID
export CONTEXT_SESSION
export LAB_POOL_SLOTS="${LAB_POOL_SLOTS:-6}"

exec bash "$ROOT/scripts/install-to-tmp.sh"
