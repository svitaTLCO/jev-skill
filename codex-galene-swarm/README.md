# Codex Galene Swarm

An isolated proof of the architecture in which Codex remains the orchestrator
and delegates bounded, read-only contracts to Qwen 3.8 through Galene. The
service exposes four MCP tools over stdio:

- `swarm_start`: persist and asynchronously dispatch a batch of contracts.
- `swarm_status`: inspect run and task state.
- `swarm_result`: retrieve completed candidates and gate evidence.
- `swarm_cancel`: prevent queued work from being promoted.

Workers return candidate text; they do not receive shell access and they do not
edit the caller's worktree. Codex remains responsible for reviewing and applying
any returned patch and for running repository-level tests.

## Documentation map

- [`docs/SCOPE.md`](docs/SCOPE.md) is the canonical product boundary: purpose,
  actors, supported use cases, invariants, and explicit non-goals.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) describes components, data flow,
  state semantics, trust boundaries, and known architectural limitations.
- [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) is the contributor and operator
  workflow, including Docker-only validation and live-smoke guidance.
- [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md) is the living
  handoff record: implemented capabilities, test health, gaps, and session log.
- [`docs/TEAM_PILOT_PLAN.md`](docs/TEAM_PILOT_PLAN.md) proposes the gates for a
  first internal distribution and real-work pilot.
- [`release/README.md`](release/README.md) describes the image-only Linux/WSL
  team bundle and Codex MCP connection.
- [`pilot/circuit-sprint-3d/README.md`](pilot/circuit-sprint-3d/README.md) is
  the playable 3D racing pilot; its evidence file records the Jev rejections
  and executable checks.

Read `docs/SCOPE.md` before changing behavior and update
`docs/IMPLEMENTATION_STATUS.md` in the same change when capability or validation
state changes. Items described as possible future work are not an approved
roadmap.

## Current vertical slice

The first slice intentionally includes only:

- an OpenAI-compatible Galene provider;
- a durable SQLite run ledger;
- bounded background concurrency;
- optional TypeSafe Jev semantic gates;
- opt-in executable verification in an ephemeral, network-disabled Docker container;
- a stdio MCP server;
- fake-provider tests that require no external credentials.

It does not yet include a dashboard, recursive agents, or a Responses API proxy.
Generated code is executed only when a task supplies a
structured `verification_command` and the operator starts the explicit
`verified` profile. A model score never substitutes for that executable check.

### Live smoke evidence (2026-09-22)

The MCP boundary was exercised with one real Galene task and mandatory Jev
gating after the Docker volume fix. Run `d4b1fbfe1f8b475c958f784ab29da502`
completed and the task passed. Galene returned a provider request ID,
`finish_reason=stop`, 321 completion tokens, 292 reasoning tokens, and 8.12
seconds latency. Jev accepted the candidate in 0.82 seconds with reference
integrity 0.86, specification compliance 0.78, scope control 0.89, and quality
2.73/3. Candidate text and credentials were not printed.

A preceding 120-token attempt failed with `finish_reason=length` after all 120
tokens were reported as reasoning. This is why the smoke contract uses the
established 1,200-token ceiling and why no-content metadata is persisted.

On 2026-09-23 the `0.2.0rc1` image completed a second live Galene + mandatory
Jev smoke through the MCP boundary using a temporary in-memory ledger. Run
`f57316afdabb402faa554721ee2f3eb8` completed with one passed task. Galene
returned a request ID, `finish_reason=stop`, 278 completion tokens, 249
reasoning tokens, and 4.49 seconds latency. Jev passed policy v1 in 0.53
seconds. The temporary ledger was removed with the container, so this run ID is
a point-in-time report identifier rather than a retrievable persistent record.
The smoke did not verify the backend model behind the `Galene/LLM` alias or
candidate quality on a real repository task.

## Run tests

All project execution happens in Docker:

```bash
docker compose run --rm test
```

The candidate team build is version `0.2.0rc1`. Its Dockerfile pins the base
image digest and uses `requirements.lock` for Python runtime dependencies.
The team bundle forces Jev gating with `SWARM_REQUIRE_JEV=1`; an unset Jev key
fails at startup. The `Galene/LLM` alias appears as `Qwen3.8-27B-NVFP4` in the
local OpenCode configuration, but the GaleneAI endpoint owner still needs to
confirm the live deployment behind that alias.

## Run the MCP server

Create a local `.env` (it is ignored) with:

```dotenv
GALENE_API_KEY=...
GALENE_BASE_URL=https://api-tlco.elettra.ai/v1
GALENE_MODEL=Galene/LLM
TYPESAFE_API_KEY=... # optional unless a call requires Jev
```

Then build the image:

```bash
docker compose build server
```

Run a credentialed end-to-end smoke test through the MCP tool boundary without
printing the generated candidate:

```bash
docker compose run --rm --entrypoint python server scripts/live_smoke.py
```

For a local Codex stdio connection, invoke the container without allocating a
TTY. Compose attaches the Docker-managed ledger volume declared above:

```toml
[mcp_servers.galene_swarm]
command = "docker"
args = [
  "compose", "-f", "/absolute/path/to/codex-galene-swarm/docker-compose.yml",
  "run", "--rm", "-T", "server"
]
```

Provider credentials remain environment variables inside the server container.
They are never included in tool results or persisted in the ledger.
The SQLite ledger is stored in the Docker-managed `swarm-data` volume, whose
mount point is owned by the image's non-root `swarm` user.

## Opt-in executable verification

The default `server` has no access to Docker or the caller's repository. To
enable executable checks, start `server-verified`. This profile mounts the
repository read-only at `/workspace` and mounts the Docker socket, which is
equivalent to granting the service control of the local Docker daemon. Determine
the socket group ID on the host and pass it explicitly:

```bash
DOCKER_GID=$(stat -c %g /var/run/docker.sock) docker compose --profile verified run --rm -T server-verified
```

`SWARM_VERIFIER_IMAGE` selects an operator-controlled, pre-existing test image;
it defaults to the profile's own `codex-galene-swarm:local` image. The worker
cannot choose or pull it. The verifier copies the repository, checks
that the candidate unified diff touches only `allowed_files`, applies it without
executing repository code, and uploads the result to an ephemeral container.
The verification command runs as UID 65534 with no network, no Linux
capabilities, `no-new-privileges`, a read-only root filesystem, bounded CPU,
memory and PIDs, and writable in-memory `/workspace` and `/tmp` mounts. The
container is removed after the result is captured. A non-executing staging
container and ephemeral snapshot image are used to populate the read-only
runtime and are also removed. The configured image must provide POSIX `sh`,
`cp`, `test`, `sleep`, plus the runtime required by the verification command.

## Contract example

```json
{
  "goal": "Add rate limiting",
  "tasks": [
    {
      "task_id": "rate-limit-core",
      "role": "implementer",
      "objective": "Return a unified diff implementing the limiter.",
      "interfaces": ["RateLimiter.allow(key: str) -> bool"],
      "allowed_files": ["src/rate_limit.py"],
      "acceptance_checks": ["does not modify unrelated files"],
      "output_kind": "unified_diff",
      "verification_command": ["python", "-m", "unittest", "tests.test_rate_limit"]
    }
  ],
  "require_jev": true
}
```

Jev receives the trusted contract and the candidate clearly delimited as
untrusted data. It returns reference-integrity, specification-compliance, and
scope-control probabilities plus a quality score. The policy is auditable and
versioned; it does not replace executable tests.
