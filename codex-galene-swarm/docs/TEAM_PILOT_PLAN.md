# Team pilot plan

**Status:** In progress; pilot choices recorded 2026-09-23
**Product:** Codex Galene Swarm, local Docker image connected to Codex over MCP stdio
**Worker endpoint:** Internal GaleneAI serving the team's Qwen 3.8 27B deployment

The first supported environments are Linux and WSL. Jev is mandatory for every
pilot task. The local OpenCode configuration names the model route `Galene/LLM`
and labels it `Qwen3.8-27B-NVFP4`; the endpoint owner must still confirm the
live backend serving that alias.

## Release target

Ship a versioned image that a developer can install from an internal registry and
connect to Codex without checking out this repository. Codex delegates bounded,
independent contracts and remains responsible for inspecting candidates, applying
changes, and validating the repository. The first team release uses the default
server profile. Docker-socket-backed executable verification remains a separate,
explicitly approved experiment.

The pilot should establish whether this workflow helps real development work,
how often it produces usable candidates, and what it costs in latency and model
usage. One successful smoke task is connection evidence, not product validation.

## Gate 0: Freeze the pilot contract

**Decide and record before implementation:**

- Supported Codex client versions on Linux and WSL.
- The exact GaleneAI base URL, authenticated access method, and model identifier
  that routes to Qwen 3.8 27B. Verify the route at the live boundary; do not
  infer the deployment from the model name in a request.
- Approved source/data classification for contract context, who may use the
  endpoint, and the ledger retention period. Contracts and candidate text are
  sent to Galene and candidates are stored locally in SQLite.
- How Jev keys are provisioned. The pilot requires Jev on every run; missing
  configuration must fail closed.
- Which task types qualify for the pilot. Include both focused modules and
  larger game-development contracts with explicit interfaces and acceptance
  checks. Record task size as an experimental variable. Exclude secrets and
  tasks requiring a worker to browse or inspect the repository itself.

**Exit:** A one-page pilot policy, named owner for the endpoint and image, and
three representative contracts with expected acceptance checks.

## Gate 1: Make the default server safe to leave running

1. Complete type and size limits for every prompt-bearing contract field and
   reject oversized MCP requests before persistence or provider dispatch.
2. Define restart semantics. On startup, reconcile abandoned queued/running
   tasks to a terminal interrupted state or implement real recovery; do not
   leave them indefinitely running. Test a process kill and restart against the
   same ledger.
3. Prune completed futures from the in-memory registry. Specify cancellation
   behavior after provider, Jev, and verifier stages, and make persisted task
   and run states consistent with that contract.
4. Define a local ledger retention and deletion procedure, including how to
   remove candidate bodies and verifier output. Keep credentials out of both
   ledger and logs. Decide whether `completed` is sufficient for partial runs
   or whether the client needs an explicit partial state.
5. Give provider calls bounded failure behavior: classify HTTP errors,
   timeouts, malformed responses, and empty completions; retain safe request
   metadata; avoid retrying requests with an unknown outcome automatically.

**Exit:** Dockerized tests cover these failure paths, a restart exercise leaves
no misleading live states, and a long-running process does not grow its future
registry with completed runs.

## Gate 2: Package and install the team build

1. Build and publish a versioned image to the internal registry. Pin base image
   and Python dependencies, record the image digest, and run dependency/image
   checks in CI. Release from a tagged commit with a small changelog.
2. Provide a minimal per-developer launcher and Codex MCP configuration that
   pull and run the image, attach a persistent **local** ledger volume, pass
   credentials through the approved secret mechanism, and allocate no TTY.
   Avoid requiring a source checkout or a host Python installation.
3. Make first-run diagnostics identify missing credentials, unreachable Galene,
   incorrect model route, unwritable ledger, and incompatible Docker/Codex
   configuration without printing secrets or candidate text.
4. Document installation, upgrade, rollback to a previous image digest,
   ledger backup/retention, and uninstall. Verify on every supported developer
   environment using a clean machine or clean user profile.

**Exit:** A teammate with no repository checkout can install, connect Codex,
discover all four MCP tools, complete a small live task, restart Codex, and
retrieve the persisted result. Rollback preserves the ledger or fails clearly
when a schema change prevents it.

## Gate 3: Prove the real workflow

Run the default profile with GaleneAI/Qwen 3.8 27B and the chosen Jev policy.
Test the whole Codex workflow: choose an eligible repository task, prepare the
minimum context, dispatch multiple independent contracts, retrieve every task
result, inspect candidate diffs, apply accepted work, and run that repository's
tests in its normal approved environment. Include at least one rejection,
provider failure, cancellation, and Codex restart. Record endpoint request IDs,
observed model route when the service exposes it, token usage, latency, and
task outcomes; keep secrets and source out of shared reports.

Use a fixed, representative task set and compare against Codex completing the
same class of tasks without the swarm. Track: candidate acceptance after review,
integration/test pass rate, rework, elapsed time, Galene/Jev requests and token
usage, cost where available, and operator friction. Record each task's scope and
reason for rejection. Do not claim a productivity or quality gain from a single
run or from model scores alone.

**Suggested pilot size:** 3-5 developers, at least 2 repositories, and roughly
20 eligible tasks over 1-2 weeks. These are planning targets, not statistical
proof. Set a baseline and a go/no-go threshold before viewing results.

**Exit:** A pilot report with raw run IDs and reproducible task descriptions,
aggregate outcomes, the main failure modes, and a decision to release, revise,
or stop. Release requires no critical data leak, no lost or misleading run state,
and repeatable installation on every supported environment.

## Separate verified-profile track

The current verified profile mounts the Docker socket, which grants control of
the host Docker daemon. It is not required to distribute or pilot the default
server. If the team elects to pilot executable verification, first define an
operator-approved threat model and host/environment scope, enforce a real hard
execution timeout with cleanup, and exercise the isolation boundary against a
real Docker daemon. Keep it opt-in and report its evidence separately.

## Order and ownership

| Step | Owner to assign | Deliverable |
|---|---|---|
| 0 | Product owner + GaleneAI owner + security/data owner | Pilot policy and live model route |
| 1 | Swarm maintainer | Lifecycle, validation, retention, failure semantics |
| 2 | Swarm maintainer + developer experience owner | Internal image, install/rollback guide, clean-environment proof |
| 3 | Pilot lead + participating developers | Real-task evidence and go/no-go report |

Dashboard, recursive workers, a Responses API proxy, distributed replicas, and
automatic patch application remain outside this release. Promote any of them
only through a separate scope decision and acceptance criteria.
