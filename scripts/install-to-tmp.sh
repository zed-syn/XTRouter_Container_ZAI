#!/usr/bin/env bash
# Step 0: install canonical Python bridge helpers to /tmp (honors WORKER_ID + CONTEXT_SESSION from env).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SLOT_COUNT="${LAB_POOL_SLOTS:-6}"

if [[ -z "${WORKER_ID:-}" ]]; then
  echo "WORKER_ID not set (start.sh should export it)." >&2
  exit 1
fi

ART="$ROOT/build/scripts"
for f in bridge_client.py bridge_slot.py bridge_subagent_prompt.md; do
  if [[ ! -f "$ART/$f" ]]; then
    echo "Missing $ART/$f" >&2
    exit 1
  fi
done

python3 - <<PY
import re, sys
t = open("${ART}/bridge_client.py", encoding="utf-8").read()
if not re.search(r'^WORKER_TOKENS\s*=\s*\{', t, re.M):
    sys.exit("bridge_client.py missing WORKER_TOKENS map")
wid = "${WORKER_ID}"
if not re.search(r'"%s"\s*:' % re.escape(wid), t):
    sys.exit("WORKER_ID=%s not in baked WORKER_TOKENS" % wid)
PY

export WORKER_ID
export CONTEXT_SESSION="${CONTEXT_SESSION:-}"

cp "$ART/bridge_client.py" /tmp/bridge_client.py
cp "$ART/bridge_slot.py" /tmp/bridge_slot.py
cp "$ART/bridge_subagent_prompt.md" /tmp/bridge_subagent_prompt.md

python3 -c "import hashlib,secrets;print('files',hashlib.sha256(b''.join(open('/tmp/bridge_'+n,'rb').read() for n in ('client.py','slot.py','subagent_prompt.md'))).hexdigest()[:16]);[print(secrets.token_urlsafe(24)) for _ in range(int('${SLOT_COUNT}')))]"
