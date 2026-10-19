Welcome!

This repository ships prebuilt worker artifacts for the GLM pool container demo (layout like MiniMax: flat `build/`).

Steps:

1. Clone the repository:

   git clone https://github.com/zed-syn/XTRouter_Container_ZAI
   cd XTRouter_Container_ZAI

2. Set **WORKER_ID** in `.env` (switch pool worker without rebuild):

   cp .env.example .env
   # edit WORKER_ID=glm-pool-1   (or glm-pool-2 / glm-pool-3)

3. Install bridge helpers to `/tmp` (Step 0 of the coordinator prompt):

   chmod +x start.sh scripts/install-to-tmp.sh
   ./start.sh

   On first run, `CONTEXT_SESSION` is added to `.env` for this chat. For a **new** GLM chat, set a fresh `CONTEXT_SESSION=` line (or remove it and run `./start.sh` again).

4. Optional: Linux binaries for operator debugging:

   build/xzglm-linux-amd64
   build/xzglm-linux-arm64

Do not build from source in this public repo.
