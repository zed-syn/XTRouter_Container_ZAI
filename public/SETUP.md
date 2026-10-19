# GLM pool worker — minimal setup

Public repo: https://github.com/zed-syn/XTRouter_Container_ZAI

One shared `build/` tree (`xzglm-linux-amd64`, `xzglm-linux-arm64`). Credentials and the sub-agent prompt are baked into the release binary your operator publishes — not stored as Python in git.

## Steps

1. Clone and enter the repo:

   ```bash
   git clone https://github.com/zed-syn/XTRouter_Container_ZAI
   cd XTRouter_Container_ZAI
   ```

2. Set **WORKER_ID** for this chat (operator assigns one id per chat; same clone for all workers):

   ```bash
   printf 'WORKER_ID=%s\n' 'glm-pool-1' > .env
   ```

   Use `glm-pool-2` or `glm-pool-3` only in a **separate** chat with that id in `.env` (no rebuild when switching).

3. Install bridge to `/tmp` (Step 0):

   ```bash
   chmod +x start.sh scripts/install-to-tmp.sh
   ./start.sh
   ```

   **New GLM chat:** add `CONTEXT_SESSION=...` to `.env` if the operator provides it. If omitted, the first `./start.sh` generates one and appends it to `.env`.

4. Note the first output line (`files …`). Then **wait** — the operator sends coordinator instructions in the next GLM message (not stored in this public repo).

## Optional wrapper (one worker per invocation)

```bash
./public/quick-start.sh              # WORKER_ID=glm-pool-1
./public/quick-start.sh glm-pool-2
./public/quick-start.sh glm-pool-3
```

Do not build from source in this public repo.
