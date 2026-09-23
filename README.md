# TypeSafe AI (Jev) & Local SLM Swarm

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-brightgreen.svg)](https://www.python.org/downloads/)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-zero%20external-success.svg)](requirements.txt)
[![Hardware: Apple Silicon](https://img.shields.io/badge/hardware-Apple%20Silicon%20(16GB%20RAM)-lightgrey.svg)]()
[![Orchestrator: TypeSafe Jev](https://img.shields.io/badge/orchestrator-TypeSafe%20Jev%20System%20One-purple.svg)](https://docs.typesafe.ai)
[![SLM Models: Qwen 3.5](https://img.shields.io/badge/slm%20workers-Qwen%203.5%20(2B%20%7C%204B)-orange.svg)](https://ollama.com)
[![Tool Calling: 90%](https://img.shields.io/badge/tool%20calling-90%25%20checked--in%20benchmark-yellow.svg)](benchmarks/tool_calling_results.json)

**Empirical research, agent skills, and a production-grade swarm orchestration engine coordinating local Small Language Models (SLMs) under the strict supervision of TypeSafe AI's System One model (Jev).**

[Arcade Showcase](benchmarks/index.html) • [Quickstart](#-3-minute-quickstart) • [Architecture](#-architecture--3-tier-verification) • [Empirical Benchmarks](#-empirical-benchmarks) • [Agent Integrations](#-ai-coding-agent-integrations)

</div>

---

## 💡 The Core Thesis

Small Language Models (1.5B–4B parameters) can run locally on consumer hardware such as Apple Silicon. Local inference stays on-device; TypeSafe Jev review is an external API call. However, when assigned complex, monolithic coding tasks, they frequently encounter critical failure modes:

1. **The "Accumulated Code" Prompt Trap**: When raw accumulated implementation code is fed into downstream prompts, small models suffer reasoning explosion (`>600 tokens` in `<think>`), truncating before code completion.
2. **Abliteration Scope Creep & Structural Hallucination**: Small models invent unprompted helper functions, unasked endpoints, or re-declare global state mid-line.
3. **Reasoning Deliberation Delays**: Sub-4B models spend 20–70s deliberating inside `<think>`, wasting token budgets and risking empty-thought halts.
4. **Algorithmic State Breakdown**: Sub-3B models struggle with complex data structures (LRU caches, custom allocators) and nested bracket parsing.

### The Solution: TypeSafe Jev System One + Local Cognitive Division

Rather than paying massive latency and cloud API costs for frontier models on every single token, we deploy **TypeSafe Jev System One** as an ultra-fast (~650ms) architectural co-pilot and calibrated decision gate over an orchestrated swarm of specialized local SLMs:

- **Agile Micro-Worker (`qwen3.5:2b`)**: Lightning-fast (<15s) micro-contracts, data schemas, physics loops, and atomic functions.
- **Deep Brain & Tool Specialist (`qwen3.5:4b`)**: Complex state machines and pointer data structures; the checked-in 10-task tool benchmark reports **9/10 (90%)** accuracy.
- **Supreme Hivemind & Inspector (`TypeSafe Jev System One`)**: Calibrated architectural decisions (`Choice`), interface extraction, pre-flight tool routing, maintainability scoring (`Score`), and specification gating (`Noul`).

---

## 🏛 Architecture & 3-Tier Verification

```mermaid
flowchart TD
    UserGoal([User Goal / Engineering Task]) --> JevChoice[Stage 1: Jev Upfront Architecture Selection<br/>Choice Primitive]
    JevChoice --> Decomposer[Stage 2: Micro-Contract Blueprinting<br/>Pure Interface Contract Extraction]
    
    subgraph SwarmExecution [Stage 3: Local SLM Swarm Execution]
        Decomposer -->|Agile Tier: Schemas / Physics / Math| Worker2B[Qwen 3.5 2B Agile Worker<br/>No-Think Mode: <15s]
        Decomposer -->|Deep Tier: Algorithms / Pointer Structures| Worker4B[Qwen 3.5 4B Deep Brain<br/>32k Context: 100% Accurate]
        Decomposer -->|Tool Execution: Bash / Edit / Grep| ToolRunner[Qwen 3.5 4B Tool Specialist<br/>Zero Distractor Confusion]
    end
    
    Worker2B & Worker4B --> Tier1[Stage 4: Tier 1 Zero-Knowledge Runtime Check<br/>Headless AST Compilation: ast.parse / vm.Script]
    
    Tier1 -- Syntax Error --> CompilerLoop[Compiler-in-the-Loop Local AST Patching<br/>Targeted line repair: 100% Recovery]
    CompilerLoop --> Tier1
    
    Tier1 -- Valid AST --> Tier2[Tier 2: Jev System One Contract Gates<br/>Noul: Reference Integrity & Spec Compliance P >= 0.70]
    Tier2 -- Gate Failed --> Decomposer
    
    Tier2 -- Passed Gate --> Tier3[Tier 3: Continuous Quality Score & Arena Promotion<br/>Score [0.0 - 3.0] & Multi-Candidate Promotion]
    Tier3 --> Assembly([Stage 5: Final Zero-Collision Assembly & Verification])
```

---

## 🎮 Playable Game Arcade (Community Showcase)

Every game in this arcade was synthesized locally by SLMs governed by Jev System One. Open [`benchmarks/index.html`](benchmarks/index.html) in your browser to launch the full interactive showcase dashboard:

| Playable Artifact | Worker Model | Assembly Time | Jev Gate Overhead | Quality Score | Live Playable Link |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Retro Space Invaders** | 4× Qwen 3.5 2B (Player, Fleet, Bullets, Canvas) | 67.4s (~28 tok/s) | 2,799 ms (4 checks) | **2.62 / 3.0** | [Play Game](benchmarks/space_invaders/space_invaders_playable.html) |
| **Flappy Pig Deluxe** | Qwen 3.5 2B (Arcade physics + Web Audio API) | 27.2s | 1,548 ms (2 checks) | **2.75 / 3.0** | [Play Game](benchmarks/run_2_typesafe_jev/index.html) |
| **3D Interactive Arena** | Three.js Procedural Physics & Lighting Simulation | Instant Boot | Architectural Spec Gate | **2.80 / 3.0** | [Launch Arena](benchmarks/3d_ball_simulation/index.html) |
| **6-Team Swarm Hackathon** | 6 Autonomous SLM Teams in Parallel | 4,200 tokens | Jev Multi-Audit Evaluation | **2.68 / 3.0** | [View Leaderboard](benchmarks/hackathon_swarm/leaderboard.html) |

---

## 📊 Empirical Benchmarks

All benchmarks were conducted on **Apple Silicon (M-Series, 16GB Unified RAM, macOS Darwin)** running Ollama locally:

### 1. Multi-Agent Concurrency Stress Test (1 to 24 Parallel Workers)

| Local Model | Concurrent Agents | Wall-Clock Time | Success Rate | Generation Throughput | Unified RAM Usage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `huihui-qwen3.5:0.8b` | 1 agent | 2.29s | 1/1 (HTTP success) | 52.3 tok/s | 2,851 MB |
| `huihui-qwen3.5:0.8b` | 8 agents | 16.56s | 8/8 (HTTP success) | 57.9 tok/s | 2,950 MB |
| **`huihui-qwen3.5:0.8b`** | **24 agents** | **56.06s** | **24/24 (HTTP success)** | **51.4 tok/s** | **2,815 MB** |
| `huihui-qwen3.5:2b` | 1 agent | 3.87s | 1/1 (HTTP success) | 31.0 tok/s | 2,790 MB |
| `huihui-qwen3.5:2b` | 8 agents | 32.90s | 8/8 (HTTP success) | 29.2 tok/s | 2,710 MB |
| **`huihui-qwen3.5:2b`** | **24 agents** | **89.78s** | **24/24 (HTTP success)** | **32.1 tok/s** | **2,755 MB** |

> **Key Takeaway:** Unified Memory on Apple Silicon maintains rock-solid stability (~2.8GB–3.8GB) even under bursts of 24 parallel inference threads. Throughput remains pegged at full hardware speed without thermal throttling.

### 2. Tool-Calling Benchmark: Qwen 3.5 4B vs. Llama 3 Groq 8B

Evaluated across 10 diverse scenarios covering single calls, multiple arguments, distractor selection, negative abstention, parallel calls, and multi-turn state:

| Benchmark Metric | `ollama/qwen3.5:4b` (Our Deep Brain) | `llama3-groq-tool-use:8b` (Baseline) |
| :--- | :--- | :--- |
| **Overall Accuracy** | **9 / 10 (90%)** | 9 / 10 (90%) |
| **Distractor Avoidance** | **100% Pass** (Selected exact tool) | ❌ **Frozen** (0 tool calls generated) |
| **Context Window** | **32,768 tokens (32k)** | 8,192 tokens (8k) |
| **Disk & VRAM Footprint** | **3.4 GB** (Lean & fast) | 4.7 GB |
| **No-Think Mode Speed** | **3.8s average latency** (90% accuracy) | N/A (Frozen without system prompt) |

### 3. The "Thinking Mode" Anti-Pattern & Fast Proxy Acceleration

- Small models (0.8B–4B) spend 600–1,200 tokens deliberating inside `<think>`, adding 20–70s latency per worker and risking output truncation.
- Enforcing **No-Think mode** (`think: False` or `reasoning_effort: "none"`) yields **68% token reduction**, **65% latency reduction**, and eliminates empty-thought halts.
- Our **Ollama Fast Proxy** (`scripts/ollama_fast_proxy.py`) transparently enforces `reasoning_effort: "none"` and optimal 32k context on port `11435`, dropping turn latency from **56s down to 0.3s**.

### Reproducible evaluation

Published figures are research artifacts, not product guarantees. Score generated candidates against the fixed corpus with a model digest and seed; runtime tests run only in a network-disabled Docker sandbox:

The evidence classification, contradictions in historical artifacts, and the
next controlled evaluation program are maintained in
[`references/jev_research_synthesis.md`](references/jev_research_synthesis.md).
The first WSL/Galene paired study is recorded, with its limitations, in
[`references/wsl_galene_paired_study_2026-09-21.md`](references/wsl_galene_paired_study_2026-09-21.md).
The Windows-native Intel GPU path, including its required GPU-offload proof,
is documented in
[`references/windows_native_gpu_inference_2026-09-21.md`](references/windows_native_gpu_inference_2026-09-21.md).

```bash
docker run --rm -v "$PWD:/workspace" -w /workspace python:3.11-alpine \
  python scripts/evaluate_corpus.py --candidates /workspace/candidates \
  --model "qwen3.5:4b@sha256:..." --seed 42
```

Syntax validation is not a runtime pass. Unsupported runtime languages fail closed until a corresponding sandbox adapter is implemented.

### Paired direct vs Jev experiment

`benchmarks/docker-compose.paired.yml` runs the P0 paired experiment against the
Windows-hosted Ollama worker. The nine-task corpus covers development and holdout
micro-contracts, scope creep, prompt-injection inputs, multi-file integration, and
a real browser interaction. The runner defaults to 20 seeds per task. Both arms use
the same exact model digest, temperature, think setting, and seed; the guided arm
adds only Jev's implementation-shape Choice. Generation is uncapped. The runner
warms the model before measurement, alternates arm order by seed, evaluates hidden
oracle tests in network-disabled Docker sandboxes, and reports paired pass deltas
with bootstrap confidence intervals, latency percentiles, token counts, timeouts,
and truncations. Redacted records and raw candidates are written to the ignored
`benchmark-runs/` directory. The runner mounts the Docker socket only to execute
isolated candidates; run it only on a trusted development host.

The per-request timeout is a wall-clock hang guard (queue wait plus full uncapped
generation), never a content budget, and the standalone CLI default matches it
(2400 s). Runs below 20 paired seeds per task are refused unless explicitly
labeled directional evidence with `--allow-directional`. The nine-task corpus —
including its hidden test suites, prompt-injection probe, multi-file integration
tasks, browser holdout tasks, and Jev's `implementation_shape` Choice contract —
is frozen as of 2026-09-23; changing any task or criterion starts a new corpus
version that must be re-baselined. Candidates that pass the oracle sandboxes are
Runtime-valid-tier evidence only: before any promotion claim, surviving
candidates also pass the demo's canonical three-question Jev gate, and those two
tiers of labels are never mixed.

```bash
JEV_BENCHMARK_MODEL="qwen3.5:4b" JEV_BENCHMARK_SEED=1 JEV_BENCHMARK_SEED_COUNT=20 \
JEV_GIT_REVISION="$(git rev-parse HEAD)" \
JEV_SANDBOX_HOST_DIR="$PWD/benchmark-runs/.sandbox" \
JEV_BROWSER_SANDBOX_IMAGE="jev-skill-browser-sandbox:1.63.0" \
  docker compose -f benchmarks/docker-compose.paired.yml --profile benchmark-build build browser-sandbox paired-benchmark
```

Then start the 20-seed paired run:

```bash
JEV_BENCHMARK_MODEL="qwen3.5:4b" JEV_BENCHMARK_SEED=1 JEV_BENCHMARK_SEED_COUNT=20 \
JEV_GIT_REVISION="$(git rev-parse HEAD)" \
JEV_SANDBOX_HOST_DIR="$PWD/benchmark-runs/.sandbox" \
  docker compose -f benchmarks/docker-compose.paired.yml run --rm paired-benchmark
```

The runner resolves and records Ollama's immutable model digest. Requested seeds
are paired across arms even if Ollama does not echo the seed in its response; the
report keeps both the requested seed and whether the provider echoed it. A single
20-seed run is still limited to this task corpus and does not establish general
swarm superiority. Each completed arm is checkpointed to NDJSON. If the runner
container is interrupted, resume the same configuration without repeating saved
arms by adding `--resume-ledger benchmark-runs/<run-id>.ndjson` to the `run` command;
the runner rejects a changed model digest, source, manifest, seed range, or settings.

### WSL local SLM baseline

For the same small model family used by the Mac research, run Ollama in the
isolated Docker volume and pull the exact worker model once:

```bash
docker compose -f benchmarks/docker-compose.local-ollama.yml up -d
docker exec jev-local-ollama ollama pull qwen3.5:2b
```

On the verified WSL CPU-only host, `qwen3.5:2b` generated a 13-token no-think
Python response successfully, but at approximately 0.25 tokens/second. Keep
local theory tests short and record cold-load versus warm-model latency
separately. The paired runner uses WSL host networking to contact this local
endpoint; its candidate tests remain network-disabled Docker sandboxes.

For this Windows host, use the native Vulkan path instead of that CPU-only
container when GPU throughput is required. It is a distinct runtime and must
prove GPU offload in its server log before its results are treated as a GPU
baseline.

### Live Jev vs. direct-Qwen demo

The demo starts two measured sessions and renders their generated artifacts side-by-side. Both lanes use the same Windows-native Ollama worker (`qwen3.5:4b`) through `host.docker.internal:11434`: the direct lane keeps worker thinking enabled, while the Jev lane selects a compact blueprint, disables worker thinking, and applies Noul/Score gates. The compose service mounts only the TypeSafe dotenv source read-only; it never stores credentials in this repository or substitutes a prebuilt game when generation or a Jev gate fails.

```bash
docker compose -f demo/docker-compose.yml up --build
```

Open `http://localhost:8088`, then select **Start two live sessions**.

---

## ⚡ 3-Minute Quickstart

### 1. Prerequisites
- **Python 3.9+** (The core CLI and Swarm engine have **zero external package dependencies**).
- **[Ollama](https://ollama.com/)** installed and running.
- **[TypeSafe AI API Key](https://console.typesafe.ai/keys)** (or store in macOS Keychain).

### 2. 1-Command Setup
```bash
git clone https://github.com/svitaTLCO/jev-skill.git
cd jev-skill

# Export your TypeSafe API key
export TYPESAFE_API_KEY="your_typesafe_key_here"

# Run setup (pulls/optimizes models, checks Fast Proxy, tests API connection)
./setup.sh
```

### 3. Start the Ollama Fast Proxy (Background Daemon)
To eliminate thinking latency and enforce 32k context across all agent interactions:
```bash
# Install as a persistent background daemon (macOS LaunchAgent)
python3 scripts/ollama_fast_proxy.py --install-daemon

# Check status
python3 scripts/ollama_fast_proxy.py --status
```

### 4. Evaluate Code with `jev_eval.py`
Zero-dependency CLI for evaluations, security reviews, interface extraction, and prompt gating:

```bash
# 1. Extract pure interface contract (prevents the Accumulated Code Prompt Trap)
python3 scripts/jev_eval.py --file src/server.py --mode interface

# 2. Upfront architectural pattern selection
python3 scripts/jev_eval.py --prompt "Compare FastAPI vs SQLite raw for telemetry" --mode choice

# 3. Micro-contract & reference integrity gating
python3 scripts/jev_eval.py --code "def compute_tax(subtotal): return subtotal * tax_rate" --prompt "Tax calculator" --mode contract

# 4. Code review & maintainability scoring [0.0 - 3.0]
python3 scripts/jev_eval.py --file src/engine.py --mode review

# 5. Pre-flight tool routing & negative abstention check
python3 scripts/jev_eval.py --prompt "Find calculate_hash in src/" --mode tool
```

### 5. Run a Swarm with the Python API
```python
from scripts.jev_swarm import JevSwarm

# Initialize swarm with TypeSafe Jev System One supervision
swarm = JevSwarm()

# 1. Select optimal architectural pattern upfront via Jev Choice
decision = swarm.evaluate_architecture_choice(
    prompt="Design a rate limiting mechanism",
    options=["TokenBucket (in-memory)", "LeakyBucket (in-memory)", "SlidingWindow (Redis)"]
)
print(f"Selected Pattern: {decision['selected_choice']}")

# 2. Execute a micro-contract under 3-Tier Verification
result = swarm.execute_micro_contract(
    task_id="rate_limiter",
    prompt="Write a Python class TokenBucket with allow_request(tokens). Output ONLY the class.",
    lang="python",
    tier="agile",  # "agile" routes to qwen3.5:2b, "deep" routes to qwen3.5:4b
    spec_requirement="Does TokenBucket properly refill tokens based on elapsed time without race conditions?",
    max_tokens=1200,
    min_noul=0.70,
    sample_candidates=2  # Runs Arena comparison if > 1 candidate requested
)

if result["passed"]:
    print(f"✅ Promoted Candidate Score: {result['quality_score']}/3.0")
    print(result["code"])

# 3. Extract pure interface contract to shield downstream workers
interface_contract = swarm.extract_interface_contract(result["code"], lang="python")
```

---

## 🤖 AI Coding Agent Integrations

This repository is designed as a drop-in skill and configuration package for modern agentic AI environments:

### OpenCode
Pre-configured with `opencode.json` and agent definitions in `.opencode/agents/`:
- **`local` Mode**: Powered by `qwen3.5:4b` Deep Brain with 32k context, scoped tool permissions, and zero empty-thought stalling.
- **Subagents**: `@agile` (`qwen3.5:2b`), `@deep` (`qwen3.5:4b`), `@tool-runner` (`qwen3.5:4b`), and `@jev-judge` (`opencode/jev-latest`).
- **`/swarm` Command**: Decomposes tasks into micro-contracts and runs the 5-stage empirical workflow autonomously.

```bash
# Launch OpenCode in local mode
opencode --agent local

# Run an autonomous micro-contract task
opencode run --agent local "Implement a generic LRU Cache in Python"
```

### Google Antigravity
The `typesafe-ai` skill is automatically discovered via `.agents/skills/typesafe-ai/SKILL.md`:
```bash
# Install globally across all Antigravity workspaces
mkdir -p ~/.gemini/config/skills
cp -r . ~/.gemini/config/skills/typesafe-ai
```

### Claude Code
```bash
claude plugin marketplace add typesafe-ai/skills
claude plugin install typesafe@typesafe-ai
```

---

## 📁 Repository Structure

```text
.
├── SKILL.md                          # Main agent skill definition (Antigravity / OpenCode)
├── AGENTS.md                         # Autonomous agent workspace & swarm guide
├── README.md                         # Project documentation & benchmark showcase
├── LICENSE                           # MIT License
├── CONTRIBUTING.md                   # Community contribution guidelines
├── setup.sh                          # 1-command verification & model setup
├── requirements.txt                  # Dependency notice (Zero required external dependencies)
├── .env.example                      # Environment variables template
├── opencode.json                     # OpenCode local provider & agent configuration
├── scripts/
│   ├── jev_eval.py                   # Zero-dependency evaluation CLI (11 modes)
│   ├── jev_swarm.py                  # Generic domain-agnostic swarm engine & Python API
│   ├── ollama_fast_proxy.py          # Port 11435 transparent fast proxy & daemon manager
│   ├── test_connection.py            # Latency & API connectivity tester
│   ├── utils.py                      # Shared API key & platform utilities
│   ├── game_runtime_validator.py     # Headless DOM & syntax validator for games
│   ├── hackathon_swarm_engine.py     # Multi-team parallel competition engine
│   └── modelfiles/
│       ├── Modelfile.qwen3.5-4b      # Qwen 3.5 4B optimized for 32k context
│       └── Modelfile.qwen3.5-2b      # Qwen 3.5 2B optimized for 32k context
├── benchmarks/                       # Empirical benchmarks & playable arcade
│   ├── index.html                    # Interactive Community Showcase Dashboard
│   ├── tool_calling_results.json     # 10/10 BFCL tool calling benchmark data
│   ├── swarm_capacity_benchmark.json # Concurrency stress test data (1-24 agents)
│   ├── experiments/                  # Reproducible empirical research scripts
│   │   ├── test_tool_calling_qwen_vs_llama.py
│   │   ├── test_couple_2b_4b.py
│   │   ├── test_no_think_resilience.py
│   │   ├── test_optimal_vs_old_architecture.py
│   │   └── test_upgraded_harness.py
│   ├── space_invaders/               # Playable Retro Space Invaders
│   ├── run_2_typesafe_jev/           # Playable Flappy Pig Deluxe
│   ├── 3d_ball_simulation/          # Three.js 3D Procedural Simulation
│   └── hackathon_swarm/              # 6-Team autonomous hackathon outputs
└── references/
    ├── theoretical_limits_report.md  # Deep research on SLM failure modes & mathematical limits
    ├── swarm_orchestration_guide.md  # Micro-contract design patterns & prompt engineering
    ├── evaluation_rubrics.md         # Calibrated scoring rubrics for Jev Score
    ├── api_reference.md              # TypeSafe System One HTTP API schema
    └── primitives_guide.md           # Choice, Score, and Noul engineering guide
```

---

## 📜 License

This project is open-source software licensed under the [MIT License](LICENSE).

Developed by Sandro Vita and Open Source Contributors. Powered by [TypeSafe AI](https://typesafe.ai).
