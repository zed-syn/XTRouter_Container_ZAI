# GLM pool worker — minimal setup

Public repo: https://github.com/zed-syn/XTRouter_Container_ZAI

No secrets in git. Credentials are baked under `build/<worker>/scripts/` in the release your operator publishes.

## Steps

1. Clone and enter the repo:

   ```bash
   git clone https://github.com/zed-syn/XTRouter_Container_ZAI
   cd XTRouter_Container_ZAI
   ```

2. Set **one** variable — which pool worker this chat uses:

   ```bash
   cp .env.example .env
   # edit: WORKER_ID=glm-pool-1   (or glm-pool-2 / glm-pool-3 — operator assigns)
   ```

   Or: `printf 'WORKER_ID=%s\n' 'glm-pool-1' > .env`

3. Install bridge helpers to `/tmp` (Step 0):

   ```bash
   chmod +x start.sh scripts/install-to-tmp.sh
   ./start.sh
   ```

4. Note the first output line (`files …`). Then **wait** — the operator pastes the full coordinator prompt into the GLM chat (generated locally by `./build.sh`, not stored in this repo).

Optional one-liner wrapper: `./public/quick-start.sh glm-pool-1`

Do not build from source in this public repo.
