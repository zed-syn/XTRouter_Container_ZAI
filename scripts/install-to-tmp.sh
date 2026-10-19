#!/usr/bin/env bash
# Step 0: install canonical Python bridge helpers to /tmp (same fingerprint as original pool prompt).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SLOT_COUNT="${LAB_POOL_SLOTS:-6}"

if [[ -z "${WORKER_ID:-}" ]]; then
  echo "WORKER_ID not set (start.sh should export it)." >&2
  exit 1
fi

ART="$ROOT/build/$WORKER_ID/scripts"
for f in bridge_client.py bridge_slot.py bridge_subagent_prompt.md; do
  if [[ ! -f "$ART/$f" ]]; then
    echo "Missing $ART/$f" >&2
    exit 1
  fi
done

python3 -c "import re,sys; t=open('${ART}/bridge_client.py',encoding='utf-8').read(); m=re.search(r'^WORKER_ID = \"([^\"]+)\"', t, re.M); wid=m.group(1) if m else ''; sys.exit(0 if wid=='${WORKER_ID}' else 1)" || {
  echo "WORKER_ID=${WORKER_ID} does not match baked bridge_client.py." >&2
  exit 1
}

cp "$ART/bridge_client.py" /tmp/bridge_client.py
cp "$ART/bridge_slot.py" /tmp/bridge_slot.py
cp "$ART/bridge_subagent_prompt.md" /tmp/bridge_subagent_prompt.md

python3 -c "import hashlib,secrets;print('files',hashlib.sha256(b''.join(open('/tmp/bridge_'+n,'rb').read() for n in ('client.py','slot.py','subagent_prompt.md'))).hexdigest()[:16]);[print(secrets.token_urlsafe(24)) for _ in range(int('${SLOT_COUNT}')))]"
