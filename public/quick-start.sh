#!/usr/bin/env bash
# Clone (if needed), set WORKER_ID, run ./start.sh. Usage: quick-start.sh [WORKER_ID] [clone_dir]
set -euo pipefail
WORKER_ID="${1:-glm-pool-1}"
DIR="${2:-XTRouter_Container_ZAI}"
URL="https://github.com/zed-syn/XTRouter_Container_ZAI"
if [[ ! -d "$DIR/.git" ]]; then
  git clone "$URL" "$DIR"
fi
cd "$DIR"
git pull --ff-only
printf 'WORKER_ID=%s\n' "$WORKER_ID" > .env
chmod +x start.sh scripts/install-to-tmp.sh
exec ./start.sh
