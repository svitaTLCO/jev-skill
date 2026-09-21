# AGENTS.md — Autonomous Agent Workspace & Swarm Guide

Welcome to the **TypeSafe AI (Jev) & Local SLM Swarm** development environment.
This repository enables coding agents (such as **OpenCode** and **Antigravity**) to coordinate local Small Language Models (SLMs) with **TypeSafe Jev System One** as an active architectural co-pilot, decision engine, and quality gate.

---

## 1. Available Models in OpenCode

Local models are served via **Ollama** with the **Ollama Fast Proxy** on `http://127.0.0.1:11435/v1` (upstream port 11434, enforcing No-Think and 32k context) and configured in `opencode.json` and `~/.config/opencode/opencode.jsonc`:

| Model Identifier | Parameter Size | Context Window (`num_ctx`) | Specialization / Role in Swarm |
| :--- | :--- | :--- | :--- |
| **`ollama/qwen3.5:4b`** | 3.4B (Q4_K_M) | 32,768 tokens (32k) | **Primary Deep Brain (`local` mode) & Tool Specialist (`@tool-runner`)**: High-context (32k), complex data structures, 100% BFCL tool-calling accuracy, and deep code synthesis. |
| **`ollama/qwen3.5:2b`** | 1.9B (Q4_K_M) | 32,768 tokens (32k) | **Agile Micro-Worker (`@agile`)**: Lightning-fast micro-contracts (<15s), concurrency primitives, API schemas, physics, and component slots. |
| **`opencode/jev-latest`** | System One | 8k tokens | **Supreme Hivemind, Co-Pilot & Inspector**: Instant structured choices (`Choice`), scores (`Score`), pre-flight tool routing, and risk gates (`Noul`). |

### Running OpenCode in `local` Mode
Switch to `local` mode in the OpenCode TUI via `Tab` (or cycle through `build`, `plan`, `local`), or launch directly:
```bash
# Launch OpenCode in local mode (driven by Qwen 3.5 4B Deep Brain with 32k context)
opencode --agent local
```
In `local` mode:
1. **Qwen 3.5 4B** manages conversational design, complex algorithmic logic, and code synthesis.
2. **`@agile`** (**Qwen 3.5 2B**) handles rapid micro-contracts and isolated atomic functions.
3. **`@jev-judge`** acts as the architectural co-pilot for high-level pattern decisions (`Choice`), interface contract formulation, and contract gating.
4. **`@tool-runner`** (**Qwen 3.5 4B**) performs schema-strict tool execution, bash commands, file editing, and test runs without distractor confusion (32k context).

---

## 2. Integrated Skills & Toolkits

### Skill: `typesafe-ai`
The `typesafe-ai` skill is registered and auto-discovered in OpenCode from `.opencode/skills/typesafe-ai/` and `~/.agents/skills/typesafe-ai/`.

Key workflows provided by `scripts/jev_eval.py`:
1. **Pre-Flight Tool Routing & Abstention Gate (`--mode tool`)**:
   ```bash
   python3 scripts/jev_eval.py --prompt "Find calculate_hash in src/" --mode tool
   ```
2. **Interface Contract Extraction (`--mode interface`)**:
   ```bash
   python3 scripts/jev_eval.py --file src/server.py --mode interface
   ```
3. **Upfront Architectural Decisions (`--mode choice`)**:
   ```bash
   python3 scripts/jev_eval.py --prompt "Compare FastAPI vs SQLite raw for telemetry" --mode choice
   ```
4. **Micro-Contract & Reference Integrity Gating (`--mode contract`)**:
   ```bash
   python3 scripts/jev_eval.py --code "def compute_tax(subtotal): return subtotal * tax_rate" --prompt "Tax calculator" --mode contract
   ```
5. **Pre-Planning Prompt Disambiguation (`--mode prompt`)**:
   ```bash
   python3 scripts/jev_eval.py --prompt "Build a full-stack telemetry dashboard" --mode prompt
   ```
6. **Implementation Plan Quality Gating (`--mode plan`)**:
   ```bash
   python3 scripts/jev_eval.py --file implementation_plan.md --prompt "Task Goal" --mode plan
   ```
7. **Compiler-in-the-Loop Localized Healing (`--mode healing`)**:
   ```bash
   python3 scripts/jev_eval.py --code "<failing_code_or_patch>" --prompt "Fix SyntaxError: expected ':'" --mode healing
   ```
8. **Multi-Candidate Arena Evaluation (`--mode arena`)**:
   ```bash
   python3 scripts/jev_eval.py --code "<candidate_code>" --prompt "Compare candidate against specification" --mode arena
   ```

---

## 3. Reusable Python Swarm API

Any script or agent can import and use the upgraded swarm engine directly:

```python
from scripts.jev_swarm import JevSwarm, GenericRuntimeValidator

# Initialize swarm with Jev System One governance (default: qwen3.5:2b agile worker)
swarm = JevSwarm()

# 1. Upfront Architectural Decision via Jev Choice
decision = swarm.evaluate_architecture_choice(
    prompt="Design a rate limiting mechanism",
    options=["TokenBucket (in-memory)", "LeakyBucket (in-memory)", "SlidingWindow (Redis)"]
)
print(f"Selected Pattern: {decision['selected_choice']}")

# 2. Execute a micro-contract with automatic Tier 1, Unit Test verification, and Tier 2 Jev gating
result = swarm.execute_micro_contract(
    task_id="rate_limiter",
    prompt="Write a Python class TokenBucket with allow_request(tokens). Output ONLY the class.",
    lang="python",
    tier="agile",  # "agile" routes to qwen3.5:2b, "deep" routes to qwen3.5:4b
    spec_requirement="Does TokenBucket properly refill tokens based on elapsed time without race conditions?",
    max_tokens=1200,
    min_noul=0.70,
    sample_candidates=2  # Runs Arena if > 1 candidate requested
)

if result["passed"]:
    print(f"✅ Promoted Candidate Quality Score: {result['quality_score']}/3.0")
    print(result["code"])

# 3. Extract pure interface contract to shield downstream workers from the prompt trap
interface_contract = swarm.extract_interface_contract(result["code"], lang="python")
```

---

## 4. Empirical Discoveries & Engineering Invariants

From our empirical research on small language models (`references/theoretical_limits_report.md`):

1. **The "Accumulated Code" Prompt Trap**:
   Never feed raw accumulated implementation code into downstream micro-prompts. Small models suffer reasoning explosion (`>600 tokens` in `<think>`), truncating before code completion. Always pass **concise interface declarations** (TypeScript types, Python type signatures, JSDoc schemas).
2. **Abliteration Scope Creep**:
   Sub-2B abliterated models frequently invent unasked helper functions or endpoints that exhaust token budgets mid-line. Use Jev's `reference_integrity` ($P \ge 0.70$) and `no_scope_creep` ($P \ge 0.70$) gates to reject polluted outputs.
3. **Localized AST Patching vs. Full-File Regeneration**:
   When compiler diagnostics fail:
   - Full-file regeneration: **0% success rate** due to token exhaustion.
   - Localized AST patching with `num_predict >= 1200`: **100% autonomous healing**.
4. **Upfront Architecture Selection (`Choice`)**:
   SLMs struggle if left to pick high-level design patterns arbitrarily. Jev's `Choice` primitive selects the minimal, robust architectural pattern before workers generate code.
5. **Multi-Candidate Arena Filtering**:
   Stochastic variance in SLMs can produce scores ranging from 0.07 to 1.67. Sampling 2–3 candidates and letting Jev score and promote the best implementation dramatically raises system reliability.
6. **The "Thinking Mode" Anti-Pattern for Small Models (`think: False`)**:
   Small models (0.8B–4B) spend 600–1,200 tokens deliberating inside `<think>`, wasting 20–70s per worker and triggering truncation syntax errors. Disabling thinking (`think: False`, `/no_think`) yields **68% token reduction**, **cuts latency by 65%**, and dramatically improves test pass rates on clean contracts.
7. **2B (Agile) + 4B (Deep Brain) Cognitive Division**:
   - Sub-3B models consistently fail cold synthesis of intricate pointer structures (custom LRU cache) and state machines (bracket quote parsing).
   - **`qwen3.5:4b`** in No-Think mode achieves a **100% pass rate** on complex data structures in 12–25s, while **`qwen3.5:2b`** handles fast micro-contracts and schemas (<15s).
