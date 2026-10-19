# XTRouter Container — ZAI / GLM pool (Go-only)

Mimimax-style split: **this private repo** holds bake tooling and secrets; the **public GitHub repo** gets a release tree (decoy Go + baked `xzglm` binary under `build/<worker>/` + `start.sh` + `.env.example`). End users set **`WORKER_ID`** only.

## Mimimax vs ZAI

| Product | End-user `.env` | Baked at release | Public decoy |
|---------|-----------------|------------------|--------------|
| **Mimimax** | `XTR_CHAT_ID` | Join secret in Go binary | `cmd/xkmmx`, `internal/demo` |
| **ZAI pool** | `WORKER_ID` | `MCP_URL`, `TOKEN`, `WORKER_ID`, `CONTEXT_SESSION` in `xzglm` | `cmd/xzglm`, `internal/demo` |

Each **new GLM chat** needs a fresh bake (new `CONTEXT_SESSION`). Re-run `build.sh` before opening that chat.

## Layout

| Path | Private | Published release |
|------|---------|-------------------|
| `public/` | Stub | Release root |
| `build/release/<worker>/` | Gitignored | Push to public GitHub |
| `build/release/<worker>/build/<worker>/xzglm-linux-amd64` | Baked binary + prompt | Same |
| `cmd/gateway` | Real bridge CLI (built as `xzglm`) | Never (binary only) |
| `cmd/xzglm` | Decoy | Copied |
| `cmd/bake`, `cmd/renderprompt`, `tools/genlit` | Operator | Never |
| `private/templates/` | Sub-agent prompt | Never |
| `secrets/*.token`, `operator.env` | Local | Never |

## Operator build

1. Copy `operator.env.example` → `operator.env` and set `MCP_URL` or `BRIDGE_PUBLIC_BASE_URL` + `BRIDGE_PUBLIC_PATH_PREFIX`.
2. Token: `secrets/glm-pool-1.token` (or `LAB_POOL_TOKEN_FILE`).
3. Git Bash:

   ```bash
   export LAB_POOL_WORKER=glm-pool-1
   export LAB_POOL_REPO_URL=https://github.com/YOUR_ORG/YOUR_PUBLIC_REPO
   bash ./build.sh
   ```

4. Outputs:
   - `build/xzglm-linux-amd64`, `build/xzglm-linux-arm64`, `build/xzglm-windows-amd64.exe`
   - `build/release/glm-pool-1/` — publish to public repo
   - `prompts/glm-pool-short-glm-pool-1.md` — paste into new chat.z.ai pool-manager chat

Manual steps (without full `build.sh`):

```bash
go run ./cmd/bake --worker glm-pool-1 --token-file secrets/glm-pool-1.token
go run ./tools/genlit   # after embedded_release.secret exists
go build -tags release -o build/xzglm-linux-amd64 ./cmd/gateway
go run ./cmd/renderprompt --worker glm-pool-1 --repo-url https://github.com/ORG/REPO
```

## GLM end user

1. Clone public repo, `cp .env.example .env`, set `WORKER_ID=glm-pool-1`.
2. `./start.sh` — installs `/tmp/xzglm` + prompt, prints `files …` and nonces.
3. Follow the short coordinator prompt (Task tool pool loop).

## Bridge CLI (Go)

Sub-agents (after `start.sh`):

```bash
SLOT_ID=glm-pool-1-p1 SLOT_NONCE=... SLOT_MAX=10 /tmp/xzglm slot take
SLOT_ID=... /tmp/xzglm slot publish TASK_ID /tmp/answer.md
```

Optional coordinator debug:

```bash
/tmp/xzglm bridge take
/tmp/xzglm bridge publish TASK_ID /tmp/answer.md
```

Canonical source: **this repo**. `local-agent-bridge/container-glm-pool/` points here for integration docs only.
