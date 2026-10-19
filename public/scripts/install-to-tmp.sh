#!/usr/bin/env bash
# Step 0: copy xzglm + sub-agent prompt to /tmp; print fingerprint + nonces.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SLOT_COUNT="${LAB_POOL_SLOTS:-6}"

if [[ -z "${WORKER_ID:-}" ]]; then
  echo "WORKER_ID not set (start.sh should export it)." >&2
  exit 1
fi

ART="$ROOT/build/$WORKER_ID"
BIN="$ART/xzglm-linux-amd64"
PROMPT="$ART/bridge_subagent_prompt.md"

if [[ ! -f "$BIN" || ! -f "$PROMPT" ]]; then
  echo "Missing baked artifacts under $ART" >&2
  exit 1
fi

cp "$BIN" /tmp/xzglm
chmod +x /tmp/xzglm
cp "$PROMPT" /tmp/bridge_subagent_prompt.md

exec /tmp/xzglm fingerprint "$SLOT_COUNT" /tmp/xzglm /tmp/bridge_subagent_prompt.md
