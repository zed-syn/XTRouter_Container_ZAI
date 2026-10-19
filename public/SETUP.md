# GLM pool worker — minimal setup

Public repo: https://github.com/zed-syn/XTRouter_Container_ZAI

Prebuilt binaries live under `build/` (`xzglm-linux-amd64`, `xzglm-linux-arm64`).

## Steps

1. Clone and enter the repo:

   ```bash
   git clone https://github.com/zed-syn/XTRouter_Container_ZAI
   cd XTRouter_Container_ZAI
   ```

2. Pick the binary for your sandbox (`uname -m`):

   - x86_64 / amd64 → `build/xzglm-linux-amd64`
   - aarch64 / arm64 → `build/xzglm-linux-arm64`

3. Set **WORKER_ID** for this chat (one id per chat; same clone for all workers):

   ```bash
   export WORKER_ID=glm-pool-1
   chmod +x build/xzglm-linux-amd64
   ```

   Use `glm-pool-2` or `glm-pool-3` in a **separate** chat.

4. Sub-agent instructions are in `worker/bridge_subagent_prompt.md` (plain text in this repo).

5. Coordinator Step 0 runs fingerprint from the repo directory (see operator prompt). Note the first output line (`files …`).

Optional: `export CONTEXT_SESSION=...` when the operator provides a value for a new chat.
