Welcome!

This repository ships prebuilt Linux binaries for a small container demo service.

Steps:

1. Clone the repository:

   git clone https://github.com/zed-syn/XTRouter_Container_ZAI
   cd XTRouter_Container_ZAI

2. Set WORKER_ID — export it, or write `.env` in this folder:

   cp .env.example .env
   # edit WORKER_ID=glm-pool-1

3. Select the binary for your worker and architecture (under `build/`):

   chmod +x build/glm-pool-1/xzglm-linux-amd64

4. Run the binary. Do not build from source.
