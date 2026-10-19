#!/usr/bin/env bash
# Step 0: install xzglm bridge to /tmp (honors WORKER_ID + CONTEXT_SESSION from env).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SLOT_COUNT="${LAB_POOL_SLOTS:-6}"

if [[ -z "${WORKER_ID:-}" ]]; then
  echo "WORKER_ID not set (start.sh should export it)." >&2
  exit 1
fi

case "$(uname -s)" in
  Linux) ;;
  *)
    echo "install-to-tmp.sh expects Linux (GLM sandbox)." >&2
    exit 1
    ;;
esac

case "$(uname -m)" in
  x86_64|amd64) ARCH=amd64 ;;
  aarch64|arm64) ARCH=arm64 ;;
  *)
    echo "Unsupported architecture: $(uname -m)" >&2
    exit 1
    ;;
esac

SRC="$ROOT/build/xzglm-linux-$ARCH"
if [[ ! -f "$SRC" ]]; then
  echo "Missing $SRC — use an operator-baked release." >&2
  exit 1
fi

cp "$SRC" /tmp/xzglm
chmod +x /tmp/xzglm

export WORKER_ID
export CONTEXT_SESSION="${CONTEXT_SESSION:-}"

/tmp/xzglm write-prompt /tmp/bridge_subagent_prompt.md
/tmp/xzglm fingerprint "$SLOT_COUNT"
