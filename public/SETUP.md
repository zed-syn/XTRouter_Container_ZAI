# GLM pool worker — minimal setup

Public repo: https://github.com/zed-syn/XTRouter_Container_ZAI

One shared `build/` tree (`xzglm-linux-amd64`, `xzglm-linux-arm64`). Credentials and the sub-agent prompt are baked into the release binary your operator publishes — not stored as Python in git.

## Steps

1. Clone and enter the repo:

   ```bash
   git clone https://github.com/zed-syn/XTRouter_Container_ZAI
   cd XTRouter_Container_ZAI
   ```

2. Set **WORKER_ID** — which pool worker this chat uses (no rebuild when switching):

   ```bash
   cp .env.example .env
   # edit: WORKER_ID=glm-pool-1   (or glm-pool-2 / glm-pool-3 — operator assigns)
   ```

   Or: `printf 'WORKER_ID=%s\n' 'glm-pool-1' > .env`

3. Install bridge to `/tmp` (Step 0):

   ```bash
   chmod +x start.sh scripts/install-to-tmp.sh
   ./start.sh
   ```

   **New GLM chat:** use a new `CONTEXT_SESSION` (operator may give you one line to add to `.env`). If you omit it, the first `./start.sh` generates one and appends it to `.env`.

4. Note the first output line (`files …`). Then **wait** — the operator pastes the full coordinator prompt into the GLM chat (generated locally by `./build.sh`, not stored in this repo).

Optional one-liner wrapper: `./public/quick-start.sh glm-pool-1`

Do not build from source in this public repo.
