# WSL Local SLM Verification — 2026-09-21

## Outcome

This WSL host can run the Mac-research worker model locally without a Windows
Ollama installation.

- Runtime: `ollama/ollama` Docker container, bound only to `127.0.0.1:11434`
- Model: `qwen3.5:2b` (`324d162be6ca`, 2.7 GB in the named
  `jev-local-ollama` volume)
- Compute: CPU only; Ollama detected 50.9 GiB available RAM and no VRAM
- Smoke task: no-think `def add(a, b): return a + b`
- Result: valid Python response, 13 generated tokens
- Warm generation duration: 47.5 seconds (about 0.25 tokens/second)

The smoke request used the Ollama API field `think: false`. An interactive CLI
request and a literal `/no_think` prompt both emitted visible reasoning first;
they are not valid substitutes for the API control in experiments.

## Research consequence

The local baseline is available, but CPU throughput makes a large exhaustive
matrix expensive. Run short, independently targeted theory tests with fixed
token caps, separate cold-load and warm timings, and objective Docker-sandbox
oracles. Do not compare its raw latency directly with the remote Galene model.
