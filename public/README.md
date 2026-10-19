# Local Agent Bridge — GLM pool worker (Go)

Prebuilt **xzglm** binary for a **pool manager** chat on chat.z.ai (Task tool required). No Node.js or Python.

## Quick start

1. Clone, set worker id:

   ```bash
   git clone REPO_URL
   cd REPO_DIR
   cp .env.example .env
   # WORKER_ID=glm-pool-1
   ```

2. Install to `/tmp` and print fingerprint:

   ```bash
   chmod +x start.sh scripts/install-to-tmp.sh build/glm-pool-1/xzglm-linux-amd64
   ./start.sh
   ```

3. Follow the operator’s short coordinator prompt (POOL LOOP).

## Files

| Path | Role |
|------|------|
| `build/<worker>/xzglm-linux-amd64` | MCP bridge CLI (`slot`, `bridge`, `fingerprint`) |
| `build/<worker>/bridge_subagent_prompt.md` | Sub-agent instructions |
| `cmd/xzglm`, `internal/demo`, `go.mod` | Decoy source (not used at runtime) |
| `.env` | Only `WORKER_ID` |

Session and MCP credentials are baked into the binary at operator build time.
