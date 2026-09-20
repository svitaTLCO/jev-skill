# Contributing to TypeSafe AI (Jev) & Local SLM Swarm

Thank you for your interest in contributing to the **TypeSafe AI (Jev) & Local SLM Swarm** project!

We welcome contributions from researchers, agentic AI developers, and open-source practitioners.

---

## Areas We Are Actively Exploring

1. **New SLM Adapters**: Testing sub-3B parameter models (e.g. SmolLM2, Llama 3.2 1B/3B, Gemma 2 2B) within the Jev Hivemind loop.
2. **Empirical Benchmarks**: Adding domain-specific micro-contract tasks (e.g., SQL generation, Rust memory boundaries, regex security, WebAssembly).
3. **Compiler-in-the-Loop Expanders**: Integrating additional language checkers (e.g., `cargo check`, `tsc --noEmit`, `mypy`).
4. **Agent Tooling**: Expanding skills and commands for OpenCode, Antigravity, Claude Code, and Cursor.

---

## Development Setup

### 1. Requirements
- Python 3.9+ (The core CLI and swarm engine require **zero** third-party Python dependencies).
- [Ollama](https://ollama.com/) running locally.
- TypeSafe AI API Key ([docs.typesafe.ai](https://docs.typesafe.ai)).

### 2. Setting Up Local Models
```bash
# Clone the repository
git clone https://github.com/your-username/jev-skill.git
cd jev-skill

# Run setup script to verify environment
./setup.sh
```

### 3. Running Verification
Always ensure tests and evaluations pass before submitting a pull request:
```bash
# Verify API connection
python3 scripts/test_connection.py

# Verify syntax across all modules
python3 -m py_compile scripts/*.py benchmarks/*.py
```

---

## Code Style & Invariants

- **Domain-Agnostic Invariant**: Swarm orchestration primitives and Jev gates must apply equally well to systems programming, data engineering, and frontend web applications.
- **Micro-Contract Scoping**: Prompts for small language models must remain narrow (<20 lines of output) with explicit interface declarations.
- **Zero Third-Party Core**: Keep `jev_eval.py` and `jev_swarm.py` purely dependent on Python standard library modules (`urllib`, `json`, `ast`, `subprocess`) so agents can install and run anywhere instantaneously.
