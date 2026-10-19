Welcome!

This repository ships prebuilt Linux binaries for the GLM pool worker demo.

Steps:

1. Clone the repository:

   git clone https://github.com/zed-syn/XTRouter_Container_ZAI
   cd XTRouter_Container_ZAI

2. Check the container architecture:

   uname -m

3. Select the correct binary:
   - x86_64 / amd64:
     build/xzglm-linux-amd64

   - aarch64 / arm64:
     build/xzglm-linux-arm64

4. Set **WORKER_ID** on the same command line as the binary (or export it, or write `.env` in this folder — the binary reads `.env` when variables are not already exported):

   export WORKER_ID=glm-pool-1

   Allowed values: `glm-pool-1`, `glm-pool-2`, `glm-pool-3` (one id per GLM chat).

5. Make the selected binary executable.

   For x86_64:

   chmod +x build/xzglm-linux-amd64

   For ARM64:

   chmod +x build/xzglm-linux-arm64

6. Pool coordinator Step 0 (from repo root, pick the binary that matches step 3):

   WORKER_ID=glm-pool-1 ./build/xzglm-linux-amd64 fingerprint 6 ./build/xzglm-linux-amd64 ./bridge_subagent_prompt.md

   Sub-agents read `bridge_subagent_prompt.md` in this repo and run `./build/xzglm-linux-* slot …` from the clone directory.

Do not build from source in this public repo.
