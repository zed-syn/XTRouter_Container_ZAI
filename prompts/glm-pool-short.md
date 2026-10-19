# Short GLM pool prompt (template)

Run `bash ./build.sh` to generate `prompts/glm-pool-short-<worker>.md` with repo URL and worker id.

Paste the generated file into a **new** chat on chat.z.ai (pool manager; needs Task tool).

Manual placeholders if you edit by hand:

- `{{WORKER_ID}}` — e.g. `glm-pool-1` (also the only `.env` variable end users set)
- `{{REPO_URL}}` — public GitHub clone URL
- `{{REPO_DIR}}` — clone directory name
- `{{POOL_SLOTS}}` — default `6`
- `{{POOL_MAX}}` — default `10`

Coordinator flow summary:

1. **Step 0:** clone repo → write `.env` with `WORKER_ID` → `./start.sh` (loads `build/<worker>/scripts/` → fingerprint + ignore nonces).
2. **POOL LOOP:** one execution prints `files …` + 6 nonces → launch 6 Task sub-agents → repeat.

Session id is baked at operator build time (new bake per new chat); not in end-user `.env`.
