# Private operator content

- `templates/bridge_subagent_prompt.md` — sub-agent FAST LOOP (Go `xzglm slot` commands); baked into each release under `build/<worker>/bridge_subagent_prompt.md`.
- Never publish `secrets/`, `operator.env`, or `internal/config/embedded_release.secret`.

Legacy Python pool template removed; canonical bake is `go run ./cmd/bake` + `build.sh`.
