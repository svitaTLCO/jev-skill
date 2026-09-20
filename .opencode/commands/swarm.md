---
description: Decompose a software engineering task into micro-contracts, dispatch to local SLM swarm workers, and gate via TypeSafe Jev 3-Tier Verification.
agent: build
---

Execute the requested task using the TypeSafe Jev Swarm methodology:
$ARGUMENTS

Follow this workflow:
1. Blueprinting: Decompose the task into 3-5 atomic, decoupled micro-contracts (data models, business logic, storage/API, tests).
2. Swarm Execution: Dispatch each micro-contract to the appropriate subagent:
   - Use @swarm-worker-2b for complex logic, algorithms, and AST manipulation.
   - Use @swarm-worker-08b for rapid lightweight micro-contracts and schemas.
3. Generic 3-Tier Verification:
   - Tier 1: Check runtime syntax / compilation (ast.parse / node vm.Script) with exit code 0.
   - Self-Healing: If Tier 1 fails, feed compiler stderr back to the worker to self-heal.
   - Tier 2: Evaluate Reference Integrity (Noul >= 0.70) and Spec Compliance (Noul >= 0.70) using @jev-judge or `jev-eval --file <file> --prompt "<spec>"`.
   - Tier 3: Score maintainability [0.0 - 3.0] and assemble the final deliverable.
