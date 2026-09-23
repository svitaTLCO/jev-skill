# Codex Galene Swarm contributor guide

This directory is an independently owned project within the parent checkout.
Keep its implementation and documentation changes inside this directory unless
the user explicitly requests a shared/root-level change.

## Required reading order

Before changing behavior, read:

1. `README.md`
2. `docs/SCOPE.md`
3. `docs/ARCHITECTURE.md`
4. `docs/IMPLEMENTATION_STATUS.md`
5. the relevant source and tests

`docs/SCOPE.md` is canonical for product boundaries and invariants. Possible
future work and open engineering gaps are not approved tasks and have no implied
priority. Obtain an explicit objective and acceptance criteria before implementing
one of them.

## Working rules

- Codex remains the orchestrator. Qwen workers return untrusted candidates and
  never receive repository, shell, tool, credential, or recursive-agent access.
- Preserve unrelated dirty files and inspect status/diff before and after edits.
- Run code, tests, builds, dependency work, and live checks only in Docker.
- Use the parent checkout's RTK-prefixed command convention.
- The default validation command from the parent checkout is:

  ```bash
  rtk docker compose -f codex-galene-swarm/docker-compose.yml run --rm test
  ```

- Do not enable the `verified` profile without explicit operator approval for
  that task. It mounts the Docker socket and therefore controls the host daemon.
- Do not run credentialed live smoke tests unless they are needed for the task;
  report their external/billable nature and never print secrets or candidates.
- A passing fake-boundary suite is not proof of live Galene, Jev, or Docker
  verifier behavior. State the exact boundary validated.
- Update `docs/IMPLEMENTATION_STATUS.md` whenever capability, test health, known
  issues, or failed approaches change.
- Update `docs/SCOPE.md` only for an explicit product-boundary decision, and keep
  `docs/ARCHITECTURE.md` aligned with material runtime or security changes.

## Completion gate

A change is ready for handoff only after the relevant failure paths are tested,
the complete Dockerized suite passes, documentation matches behavior, and the
final diff is checked for scope drift and credential exposure. Codex still owns
reviewing and applying worker candidates and running repository-level validation.

