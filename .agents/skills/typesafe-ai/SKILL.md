---
name: typesafe-ai
description: >-
  Use TypeSafe AI's System One model (Jev) to evaluate, review, and improve code quality,
  gate prompt enhancement and implementation plans, verify edge cases and regressions, select
  optimal architectural designs, orchestrate small local models (SLMs) via step-by-step
  micro-component decomposition, and build applications using TypeSafe's typed decision primitives (Choice, Score, Noul).
---

# TypeSafe AI (Jev) Code Intelligence & Evaluation Skill

This skill teaches the coding agent how to leverage [TypeSafe AI](https://docs.typesafe.ai/introduction) and its flagship **System One model (Jev)** as an **active architectural co-pilot, decision engine, and quality gate** to elevate code quality, verify solutions against specifications, and coordinate local Small Language Model (SLM) swarms.

---

## 1. Mental Model: System One as an Architectural Co-Pilot

Unlike standard LLMs that generate freeform conversational prose, **Jev** is a **System One** model trained to make **fast, calibrated, and structured decisions**.

- **Input**: Natural language context and state (code, diffs, user requirements, schemas).
- **Questions**: Typed queries evaluated in parallel.
- **Output**: Typed choices, continuous scores, and calibrated probabilities (not unverified prose).

### The Three Primitives

| Primitive | Software Engineering Application | Result Type |
| :--- | :--- | :--- |
| **`Choice`** | Selecting between competing architectural patterns, algorithms, or refactoring strategies. | Selected option, distribution over choices, confidence. |
| **`Score`** | Evaluating code maintainability, test thoroughness, security posture, or simplicity. | Continuous score along descriptive rubric levels, confidence. |
| **`Noul`** | Binary sanity check: regression risk, spec adherence, edge-case safety, reference integrity. | Calibrated probability $P(\text{Yes}) \in [0.0, 1.0]$. |

---

## 2. Empirical Discoveries & Engineering Invariants

Empirical research across local SLM swarms (`huihui-qwen3.5:2b`, `huihui-qwen3.5:0.8b`, and `llama3-groq-tool-use:8b`) revealed critical failure modes and architectural solutions:

1. **The "Accumulated Code" Prompt Trap**:
   Passing full accumulated code from earlier steps into downstream worker prompts causes `<think>` reasoning token explosion (>600 tokens). Workers exhaust their token limits mid-line, causing secondary syntax truncations.
   *Invariant*: Pass **only concise interface declarations** (TypeScript types, Python type signatures, JSDoc schemas) into downstream prompts.

2. **Abliteration Scope Creep**:
   Sub-2B abliterated models frequently invent unasked helper functions or endpoints.
   *Invariant*: Gate every generated micro-contract through Jev's `reference_integrity` ($P \ge 0.70$) and `no_scope_creep` ($P \ge 0.70$) checks.

3. **Localized AST Patching vs. Full-File Regeneration**:
   When compiler checks fail, asking an SLM to rewrite the entire file fails (0% pass rate under moderate budgets).
   *Invariant*: Feed exact compiler tracebacks back to the worker with `num_predict >= 1200` to apply a **localized AST patch**, achieving a 100% healing rate.

4. **Upfront Architecture Selection (`Choice`)**:
   SLMs struggle when forced to pick complex architectures on the fly.
   *Invariant*: Use Jev's `Choice` primitive to evaluate trade-offs and select the architectural pattern *before* workers generate code.

5. **Multi-Candidate Arena Filtering**:
   Stochastic variance in SLMs causes quality scores to fluctuate between 0.07 and 1.67.
   *Invariant*: Generate 2–3 candidates for critical modules and use Jev to score and promote the best candidate.

6. **The "No-Think" Latency & Anti-Truncation Paradigm**:
   Enabling `<think>` mode on sub-5B models causes reasoning monologues consuming 600–1,200 tokens, degrading latency by 3x and causing frequent mid-line syntax truncations without improving algorithmic logic.
   *Invariant*: Disable reasoning mode (`think: False`, `/no_think`) on all code worker prompts. Use TypeSafe Jev System One as the reasoning co-pilot.

7. **The 2B + 4B Cognitive Tier Division**:
   - **4B (`qwen3.5:4b`)**: Minimum viable parameter threshold for cold synthesis of complex pointer-based data structures (LRU cache, MinHeap) and multi-state parsers (100% first-pass pass rate).
   - **2B (`qwen3.5:2b`)**: High-speed micro-worker for linear contracts, schemas, physics, and state transitions (2.5x faster throughput).

---

## 3. Evaluation CLI (`scripts/jev_eval.py`)

The helper script `scripts/jev_eval.py` supports direct code strings, files, diffs, and prompts:

```bash
# 1. Architectural Choice Decision
python3 scripts/jev_eval.py --prompt "Compare FastAPI vs SQLite raw for telemetry" --mode choice

# 2. Micro-Contract & Reference Integrity Gate
python3 scripts/jev_eval.py --code "def compute_tax(subtotal): return subtotal * tax_rate" --prompt "Tax calculator" --mode contract

# 3. Pre-Planning Prompt Disambiguation
python3 scripts/jev_eval.py --prompt "Build a full-stack telemetry dashboard" --mode prompt

# 4. Implementation Plan Quality Gate
python3 scripts/jev_eval.py --file implementation_plan.md --prompt "Task Goal" --mode plan

# 5. Compiler-in-the-Loop Localized Healing Check
python3 scripts/jev_eval.py --code "<failing_code_or_patch>" --prompt "Fix SyntaxError: expected ':'" --mode healing

# 6. Multi-Candidate Arena Evaluation
python3 scripts/jev_eval.py --code "<candidate_code>" --prompt "Evaluate candidate implementation" --mode arena
```

*(Requires `TYPESAFE_API_KEY` set in the environment, Keychain, or passed via `--api-key`).*

---

## 4. Reusable Python Swarm API (`scripts/jev_swarm.py`)

Import `JevSwarm` to orchestrate local SLMs and Jev System One programmatically:

```python
from scripts.jev_swarm import JevSwarm

# Cognitive tier defaults: agile="qwen3.5:2b", deep="qwen3.5:4b" with think: False
swarm = JevSwarm()

# Upfront architectural selection
decision = swarm.evaluate_architecture_choice(
    prompt="Design a rate limiting mechanism",
    options=["TokenBucket (in-memory)", "LeakyBucket (in-memory)", "SlidingWindow (Redis)"]
)

# Execute micro-contract with tier selection ('agile' or 'deep')
result = swarm.execute_micro_contract(
    task_id="rate_limiter",
    prompt="Write a Python class TokenBucket with allow_request(tokens). Output ONLY the class.",
    tier="deep",  # or 'agile' for fast micro-contracts
    lang="python",
    spec_requirement="Does TokenBucket properly refill tokens based on elapsed time without race conditions?",
    max_tokens=1200,
    min_noul=0.70,
    sample_candidates=2  # Runs Arena if > 1 candidate requested
)

# Extract interface contract to shield downstream workers from the prompt trap
interface_contract = swarm.extract_interface_contract(result["code"], lang="python")
```

---

## 5. Direct API Calls (HTTP & SDK)

### Direct API Call (curl)
```bash
curl -X POST https://api.typesafe.ai/v1/systemone \
  -H "Authorization: Bearer $TYPESAFE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "state": "User requested account cancellation due to price",
    "model": "jev-latest",
    "questions": {
      "intent": {
        "type": "choice",
        "instructions": "Identify the user retention category",
        "criteria": {
          "churn_risk": "Explicitly wanting to cancel subscription",
          "discount_inquiry": "Asking for cheaper tier",
          "technical_support": "Encountering usability issues"
        }
      }
    }
  }'
```

### Python SDK (`typesafe-sdk`)
```python
from typesafe_sdk import TypeSafeClient, Choice, Score, Noul

client = TypeSafeClient()  # reads TYPESAFE_API_KEY
response = client.system_one(
    state="Incoming ticket content...",
    questions={
      "priority": Score(
          instructions="Rate customer urgency",
          criteria=["Low", "Medium", "High", "Critical"]
      ),
      "is_bug": Noul(instructions="Does this describe a software defect?")
    }
)
```

---

## 6. References & Documentation

- [Theoretical Limits & Empirical Report](./references/theoretical_limits_report.md): Full empirical benchmarks on SLM limits, token ceilings, and self-healing.
- [Swarm Orchestration Guide](./references/swarm_orchestration_guide.md): Scaling horizontal micro-specialist swarms (0.8B to 3B) under Jev.
- [Prompt Enhancement & Planning Guide](./references/prompt_enhancement_and_planning.md): Batch prompt disambiguation & implementation plan quality gating.
- [Primitives Guide](./references/primitives_guide.md): Deep-dive into Choice, Score, and Noul.
- [Micro-Orchestration Guide](./references/micro_orchestration_guide.md): Step-by-step small model orchestration patterns.
- [API Reference](./references/api_reference.md): HTTP schema, error codes, and headers.
- [Standard Evaluation Rubrics](./references/evaluation_rubrics.md): Production-tested rubrics for code reviews.
