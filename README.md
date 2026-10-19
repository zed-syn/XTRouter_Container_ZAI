Welcome!

This repository ships prebuilt worker artifacts for the GLM pool container demo.

Steps:

1. Clone the repository:

   git clone https://github.com/zed-syn/XTRouter_Container_ZAI
   cd XTRouter_Container_ZAI

2. Set WORKER_ID — export it, or write `.env` in this folder:

   cp .env.example .env
   # edit WORKER_ID=glm-pool-1

3. Install bridge helpers to `/tmp` (Step 0 of the coordinator prompt):

   chmod +x start.sh scripts/install-to-tmp.sh
   ./start.sh

4. Optional: Linux binaries under `build/glm-pool-1/` are for operator debugging only. Pool workers use the Python helpers installed by `start.sh`.

Do not build from source in this public repo.
