Welcome!

This repository ships prebuilt Linux binaries for a small container demo.

Steps:

1. Clone the repository:

   git clone https://github.com/zed-syn/demo-test-hieu-nang zed-glm-worker
   cd zed-glm-worker

2. Check the container architecture:

   uname -m

3. Select the correct binary:
   - x86_64 / amd64:
     build/xzglm-linux-amd64

   - aarch64 / arm64:
     build/xzglm-linux-arm64

4. Set WORKER_ID — export it, or write `.env` in this folder (the binary reads `.env` by itself):

   export WORKER_ID=glm-pool-1

5. Make the selected binary executable.

   For x86_64:

   chmod +x build/xzglm-linux-amd64

   For ARM64:

   chmod +x build/xzglm-linux-arm64

6. From the repository root, run the binary you selected in step 3.
