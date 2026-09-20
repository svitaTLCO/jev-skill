# AGENTS.md — Autonomous Agent Workspace & Swarm Guide

Welcome to the **TypeSafe AI (Jev) & Local SLM Swarm** development environment.
This repository enables coding agents (such as **OpenCode** and **Antigravity**) to coordinate local Small Language Models (SLMs) with **TypeSafe Jev System One** as an architectural judge and quality gate.

---

## 1. Available Local Models in OpenCode

Local models are served via **Ollama** on `http://127.0.0.1:11434/v1` and configured in `opencode.json` and `~/.config/opencode/opencode.jsonc`:

| Model Identifier | Parameter Size | Context Window (`num_ctx`) | Specialization / Role in Swarm |
| :--- | :--- | :--- | :--- |
| **`ollama/huihui-qwen3.5:2b`** | 1.9B (Q4_K_M) | 32,768 tokens (32k) | **Deep Brain / Complex Logic**: Vector math, multi-file REST endpoints, AST patching, algorithm synthesis. |
| **`ollama/huihui-qwen3.5:0.8b`** | 752M (Q4_K_M) | 16,384 tokens (16k) | **Agile Micro-Worker**: Rapid micro-contracts (<20 lines), state machines, audio frequencies, data schemas. |
| **`opencode/jev-latest`** | System One | 8k tokens | **Supreme Hivemind & Inspector**: Instant structured choices (`Choice`), scores (`Score`), and risk gates (`Noul`). |

### Running OpenCode with Local Swarm Models
```bash
# Launch OpenCode interactive TUI with the 2B abliterated model
opencode -m ollama/huihui-qwen3.5:2b

# Launch OpenCode interactive TUI with the 0.8B ultra-fast model
opencode -m ollama/huihui-qwen3.5:0.8b

# Run a headless task via OpenCode CLI
opencode run -m ollama/huihui-qwen3.5:2b "Implement a generic TokenBucket rate limiter in Python"
```

---

## 2. Integrated Skills & Toolkits

### Skill: `typesafe-ai`
The `typesafe-ai` skill is registered and auto-discovered in OpenCode from `.opencode/skills/typesafe-ai/` and `~/.agents/skills/typesafe-ai/`.

Key workflows provided by the skill:
1. **Pre-Planning Prompt Disambiguation**:
   ```bash
   python3 scripts/jev_eval.py --prompt "Task description..." --mode prompt
   ```
2. **Implementation Plan Quality Gating**:
   ```bash
   python3 scripts/jev_eval.py --file implementation_plan.md --prompt "Task Goal" --mode plan
   ```
3. **Generic 3-Tier Swarm Verification**:
   - **Tier 1 (Runtime Sanity)**: Headless AST compilation (`ast.parse` / `node -e "new vm.Script(...)"`) ensuring exit code `0`.
   - **Compiler-in-the-Loop Self-Healing**: Automatically feeds compiler stderr back to the SLM with `num_predict >= 1200` to fix syntax and reference defects.
   - **Tier 2 (Jev Contract Gates)**: Calibrated `Noul` checks on **Reference Integrity** ($P(\text{Yes}) \ge 0.70$) and **Specification Compliance** ($P(\text{Yes}) \ge 0.70$).
   - **Tier 3 (Quality & Choice)**: Calibrated continuous scoring `Score` [0.0 - 3.0] and `Choice` selection.

---

## 3. Reusable Python Swarm API

Any script or agent can import and use the swarm engine directly:

```python
from scripts.jev_swarm import JevSwarm, GenericRuntimeValidator

# Initialize swarm with local 2B model
swarm = JevSwarm(default_worker_model="huihui-qwen3.5:2b")

# Execute a micro-contract with automatic Tier 1, Self-Healing, and Tier 2 Jev gating
result = swarm.execute_micro_contract(
    task_id="rate_limiter",
    prompt="Write a Python class TokenBucket with allow_request(tokens). Output ONLY the class.",
    lang="python",
    spec_requirement="Does TokenBucket properly refill tokens based on elapsed time without race conditions?",
    max_tokens=1200,
    min_noul=0.70
)

if result["passed"]:
    print(f"✅ Quality Score: {result['quality_score']}/3.0")
    print(result["code"])
```

---

## 4. Key Engineering Invariants for Swarms

1. **Strictly Domain-Agnostic**: All swarm tooling, prompts, and gates must apply across backend microservices, data transformations, CLI tools, and web applications.
2. **Interface Contracts Only**: Never feed accumulated monolithic code into downstream micro-prompts. Small models suffer reasoning expansion (>600 tokens in `<think>`). Pass only concise TypeScript/Python interface declarations.
3. **Token Budgets**: For `huihui-qwen3.5` models, configure `num_predict >= 1200` to prevent mid-loop truncation caused by reasoning tags.
