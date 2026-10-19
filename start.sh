#!/usr/bin/env bash
# Load WORKER_ID from .env, install shared Python bridge helpers from build/scripts/ to /tmp.
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

ART="$ROOT/build/scripts"
if [[ ! -f "$ART/bridge_client.py" ]]; then
  echo "Missing $ART/bridge_client.py — use an operator-baked release." >&2
  exit 1
fi

if [[ -z "${CONTEXT_SESSION:-}" ]]; then
  CONTEXT_SESSION="$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")"
  printf '\nCONTEXT_SESSION=%s\n' "$CONTEXT_SESSION" >> .env
  export CONTEXT_SESSION
fi

export WORKER_ID
export CONTEXT_SESSION
export LAB_POOL_SLOTS="${LAB_POOL_SLOTS:-6}"

exec bash "$ROOT/scripts/install-to-tmp.sh"
