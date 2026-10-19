#!/usr/bin/env bash
# Load WORKER_ID from .env, install Python bridge helpers from build/<worker>/scripts/ to /tmp.
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

ART="$ROOT/build/$WORKER_ID/scripts"
if [[ ! -f "$ART/bridge_client.py" ]]; then
  echo "Missing $ART/bridge_client.py — use a baked release for this worker." >&2
  exit 1
fi

export WORKER_ID
export LAB_POOL_SLOTS="${LAB_POOL_SLOTS:-6}"

exec bash "$ROOT/scripts/install-to-tmp.sh"
