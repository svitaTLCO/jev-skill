# Windows-GPU Ollama race evidence — 2026-09-22

Live-demo race evidence recorded against the Windows-native Ollama worker
(`qwen3.5:4b` Q4_K_M, Vulkan / Intel Iris Xe iGPU) after the host-shutdown
recovery of 2026-09-22. This is the continuation of the decision recorded in
[windows_native_gpu_inference_2026-09-21.md](windows_native_gpu_inference_2026-09-21.md).

## Purpose

Answer the instrumentation question that blocked the recovered task: were the
direct-lane failures on this worker **cap-bound** (token budget too small for
the thinking channel) or a genuine **model incompleteness**? Then capture the
first Windows-GPU data point toward the research question: *does Jev's
advantage come out only on small local models?*

## Topology

- Windows-native Ollama **v0.34.2**, bound to **loopback `127.0.0.1:11434`
  only** (no LAN exposure; accepted as mandated by the 2026-09-21 decision).
- WSL cannot reach Windows loopback directly (NAT mode; gateway address times
  out). All worker calls therefore go from the demo Docker container through
  `http://host.docker.internal:11434`, the path proven working on 2026-09-21.
- Demo server: `demo/docker-compose.yml` (Python 3.11 alpine, port `8088`).
  The two lanes share one inference slot (`OLLAMA_NUM_PARALLEL=1`) and
  serialize through Ollama's queue.

## GPU offload acceptance

Per the 2026-09-21 acceptance check, the Ollama server console log (supplied
by the operator on 2026-09-22; user profile paths redacted here) showed:

- device discovered as **`Vulkan0`**, Intel Iris Xe;
- `qwen3.5:4b` loaded with **34/34 layers offloaded** to the GPU;
- environment flag **`OLLAMA_VULKAN=true`**;
- **no CPU fallback** observed during the load.

Acceptance: **PASSED**. The performance experiments below compare against a
genuinely GPU-backed worker.

## Measured throughput (qwen3.5:4b, iGPU shared memory)

| Observation | Value | Source |
| --- | --- | --- |
| Model load (warm restart) | 15.2 s | decisive probe |
| Cold load (first use) | 21.4 s | 2026-09-21 smoke |
| Prompt evaluation | 12.17 tok/s | 2026-09-21 smoke |
| Generation (short tasks, `tg_3s`) | 3.2–7.3 tok/s | 2026-09-21 smoke |
| Generation, think-on broad game task | 3.44 tok/s sustained | decisive probe |
| Projected memory footprint | ~3.8 GB | 2026-09-21 estimate |

The decisive probe replayed the exact direct-lane request (broad
`GAME_REQUIREMENT`, `think: true`, `temperature: 0.2`, `num_predict: 8192`):

```text
wall_s=1239.5  done_reason=stop  eval_count=4202  prompt_eval_count=69
load_s=15.2    eval_tps=3.44     chars=10882      doctype=True  close_html=True
```

Classification: **not cap-bound at 8192.** With thinking enabled the model
consumes ~4.2k tokens end-to-end (reasoning channel included) and still stops
with a complete `<!doctype html>…</html>` document. The previous 4096 budget
was simply below that requirement and truncated mid-document. Consequence: the
default `num_predict` in `scripts/demo_server.py` was raised from 4096 to
**8192** (2× headroom over the measured requirement) and verified in the
rebuilt container image.

## Instrumentation history (races #1–#2)

These runs are recorded as **instrumentation history**, not model results:
each failure had a diagnosable tooling cause that was fixed before any
conclusion about the model.

### Race #1 `bb5ba652d8454cb78a27d6443f7ee355` — both lanes failed (tooling bugs)

- Direct failed @397.24 s: default `num_predict=1800` truncated the document
  mid-way while the thinking channel consumed the budget.
- Guided failed @421.09 s with a client timeout: the 420 s client deadline
  did not cover queue wait behind the slow direct lane (single inference
  slot), so the guided lane never even started generating.

Fix (patch v1): `num_predict` 1800 → 4096, client deadline 420 s → 2400 s
(must cover queue wait plus full generation on a ~5 tok/s worker).

### Race #2 `b67dfd59a2554732af17bf45dd343f3c` — cap bound + first gate evidence

- Direct still incomplete @1167.37 s at the 4096 cap: truncation-by-cap
  confirmed on the broad think-on task (motivated the decisive probe).
- Guided gate-rejected @1451.51 s: `contract=0.07, scope=0.89,
  quality=0.46` (`jev_seconds=0.77`). Legitimate governance behavior, not a
  bug.

Fix (patch v2): run-ledger observability — truncated and gate-rejected raw
outputs are now persisted to `demo/runs/<id>/<lane>.raw.txt` (gitignored),
and extraction errors report char/eval counts.

## Final race #3 `a3d4d70854984c28b63312a6a97cb0c1`

Run 2026-09-22, approximately 15:03–15:31 local time, against the rebuilt
image carrying the 8192 budget.

| Lane | Outcome | Evidence |
| --- | --- | --- |
| Direct | **READY** | 4525 tokens, 1717.93 s (~2.6 tok/s including load + queue); artifact `demo/runs/<id>/direct.html` (11,420 B), complete START/PLAYING/GAMEOVER state machine, gravity, pipes, scoring, collision, restart, Space/click/touch input. |
| Guided | **FAILED (by design)** | Jev Choice selected a blueprint, then the constrained ≤900-token no-think generation was rejected by the Jev gate: `contract=0.04, scope=0.84, quality=0.48` (`jev_seconds=0.83`, lane elapsed 329.56 s). Candidate (3,328 chars) preserved in the run ledger. |

### Promotion labels (per the evidence policy in `jev_research_synthesis.md`)

Labels are applied separately and never mixed:

- Direct artifact: **Generated · Syntax-valid** — the extracted `<script>`
  block passes `node --check` (Node 24.14.0). Runtime validity is **not**
  claimed; browser/human playtest pending.
- Guided candidate: **Gate-rejected · Syntax-invalid (parser-confirmed)** —
  `node --check` reports `SyntaxError: Unexpected identifier 'e'`: the
  candidate declares `function e(…)` and later re-declares the same lexical
  name in `let …, e=0, …`; a second defect (double `else` in `draw()`) is
  visible on inspection. The script can never be parsed, so the page renders
  blank. The Noul gate's near-zero contract score is objectively justified.

## Findings toward the research question

1. **Jev's measurable advantage on this 4B local worker appears as gating,
   not generative rescue.** Two independent attempts produced candidates that
   pass the structural HTML extraction but are syntactically unexecutable;
   the Noul gate rejected both with a stable signature (contract 0.07 →
   0.04, scope 0.89 → 0.84, quality 0.46 → 0.48). A purely structural check
   alone would have let such a candidate through as "complete".
2. **Choice-driven planning did not rescue the compressed arm here.** The
   constrained ≤900-token no-think generation produced non-runnable code on
   2/2 attempts, while the unconstrained think-on direct arm produced a
   complete, syntax-valid document. This is consistent with the empirical
   invariants already recorded (compressed contracts stress SLMs; multi-
   candidate arena filtering raises reliability — AGENTS.md §4).
3. **Latency versus detection.** The guided lane was faster (329.6 s vs
   1717.9 s) because its output is much smaller; the direct lane won on
   completeness and syntax. Compared with the macOS baselines (guided 20.00 s
   vs direct 18.39 s wall; Noul 0.01) and the WSL/Galene paired study
   (latency-neutral, inconclusive), the Windows-iGPU data point suggests that
   on slow small local workers Jev's advantage shifts from **latency to
   defect-detection rate**.
4. **Honest negative result, single-shot semantics.** Under today's demo
   semantics (one guided attempt per run), the first-attempt pass rate of the
   guided lane on this worker is 0/2. This is recorded as-is; changing the
   semantics (bounded regeneration / arena promotion) is a deliberate design
   change and is deferred to a dedicated experiment so that future arm
   configurations remain comparable across the P0 program.

## Boundaries and non-goals

- No playability or "works in a browser" claim is made for either artifact;
  runtime verification requires a human/browser pass.
- Raw ledgers remain outside version control (`demo/runs/` is gitignored);
  only the analysis is committed.
- Loopback-only binding of port 11434 was maintained throughout; nothing was
  exposed to the LAN.
- One unrelated scaffold (`codex-galene-swarm/`, created 2026-09-22) exists
  in the tree and is intentionally excluded from this evidence set.

## Next steps

- **P0 paired multi-seed benchmark** on this same topology: ≥20 matched
  seeds per task, identical arm configuration, bootstrap CIs (per
  `jev_research_synthesis.md`).
- **Design decision before P0:** bounded regeneration / arena promotion for
  the guided lane on gate rejection (AGENTS.md invariant #5) — must be fixed
  before P0 so arms stay identical across tasks and hosts.
