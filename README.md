Welcome!

This repository ships prebuilt worker artifacts for the GLM pool container demo (layout like MiniMax: flat `build/`).

Steps:

1. Clone the repository:

   git clone https://github.com/zed-syn/XTRouter_Container_ZAI
   cd XTRouter_Container_ZAI

2. Set **WORKER_ID** in `.env` (switch pool worker without rebuild):

   cp .env.example .env
   # edit WORKER_ID=glm-pool-1   (or glm-pool-2 / glm-pool-3)

3. Install the bridge to `/tmp` (Step 0 of the coordinator prompt):

   chmod +x start.sh scripts/install-to-tmp.sh
   ./start.sh

   This copies `build/xzglm-linux-*` to `/tmp/xzglm` and writes `/tmp/bridge_subagent_prompt.md`.

   On first run, `CONTEXT_SESSION` is added to `.env` for this chat. For a **new** GLM chat, set a fresh `CONTEXT_SESSION=` line (or remove it and run `./start.sh` again).

4. Pool sub-agents use `/tmp/xzglm slot register|take|publish|…` (see `/tmp/bridge_subagent_prompt.md`).

Do not build from source in this public repo.
