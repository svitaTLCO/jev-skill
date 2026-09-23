# Agent workspace guide

This checkout contains two related but independently owned projects. Identify the requested project before editing; do not treat the whole checkout as one application.

## Shared operating rules

- Preserve existing user changes and unrelated dirty files. Inspect `git status` before editing and review the diff afterward.
- Run project code, tests, builds, package installs, UI/stress tests, database commands, and environment setup in Docker. Do not run project Python, Node.js, package managers, runtimes, or installers directly on the host.
- Prefix shell commands with `rtk` when available; prefix every segment in a command chain. Use raw commands only when RTK has no applicable wrapper or for debugging.
- Before destructive or environment-changing operations involving volumes, databases, staging, production, migrations, or stress tests, explain the impact and obtain explicit confirmation.
- Keep credentials in ignored local environment files or container environment; never print, commit, or persist secrets.
- Do not invent an implementation plan from roadmap ideas. The Codex Galene Swarm README is its current project overview; it does not define approval or ordering for future features.

## Project routing and ownership

### Codex Galene Swarm — active scope when the task says Codex/Qwen swarm

- Project root: [`codex-galene-swarm/`](codex-galene-swarm/)
- Start with [`codex-galene-swarm/README.md`](codex-galene-swarm/README.md), then inspect the relevant source and tests before changing behavior.
- This is an MCP service where Codex remains the orchestrator and delegates bounded contracts to Qwen through Galene. Workers return candidate text; they do not get shell access or edit the caller's worktree. Codex reviews/applies candidates and owns repository-level validation.
- The current slice includes the Galene-compatible provider, SQLite run ledger, bounded background concurrency, optional Jev gates, an MCP stdio server, and opt-in executable verification. Treat README as the source for current boundaries and operational details; verify claims against code/tests before extending them.
- Default test command from this checkout root: `rtk docker compose -f codex-galene-swarm/docker-compose.yml run --rm test`.
- The `verified` Compose profile mounts the workspace read-only and the Docker socket. Docker-socket access grants control of the local Docker daemon; do not enable or run this profile without the operator's explicit approval for that task.
- Keep changes inside `codex-galene-swarm/` unless the user explicitly requests shared/root-level changes. Do not modify Jev project implementation on behalf of this project.
- There is currently no separate implementation-plan/task-list document in this project. README items described as not-yet-included (dashboard, recursive agents, Responses API proxy) are not automatically authorized tasks.

### TypeSafe AI / Jev Skills — separate project, owned by another agent

- Project root: this checkout's root (`scripts/`, `tests/`, `references/`, `demo/`, `benchmarks/`).
- Its scope is the Jev evaluation and local-SLM tooling documented in the Jev README, source, and `references/`.
- Do not take over, resume, or alter Jev implementation work when the request is for Codex Galene Swarm. If a task explicitly targets Jev, work only within its requested scope and coordinate ownership with the Jev agent when changes overlap.
- Treat model performance, latency, hardware, and benchmark statements as claims requiring current evidence; do not repeat old results as live verification.

## Coordination between agents

- Make task ownership explicit by project path. Parallel work is safe only when edits are disjoint or ownership has been agreed.
- Before editing, check for existing changes in the target files. Do not discard, reset, or silently absorb another agent's work.
- Keep shared guidance at this file concise and stable; put implementation-specific details and operational changes in the owning project's README/tests/source.
- Update this file when project boundaries, safety rules, or canonical entry points change—not for routine implementation details.
