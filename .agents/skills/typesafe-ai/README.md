# TypeSafe AI (Jev) Skill for Coding Agents

A specialized agent skill and CLI toolkit that empowers AI coding agents to use **[TypeSafe AI's Jev model](https://docs.typesafe.ai/introduction)** (System One) to systematically evaluate, verify, and improve code quality, as well as integrate TypeSafe capabilities into projects.

---

## What is TypeSafe / Jev?

[Jev](https://docs.typesafe.ai/introduction) is TypeSafe's flagship **System One** model. Instead of generating freeform text or code, it makes fast, structured decisions:
- **`Choice`**: Selects between discrete options with probability distributions and confidence.
- **`Score`**: Positions input along ordered, descriptive rubric levels (e.g. 0 to 3 maintainability).
- **`Noul`**: Computes calibrated probabilities $P(\text{Yes}) \in [0.0, 1.0]$ for binary sanity checks (e.g., regression risks).

---

## Directory Structure

```text
.
├── SKILL.md                          # Main skill definition & agent instructions
├── scripts/
│   ├── jev_eval.py                   # Zero-dependency CLI for code evaluations
│   └── test_connection.py            # Diagnostic script to test API key & latency
├── references/
│   ├── api_reference.md              # Complete TypeSafe System One API schema
│   ├── primitives_guide.md           # Guide to Choice, Score, and Noul
│   └── evaluation_rubrics.md         # Standard rubrics for maintainability & security
├── examples/
│   ├── code_review_example.json      # Sample code evaluation payload
│   └── refactor_decision.json        # Sample architectural choice payload
└── README.md                         # This file
```

---

## Getting Started

### 1. Set Your TypeSafe API Key

Obtain your API key from the [TypeSafe Console](https://console.typesafe.ai/keys) and export it:

```bash
export TYPESAFE_API_KEY="your_api_key_here"
```

Verify your connection with the diagnostic script:

```bash
python3 scripts/test_connection.py
```

### 2. Evaluate Code with `jev_eval.py`

You or your coding agent can run code evaluations directly:

```bash
# Evaluate a single file against a task specification
python3 scripts/jev_eval.py \
  --file path/to/code.py \
  --prompt "Implement an LRU cache with O(1) get and put"

# Evaluate a git diff
git diff > /tmp/change.patch
python3 scripts/jev_eval.py \
  --diff /tmp/change.patch \
  --prompt "Refactor user authentication handler"

# Run in security audit mode
python3 scripts/jev_eval.py \
  --file path/to/api.py \
  --mode security

# Phase 1: Disambiguate & enhance user prompts before planning
python3 scripts/jev_eval.py \
  --prompt "Create an interactive 3D Palio di Siena game in browser" \
  --mode prompt

# Phase 2: Gate implementation plans before execution
python3 scripts/jev_eval.py \
  --file implementation_plan.md \
  --prompt "Build Palio di Siena 3D Game" \
  --mode plan
```

### 3. Batched Questioning (Zero Latency Speculation)

Jev processes an entire dictionary of multiple typed questions (`Choice`, `Score`, `Noul`) over the same state in a **single HTTP call** with **zero added latency** (~750ms total). This allows agents to front-load critical constraints before writing a single line of code:
- **Prompt Enhancement**: Resolves architectural direction, scope boundaries, and flags overengineering risks before drafting a plan.
- **Plan Gating**: Scores plan soundness and detects bloated abstractions or unverified hand-waving before implementation begins.

See [`references/prompt_enhancement_and_planning.md`](./references/prompt_enhancement_and_planning.md) for full details.

### 4. Jev-Orchestrated Micro-Stepping (Small Model / SLM Orchestration)

Small language models (1B–7B parameters, e.g. local Ollama models) often fail on monolithic zero-shot prompts due to attention drift and repetitive token loops.

With **Jev Micro-Stepping**:
1. **Jev chooses the blueprint** (`Choice` primitive, ~700ms).
2. The small model is given a **narrow, 5-line component** task (e.g. just the physics object).
3. **Jev verifies each component** (`Noul` primitive, ~600ms).
4. The system assembles the verified blocks into a functioning whole in under 15 seconds.

See [`references/micro_orchestration_guide.md`](./references/micro_orchestration_guide.md) for full details.

---

## Installing into AI Coding Agents

### Antigravity
To make this skill available across your Antigravity workspaces:
1. **Workspace Level**: Place this skill inside `.agents/skills/typesafe-ai/` in any project.
2. **Global Level**: Copy or symlink this folder to `~/.gemini/config/skills/typesafe-ai/`:
   ```bash
   mkdir -p ~/.gemini/config/skills
   cp -r /Users/sandrovita/jev-skill ~/.gemini/config/skills/typesafe-ai
   ```

### Claude Code
```bash
claude plugin marketplace add typesafe-ai/skills
claude plugin install typesafe@typesafe-ai
```

---

## Documentation Links

- [TypeSafe Documentation](https://docs.typesafe.ai)
- [System One Mental Model](https://docs.typesafe.ai/concepts/system-one.md)
- [Cookbooks](https://docs.typesafe.ai/cookbooks)
- [Python SDK Reference](https://docs.typesafe.ai/sdk/python.md)
