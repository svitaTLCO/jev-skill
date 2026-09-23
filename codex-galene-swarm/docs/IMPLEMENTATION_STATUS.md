# Implementation Tracking: Codex Galene Swarm

## Status: IN_PROGRESS

**Last updated:** 2026-09-23  
**Current phase:** Iterate  
**Blocking issues:** None for the current proof-of-architecture slice

This file is the cross-session handoff. It reports implementation facts and
identified gaps; it does not authorize or prioritize future features. Product
scope is owned by `SCOPE.md`.

## Task status

| ID | Capability | Status | Evidence |
|---|---|---|---|
| T-1 | Core task-contract validation | DONE | Required fields, IDs, output/token/verification bounds, unknown-field rejection |
| T-2 | OpenAI-compatible Galene/Qwen provider | DONE | Provider adapter, prompt test, dated live smoke in README |
| T-3 | Durable SQLite run/task evidence | DONE | Store used by orchestration tests and Docker volume configuration |
| T-4 | Bounded asynchronous execution | DONE | Thread pool, 1-8 concurrency validation, maximum 12 tasks per run |
| T-5 | Optional fail-closed Jev policy gate | DONE | Evaluator implementation and orchestration tests |
| T-6 | Four-tool MCP stdio boundary | DONE | MCP tool-discovery test |
| T-7 | Opt-in networkless Docker verification | DONE | Path, isolation, cleanup, and evidence tests using a fake Docker client |
| T-8 | Real Docker verifier boundary exercise | NOT_VERIFIED | No current real-daemon execution evidence in this documentation session |
| T-9 | Restart reconciliation/recovery | NOT_STARTED | Durable ledger exists, durable queue/recovery does not |
| T-10 | Hard verifier execution timeout | NOT_STARTED | Docker SDK `exec_run` is currently unbounded by the configured timeout |
| T-11 | Long-running process lifecycle cleanup | NOT_STARTED | Completed future entries are not pruned |

## Dependencies

- T-8 requires explicit approval because it enables the Docker-socket-backed
  verified profile.
- T-9, T-10, and T-11 require explicit selection and acceptance criteria before
  implementation; their order is not established here.

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

- [ ] Reconcile or explicitly expire `queued`/`running` rows left by an
  unexpected process restart.
- [ ] Type-check and size-bound every prompt-bearing contract field (`goal`,
  strings, and list elements); current validation is complete only for the core
  scalar and verification constraints.
- [ ] Enforce a real wall-clock timeout around verifier command execution and
  cover cleanup on timeout.
- [ ] Remove completed runs from the in-memory future registry.
- [ ] Decide whether cancellation must be checked after Jev and verifier work or
  whether current cooperative semantics remain the contract.
- [ ] Decide whether run-level outcomes need a distinct `partial` state; today a
  mixture containing any passed/rejected task resolves to `completed`.
- [ ] Add current real-daemon evidence for the verifier isolation boundary if
  that capability is promoted beyond proof-of-architecture status.
- [ ] Define retention/redaction policy before storing candidates from sensitive
  repositories in a long-lived ledger.

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
| Dockerized unittest discovery | 14 | 0 | 0 | Models/orchestration/MCP/provider prompt/verifier with fakes |
| Live Galene + Jev smoke | historical only | n/a | n/a | Last evidence is dated 2026-09-22 in README |
| Real Docker verifier execution | 0 | 0 | 0 | Not run; requires explicit approval for socket access |

Latest local command on 2026-09-23:

```bash
rtk docker compose -f codex-galene-swarm/docker-compose.yml run --rm test
```

Result: 14 tests passed in 1.629 seconds. This validates the fake-boundary suite,
not current external service availability or real Docker isolation.

## Session log

### 2026-09-23 — Consolidated development documentation

- Reconciled the current scope against source, tests, Compose, and the live-smoke
  script.
- Added canonical product scope, architecture, development/operations, and this
  living implementation record.
- Documented exact state/cancellation/restart semantics and verifier privilege.
- Ran the Dockerized suite: 14 passed, 0 failed, 0 skipped.
- Did not change runtime behavior or enable the privileged verified profile.
