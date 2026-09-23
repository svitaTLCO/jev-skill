# Implementation Tracking: Codex Galene Swarm

## Status: IN_PROGRESS

**Last updated:** 2026-09-23  
**Current phase:** Team release candidate and real-work game pilot
**Blocking issues:** Game candidates failed mandatory Jev, including an uncapped retry; endpoint route confirmation, ledger retention choice, and internal distribution target remain open

This file is the cross-session handoff. It reports implementation facts and
identified gaps; it does not authorize or prioritize future features. Product
scope is owned by `SCOPE.md`.

## Task status

| ID | Capability | Status | Evidence |
|---|---|---|---|
| T-1 | Core task-contract validation | DONE | Required fields, IDs, output/token/verification bounds, unknown-field rejection |
| T-2 | OpenAI-compatible Galene/Qwen provider | DONE | Provider adapter, prompt test, dated live smoke in README |
| T-3 | Durable SQLite run/task evidence | DONE | Store used by orchestration tests and Docker volume configuration |
| T-4 | Configured asynchronous execution | DONE | Positive operator-selected worker count; no fixed task-batch ceiling |
| T-5 | Optional fail-closed Jev policy gate | DONE | Evaluator implementation and orchestration tests |
| T-6 | Four-tool MCP stdio boundary | DONE | MCP tool-discovery test |
| T-7 | Opt-in networkless Docker verification | DONE | Path, isolation, cleanup, and evidence tests using a fake Docker client |
| T-8 | Real Docker verifier boundary exercise | NOT_VERIFIED | No current real-daemon execution evidence in this documentation session |
| T-9 | Restart reconciliation/recovery | DONE | Startup marks interrupted active runs/tasks failed; no automatic retry |
| T-10 | Hard verifier execution timeout | NOT_STARTED | Docker SDK `exec_run` is currently unbounded by the configured timeout |
| T-11 | Long-running process lifecycle cleanup | DONE | Completed futures removed from process registry |
| T-12 | Image-only Linux/WSL team bundle | IN_PROGRESS | `0.2.0rc1` local image built; release Compose/config written; clean install and registry publication pending |
| T-13 | Mandatory Jev pilot policy | DONE | Team Compose forces `SWARM_REQUIRE_JEV=1`; startup checks the key |
| T-14 | Circuit Sprint 3D real-work pilot | IN_PROGRESS | Playable game, 5 Node and 2 Chromium tests pass; all six nonempty game candidates rejected by Jev |

## Dependencies

- T-8 requires explicit approval because it enables the Docker-socket-backed
  verified profile.
- T-10 belongs to the separately approved verified-profile track and is not a
  blocker for the default team server.

## Current file ownership

| Area | Files |
|---|---|
| Product/operator entry point | `README.md` |
| Product and engineering documentation | `docs/*.md` |
| Models and contracts | `src/codex_galene_swarm/models.py` |
| Orchestration and state | `src/codex_galene_swarm/orchestrator.py`, `store.py` |
| External model boundaries | `src/codex_galene_swarm/providers.py`, `jev.py` |
| Executable verification | `src/codex_galene_swarm/verifier.py` |
| MCP composition | `src/codex_galene_swarm/server.py` |
| Live boundary probe | `scripts/live_smoke.py` |
| Automated checks | `tests/` |
| Container runtime | `Dockerfile`, `docker-compose.yml` |

## Known issues and open engineering gaps

- [x] Reconcile `queued`/`running` rows left by an unexpected process restart.
- [x] Type-check and size-bound every prompt-bearing contract field.
- [ ] Enforce a real wall-clock timeout around verifier command execution and
  cover cleanup on timeout.
- [x] Remove completed runs from the in-memory future registry.
- [x] Prevent cancelled tasks from being overwritten by late gate/verifier work.
- [ ] Decide whether run-level outcomes need a distinct `partial` state; today a
  mixture containing any passed/rejected task resolves to `completed`.
- [ ] Add current real-daemon evidence for the verifier isolation boundary if
  that capability is promoted beyond proof-of-architecture status.
- [ ] Define retention/redaction policy before storing candidates from sensitive
  repositories in a long-lived ledger.
- [ ] Validate the image-only bundle on clean Linux and WSL environments and
  publish an approved image digest or archive.
- [ ] Confirm the live Galene route behind `Galene/LLM` is Qwen 3.8 27B.
- [ ] Resolve game-contract and Jev-gate mismatch before claiming an autonomous
  or gate-approved real-work swarm result.

These are observations, not an approved roadmap. A selected item needs explicit
requirements and acceptance criteria before code changes begin.

## Explicitly uncommitted product ideas

- Dashboard or human workflow UI
- Recursive agents or worker-to-worker delegation
- Responses API compatibility proxy
- Automatic patch application or merge
- Distributed/multi-replica execution

Do not infer priority or approval from this list. See the non-goals and scope
change rule in `SCOPE.md`.

## Dead ends and operational lessons

### DE-1: Treating a small completion budget as sufficient for Galene

**What was attempted:** A live smoke used a 120-token completion ceiling.  
**Root cause:** The provider consumed the budget as reasoning and returned no
candidate with `finish_reason=length`.  
**Verdict:** Preserve no-content provider metadata and size the budget to the
contract. The current smoke uses 1,200; this is a smoke-specific operating
choice, not a universal performance claim.

### DE-2: Writing the SQLite ledger through an incorrectly owned volume

**What was attempted:** Run the non-root service with a Docker-managed ledger
volume that was not writable by its user.  
**Root cause:** Volume mount ownership did not match UID 10001.  
**Verdict:** Keep `/data` created and owned by the image's `swarm` user and use
the declared Docker-managed volume.

## Test health

| Suite | Passing | Failing | Skipped | Boundary |
|---|---:|---:|---:|---|
| Dockerized unittest discovery | 26 | 0 | 0 | Models/orchestration/MCP/provider errors/verifier with fakes |
| Live Galene + Jev smoke | 1 | 0 | 0 | 2026-09-23 image-only smoke through MCP, ephemeral ledger; details in README |
| Real Docker verifier execution | 0 | 0 | 0 | Not run; requires explicit approval for socket access |
| Circuit Sprint 3D Node tests | 5 | 0 | 0 | Track, mesh, controls, bounded vehicle motion, AI three-lap completion |
| Circuit Sprint 3D Chromium tests | 2 | 0 | 0 | Render, solo drive/pause, two-player HUD in Docker software WebGL |

Latest local command on 2026-09-23:

```bash
rtk docker compose -f codex-galene-swarm/docker-compose.yml run --rm test
```

Result: 26 tests passed in 2.902 seconds. This validates the fake-boundary suite,
not current external service availability or real Docker isolation.

The `0.2.0rc1` image built locally. Image-only startup with a temporary
in-memory `/data` mount rejected a missing mandatory Jev key as expected and
started cleanly with dummy keys.
The same image then completed one live Galene + mandatory Jev MCP smoke using
the in-memory ledger. This proves a point-in-time endpoint path, not the actual
backend model route, persistent team-volume recovery, or real-task quality.

## Session log

### 2026-09-23 — Removed research-stage generation ceilings

- `max_tokens` is now optional and omitted from Galene requests by default;
  explicit positive values are forwarded without a product-imposed maximum.
- `GALENE_TIMEOUT_SECONDS=0` can disable the local provider-call deadline for a
  supervised experiment; the ordinary default remains 180 seconds.
- Removed fixed 12-task and 8-worker upper bounds. Worker count remains an
  operator setting, default 4; the service adds no rate-limit sleeps or retry
  throttling. Galene's own capacity and limits still apply.
- Retained prompt-field validation, response-size protection, and verifier
  resource limits because they protect the service rather than constrain model
  research. Added tests for an uncapped request, a 16,000-token request, and a
  13-task batch with nine configured workers.
- Built `codex-galene-swarm:research` and sent one uncapped live provider probe
  through the installed image. Galene returned content with `finish_reason=stop`,
  2 completion tokens, 0 reasoning tokens, and 426 ms observed latency. This
  verifies request acceptance, not large-output behavior or endpoint capacity.
- Reran the game track-module contract without `max_tokens` through MCP and
  mandatory Jev. Run `ab6ccd40cdb64be786d1b8efb0ec3cb1` returned a full
  3,564-token candidate (`finish_reason=stop`), then Jev rejected it for
  specification compliance 0.62. The output limit is no longer the observed
  blocker for this task; contract fidelity and gate outcome remain unresolved.

### 2026-09-23 — Circuit Sprint 3D real-work pilot

- Corrected the provider request for the Galene route: low reasoning effort,
  top-level `enable_thinking: false`, and the existing chat-template flag.
  A focused provider test was added; the Dockerized swarm suite passed 23/23.
- Ran two persistent-volume game-contract batches through MCP with mandatory
  Jev. Five nonempty candidates were rejected; one task returned no content.
  Earlier 4,000-token contracts exhausted their budget in reasoning. See
  `pilot/circuit-sprint-3d/PILOT_EVIDENCE.md` for run IDs and limits.
- Integrated three manually reviewed candidate modules with Codex-authored
  game code. The playable 3D game passed five Dockerized Node tests, a
  production build, and two Dockerized Chromium browser tests. Jev rejection
  remains a release blocker for claiming gate-approved swarm development.

### 2026-09-23 — Team pilot candidate work

- Recorded Linux/WSL, mandatory Jev, and the local `Galene/LLM` model alias in
  the pilot plan. Live route ownership remains to be confirmed.
- Added full prompt-field bounds, restart reconciliation, guarded cancellation,
  future cleanup, and safer provider error/truncation handling.
- Added an image-only release bundle and pinned the base/runtime dependencies.
- Ran the Dockerized suite: 22 passed, 0 failed, 0 skipped; built the local
  `0.2.0rc1` image; completed one credentialed live Galene + Jev smoke without
  exposing candidate text. No persistent team volume test was run.

### 2026-09-23 — Consolidated development documentation

- Reconciled the current scope against source, tests, Compose, and the live-smoke
  script.
- Added canonical product scope, architecture, development/operations, and this
  living implementation record.
- Documented exact state/cancellation/restart semantics and verifier privilege.
- Ran the Dockerized suite: 14 passed, 0 failed, 0 skipped.
- Did not change runtime behavior or enable the privileged verified profile.
