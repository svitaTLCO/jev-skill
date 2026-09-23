# Development and Operations

**Last reviewed:** 2026-09-23

## Start here

Read, in order:

1. `docs/SCOPE.md` for the product boundary and invariants.
2. `docs/ARCHITECTURE.md` for runtime behavior and trust boundaries.
3. `docs/IMPLEMENTATION_STATUS.md` for the current handoff and known gaps.
4. The source and tests for the component being changed.

All project code, tests, builds, package installation, and live checks run in
Docker. Host use is limited to file inspection/editing, Git, and Docker
orchestration.

## Local validation

From the checkout root:

```bash
rtk docker compose -f codex-galene-swarm/docker-compose.yml run --rm test
```

From this project directory:

```bash
rtk docker compose run --rm test
```

The default tests use fake provider/evaluator/verifier boundaries and require no
credentials or Docker socket mount. A green suite proves the tested application
logic; it does not prove live Galene/Jev availability or real verifier isolation.

## Change workflow

1. Inspect Git status and preserve existing unrelated changes.
2. Identify the affected invariant, contract, state transition, or boundary.
3. Add a regression test for the intended success and important failure paths.
4. Make the narrowest implementation change.
5. Run the complete Dockerized test suite.
6. If an external boundary changed, run the corresponding opt-in validation and
   record exactly what it proves.
7. Update operator-facing documentation and `IMPLEMENTATION_STATUS.md`.
8. Review the final diff for leaked credentials, scope drift, and stale claims.

Tests should prefer injected fakes over network calls. Runtime claims must still
be checked at the real boundary before being presented as live evidence.

## Run the default MCP server

Create ignored `codex-galene-swarm/.env` content:

```dotenv
GALENE_API_KEY=...
GALENE_BASE_URL=https://api-tlco.elettra.ai/v1
GALENE_MODEL=Galene/LLM
TYPESAFE_API_KEY=... # optional; required by require_jev=true
```

Build and run without a TTY for an MCP stdio client:

```bash
rtk docker compose -f codex-galene-swarm/docker-compose.yml build server
rtk docker compose -f codex-galene-swarm/docker-compose.yml run --rm -T server
```

The server keeps its SQLite ledger in the `swarm-data` Docker volume. Do not
remove or recreate that volume as a routine troubleshooting step.

## Live Galene/Jev smoke

With valid ignored credentials configured:

```bash
rtk docker compose -f codex-galene-swarm/docker-compose.yml run --rm --entrypoint python server scripts/live_smoke.py
```

The script exercises all calls through the MCP boundary, does not print the
candidate, and fails unless the task passes. It makes billable/external requests
and its result is point-in-time evidence only. Record the date, run ID, terminal
states, provider finish reason/token metadata, latency, and Jev policy evidence;
never record credentials or candidate source merely to prove the path ran.

## Verified profile

Do not enable this profile casually. It mounts the caller repository read-only
and the Docker socket; socket access is effectively host-level Docker control.
Starting it requires explicit operator approval for that task.

After approval, determine the socket group and start it with:

```bash
DOCKER_GID=$(stat -c %g /var/run/docker.sock) \
  rtk docker compose -f codex-galene-swarm/docker-compose.yml \
  --profile verified run --rm -T server-verified
```

`SWARM_VERIFIER_IMAGE` must name a pre-existing operator-controlled image with
POSIX `sh`, `cp`, `test`, `sleep`, and the runtime used by the task's argument
vector. The service does not pull a worker-selected image.

## Contract authoring checklist

- Split only independent work; there is no task dependency scheduler.
- Make one objective observable and small enough for the token ceiling.
- Supply exact interfaces and only the context the worker needs.
- Keep `allowed_files` narrow; an empty list means no file writes are permitted
  in the prompt and makes executable verification unavailable.
- Write checks that distinguish a plausible-looking answer from a correct one.
- Use `analysis` for advisory text, `code` for a code fragment, and
  `unified_diff` for a candidate patch.
- Require Jev when semantic gating is part of acceptance, not merely because the
  key happens to be configured.
- Supply a verification command only when its runtime exists in the verifier
  image and it can operate without network access.
- Inspect every task state and evidence; never equate run `completed` with all
  tasks passing.

## Documentation maintenance

- `SCOPE.md` changes only when the product boundary, actors, or invariants change.
- `ARCHITECTURE.md` changes with components, state semantics, data flow, security
  boundaries, configuration, or material limitations.
- `IMPLEMENTATION_STATUS.md` is updated in every development session that changes
  capability, test health, known issues, or failed approaches.
- Keep historical live evidence dated. Replace claims of current health with a
  new run instead of treating old evidence as permanent.
- When the implementation-status file approaches 500 lines, archive older
  completed/session material under `docs/archive/` before compacting it.

## Troubleshooting

| Symptom | First checks |
|---|---|
| Server fails during startup | `GALENE_API_KEY`, `GALENE_BASE_URL`, database path ownership |
| Required Jev run is rejected before dispatch | `TYPESAFE_API_KEY` is present in the server container |
| Provider returns no content | Inspect stored finish reason and reasoning-token metadata; increase a deliberately undersized task ceiling only when justified |
| Verification request is refused | Use the verified profile and provide both `allowed_files` and a `unified_diff` output kind |
| Docker verifier cannot start | Socket mount/group, pre-existing image, daemon availability, and required utilities |
| Run remains queued/running after restart | Current service has no job recovery; preserve the ledger for diagnosis and start a new run deliberately |
| Run says completed but work is missing | Inspect each task; rejected/failed tasks can coexist with a completed run |

