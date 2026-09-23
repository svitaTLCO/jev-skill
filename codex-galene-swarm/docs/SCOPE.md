# Product Scope

**Status:** Canonical for the current product boundary  
**Last reviewed:** 2026-09-23

## Purpose

Codex Galene Swarm lets Codex delegate several independent, bounded software
tasks to Qwen workers served by Galene, while Codex remains the only agent that
owns repository context, decides whether a candidate is useful, edits the
caller's worktree, and declares the overall work complete.

The product is an MCP service for controlled delegation. It is not an autonomous
multi-agent development environment.

## Actors and responsibilities

| Actor | Owns | Must not do |
|---|---|---|
| Operator | Credentials, server profile, verifier image, Docker-socket authorization | Treat optional model evaluation as executable proof |
| Codex | Task decomposition, minimum context, candidate review/application, repository validation, final answer | Delegate final accountability or expose unrelated repository data |
| Swarm service | Contract validation, dispatch, bounded concurrency, persistence, optional gates, result retrieval | Modify the caller's worktree |
| Galene/Qwen worker | Produce candidate text for one contract | Use tools, access the worktree, broaden scope, or coordinate other workers |
| Jev | Evaluate a candidate against its trusted contract when required | Execute code or replace repository tests |
| Docker verifier | Apply one bounded diff to an isolated copy and run an operator-supplied command | Modify the source repository or use the network |

## Supported use cases

The current service supports:

1. Codex submits between 1 and 12 independent task contracts under one goal.
2. The service runs them asynchronously with configured concurrency from 1 to 8.
3. Each worker returns `unified_diff`, `code`, or `analysis` text.
4. The service optionally requires a fail-closed Jev policy evaluation.
5. A `unified_diff` task may request executable verification when the privileged
   verifier profile was explicitly enabled.
6. Codex polls status, retrieves evidence and candidates, and may request
   cancellation.

Good swarm work is parallelizable and has a narrow objective, explicit
interfaces, enough context to work without repository access, an allowed-file
set, and observable acceptance checks. Cross-cutting design decisions,
repository exploration, sequential tasks, final integration, and release
decisions remain with Codex.

## Product invariants

These rules define the tool. A change that breaks one is a scope change, not a
routine implementation detail.

- Codex remains the orchestrator and final authority.
- Workers receive prompt text only. They get no shell, filesystem, MCP, network,
  credential, or worktree capability from this service.
- A worker handles one bounded contract and cannot create child workers.
- Worker output is an untrusted candidate, never an automatically accepted edit.
- The default server cannot execute generated code and cannot access the caller's
  repository or Docker daemon.
- Jev is optional unless the caller sets `require_jev=true`; when required,
  missing configuration or evaluation failure fails closed.
- Executable verification is opt-in, is limited to unified diffs and declared
  files, and runs only through the separately enabled verified profile.
- Model scores and syntax checks do not substitute for the repository's own
  executable acceptance tests.
- Run and task evidence is persisted without persisting provider credentials.
- Candidate review, application to the real worktree, integration testing, and
  user-facing completion remain outside the service.

## Task contract

The table below defines the intended JSON shape. The current implementation
enforces required scalar fields, task ID safety, output kind, token bounds,
verification-command bounds, and unknown-field rejection. Complete type and
size validation for every prompt-bearing list/string remains an identified gap
in `IMPLEMENTATION_STATUS.md`.

| Field | Required | Meaning and bounds |
|---|---:|---|
| `task_id` | yes | Unique within the run; alphanumeric plus `-` and `_` |
| `role` | yes | Worker posture, such as `implementer`, `reviewer`, or `analyst` |
| `objective` | yes | One concrete outcome |
| `interfaces` | no | Symbols, inputs, outputs, or protocols the candidate may rely on |
| `allowed_files` | no | Files the candidate may mention or modify; enforced for verified diffs |
| `acceptance_checks` | no | Contract-level conditions used by the worker and Jev |
| `context` | no | Minimum repository information needed; treated as untrusted data |
| `output_kind` | no | `unified_diff` (default), `code`, or `analysis` |
| `max_tokens` | no | Completion ceiling from 1 to 4,000; default 1,400 |
| `verification_command` | no | Argument vector, maximum 32 parts and 4,096 characters total |

A verification command requires `output_kind="unified_diff"` and at least one
`allowed_files` entry. Contracts reject unknown fields instead of silently
ignoring them.

## Evidence and success semantics

- `swarm_status` returns run/task state and contracts without candidate bodies.
- `swarm_result` returns stored candidates, provider metadata, Jev evidence,
  verification evidence, and errors.
- A task is `passed` only after every requested gate passes. A Jev rejection or
  a non-zero verification exit is `rejected`; provider or verification
  infrastructure errors are `failed`.
- A run is `completed` when at least one terminal task is not `failed` or
  `cancelled`. Consequently, callers must inspect every task; `completed` does
  not mean every task passed.

## Explicit non-goals

The current scope does not include:

- automatic candidate application or merge;
- autonomous repository exploration by workers;
- recursive delegation or worker-to-worker communication;
- dependency scheduling between tasks;
- a dashboard or human workflow UI;
- a Responses API compatibility proxy;
- distributed execution across service replicas;
- hard interruption of an in-flight provider, Jev, or verifier request;
- production tenancy, remote-user authentication, quotas, or billing;
- claiming that one live smoke run establishes model quality or performance.

Dashboard, recursive-agent, and Responses API ideas are uncommitted possibilities,
not implied next steps. Moving any non-goal into scope requires an explicit
decision, acceptance criteria, threat-model review, and an update to this file.

## Definition of done for a product change

A behavior change is complete only when:

1. Its contract and failure behavior are explicit.
2. It preserves the product invariants or records an approved scope change.
3. Unit/integration tests cover success and material failure paths.
4. The Dockerized test suite passes.
5. Security-sensitive runtime behavior is validated at the real boundary when
   applicable; mocks alone are labeled as such.
6. README/operator guidance and `IMPLEMENTATION_STATUS.md` reflect the result.
