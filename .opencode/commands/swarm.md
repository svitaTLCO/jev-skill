---
description: Decompose a software engineering task into micro-contracts, dispatch to local SLM swarm workers, and gate via TypeSafe Jev 3-Tier Verification and Architectural Co-Pilot.
agent: local
---

Execute the requested task using the TypeSafe Jev Swarm methodology:
$ARGUMENTS

### 🚨 Autonomous Continuity Mandate (Zero-Halt Execution):
- **DO NOT pause or stop between stages to summarize progress, announce intentions in text, or ask "Shall I proceed?".**
- If you output conversational text without a tool call, OpenCode will yield control and wait for the human. Therefore, **EVERY intermediate step MUST immediately invoke the next tool call or subagent delegation (`task`)**.
- Run through all 5 stages autonomously and continuously without stopping until Stage 5 verification is complete. Only write conversational summaries when the final solution is verified and delivered.

Follow this 5-stage empirical workflow:

1. **Stage 1: Architectural Selection via Jev (`Choice`)**:
   - If there are architectural decisions (e.g., synchronous vs. event-driven, single-file vs. modular, relational vs. key-value), invoke `@jev-judge` or run:
     `python3 scripts/jev_eval.py --prompt "Task Requirements..." --mode choice`
   - Adopt the chosen design pattern before writing any micro-contracts.

2. **Stage 2: Micro-Contract Blueprinting & Interface Formulation**:
   - Decompose the task into 3-5 atomic, decoupled micro-contracts (data models, core logic, API/storage, tests).
   - **Enforce Interface Isolation**: Pass ONLY concise interface definitions (TypeScript types, Python signatures, JSDoc schemas) to workers. Never feed raw accumulated code into downstream worker prompts (prevents the *Accumulated Code Prompt Trap*).

3. **Stage 3: Swarm Worker Execution & Arena Sampling (No-Think Enabled)**:
   - Dispatch each micro-contract with thinking mode disabled (`think: False` / `/no_think`):
     - Use `@deep` / `qwen3.5:4b` for complex algorithms, data structures, state machines, and AST transformations.
     - Use `@agile` / `qwen3.5:2b` for rapid schemas, lookup tables, physics/audio loops, and micro-contracts (<20 lines).
   - For mission-critical logic, sample 2-3 candidate implementations for Jev Arena evaluation.

4. **Stage 4: Generic 3-Tier Verification & Localized Self-Healing**:
   - **Tier 1 (Runtime Sanity)**: Compile AST headlessly (`python3 -c "import ast; ast.parse(...)"` or `node -e "new vm.Script(...)"`).
   - **Compiler-in-the-Loop Healing**: If Tier 1 fails, pass the compiler traceback back to the worker with `num_predict >= 1200` to apply a **localized AST patch**. Do NOT regenerate the full file.
   - **Tier 2 (Jev Contract Gates)**: Run `@jev-judge` or `python3 scripts/jev_eval.py --code "..." --prompt "<spec>" --mode contract`. Ensure Reference Integrity ($P \ge 0.70$) and Spec Compliance ($P \ge 0.70$).
   - **Tier 3 (Quality Score & Arena Selection)**: Score maintainability [0.0 - 3.0] and promote the winning candidate.

5. **Stage 5: Final Assembly & System Verification**:
   - Assemble the verified micro-contracts, ensuring zero namespace collisions or variable re-declarations.
   - Run end-to-end unit tests and deliver the final solution.
