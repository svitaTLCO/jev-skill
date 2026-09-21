# Jev + SLM Research Synthesis

**Status:** evidence map and next-experiment protocol, 2026-09-21.

## Executive conclusion

The research supports a promising *governed micro-contract* architecture, but
does not yet demonstrate a reliable autonomous end-to-end coding swarm.  The
most defensible current claim is narrower:

> On the tested small local models, concise, bounded contracts and no-think
> generation reduce a known truncation and scope-creep failure mode.  Jev is a
> useful source of structured decisions and candidate signals.  A candidate is
> promotable only after independent, task-specific execution tests.

The next gain is not another orchestration feature.  It is a controlled,
budget-matched evaluation that attributes any improvement separately to:
interface compression, no-think inference, Jev Choice, Jev gates, repair, and
candidate selection.

## Evidence ledger

### Demonstrated in the checked-in artifacts

| Finding | Evidence | Confidence and limit |
| --- | --- | --- |
| Raw accumulated implementation context caused later evolutionary stages to truncate at the 700-token ceiling, while the isolated first stage compiled in 5/8 cases. | `theoretical_limits_report.md` 227-242 | High for that task/model/budget; it does not prove the proposed interface-only fix. |
| Broad multi-worker assembly failed zero-touch in three reported experiments. | `theoretical_limits_report.md` 28-41, 64-76, 101-118 | High; the resulting playable artifacts may include manual reconstruction. |
| The recorded self-healing run did not heal either of its two cases. | `exp4_self_healing_results.json` 1-43 | High; contradicts a general 100% repair claim. |
| The current runtime validator fails closed for unsupported languages and runs supplied Python tests in a constrained Docker container. | `scripts/jev_swarm.py` 143-245 | High for Python only; HTML/browser and other language runtime adapters are absent. |
| The fixed corpus records model, seed, manifest and candidate hashes. | `scripts/evaluate_corpus.py` 17-51 | High; it evaluates supplied files, not a full generation run. |

### Plausible hypotheses, not yet established

| Hypothesis | Why it is plausible | What would establish it |
| --- | --- | --- |
| Interface-only handoffs improve multi-stage completion. | The raw-code stages failed under a constrained token budget. | Paired multi-seed comparison with identical task, model and budget. |
| No-think improves quality-adjusted latency for small models. | The reports identify reasoning-token exhaustion, and the demo required no-think to obtain an HTML answer. | Per-model, task-stratified comparison of think/no-think with output budgets and runtime tests held constant. |
| Jev Choice improves architecture selection. | It provides a compact structured decision before generation. | Compare against a fixed predeclared architecture and a no-Jev condition. |
| Noul/Score gates improve promoted-candidate quality. | They can filter candidates before assembly. | Blind calibration against hidden objective tests, including false accepts and false rejects. |
| Localized repair is better than full regeneration. | The failure mechanism is consistent with a smaller output request. | Frozen defect corpus, equal budgets, exact patch protocol and semantic regression tests. |
| Candidate arenas improve final quality. | Stochastic candidates vary. | Compare pass@1, pass@2 and pass@3, with objective and Jev selectors independently ablated. |

### Claims that must not be used as conclusions

- “100% localized AST recovery” is not supported by the checked-in repair
  result: both recorded candidates remain invalid.  The harness also asks for a
  complete regenerated file rather than an exact local diff
  (`exp4_self_healing_swarm.py` 153-170).
- “24 agents at 100% success” means an HTTP response decoded as JSON.  The
  stress test does not parse or execute the generated answer
  (`swarm_concurrency_stress_test.py` 48-84); it is availability data, not task
  correctness or a safe concurrency limit.
- A direct-versus-Jev Flappy result cannot establish a speed win: the checked-in
  guided lane took 20.00s versus 18.39s for direct generation, generated the
  same 850 tokens, and received Noul 0.01 / quality 0.0
  (`local_flappy/benchmark_results.json` 5-45).
- `run_benchmark.py` is not a direct-generation baseline: it sleeps for 0.5s
  and reads an already-existing Jev artifact (`run_benchmark.py` 71-89,
  145-150).  It must be retained only as a historical demonstration.
- Syntax success, Jev score, HTTP success, and a manually repaired playable
  artifact are distinct outcome classes.  They must never be averaged or
  reported as the same success metric.

## Condensed operating model

```text
Task specification
  -> deterministic task manifest (exports, invariants, evaluator)
  -> Jev Choice only where real alternatives exist
  -> small worker receives contract, interfaces, and negative constraints
  -> candidate artifact
  -> hard gate: parser + isolated runtime/oracle tests
  -> soft gate: calibrated Jev Noul/Score, used for ranking or abstention
  -> deterministic assembly with namespace and dependency checks
  -> integration/browser tests
  -> immutable run record and promotion decision
```

The key design rule is that Jev is **governance and information compression**,
not an oracle for executable correctness.  Objective evaluators are hard
promotion gates; Jev answers are inputs to routing, prioritisation, and
investigation until calibration demonstrates otherwise.

## Architecture changes with the highest expected value

1. **Make the task manifest the boundary.** Define required exports, allowed
   dependencies, state ownership, negative constraints, unit/integration tests,
   and a fixed token budget before calling a worker.  Pass prior interfaces, not
   prior source.  Replace blind concatenation with an AST/module-aware assembler
   that rejects duplicate globals and missing exports.
2. **Make every promotion objective.** Keep the current Docker Python adapter;
   add a browser sandbox for HTML/JS and adapters for each supported runtime.
   A Jev score must never override a failed evaluator.
3. **Record a complete run ledger.** For every candidate store task/split ID,
   specification hash, worker model digest, provider, decoding settings,
   requested/effective seed, token and latency measures, candidate hash, Jev
   questions/answers, evaluator version, test logs, repair diff, and promotion
   reason.  Store raw output outside version control and never record secrets.
4. **Treat repair as a patch transaction.** The repair prompt must request an
   exact unified diff limited to the diagnostic region; apply it mechanically,
   run the original tests plus regression tests, and reject changes outside the
   allowed files/lines.  Full regeneration is a distinct fallback arm, not
   “self-healing.”
5. **Separate selection from generation.** Generate candidates independently;
   select first by objective validity, then use calibrated Jev signals only to
   order equally valid candidates.  Report pass@k separately from selected
   quality.

## Minimum viable evidence program

### P0 — paired end-to-end benchmark (first priority)

Run at least 20 paired seeds per task across a development/holdout corpus.
Every arm must use the identical model digest, provider, prompt intent,
decoding configuration, token budget, cache state policy and evaluator.  The
direct arm must actually invoke the model; the guided arm adds only the named
Jev stages.

Report, per task and aggregate:

- pass@1 and pass@k from parser, sandbox and integration/browser tests;
- end-to-end p50/p95 latency, worker/Jev latency, output/input tokens and cost;
- retries, timeouts, truncations, repair rate and assembly failures;
- paired deltas with bootstrap confidence intervals;
- all failures classified as generation, gate, assembly, repair, or evaluator.

The corpus needs more than the current two Python micro-tasks (one holdout)
in `evaluation_manifest.json` 1-20.  Add multi-file, browser, integration,
scope-creep and prompt-injection cases, and keep the final oracle checks hidden
from generation prompts.

### P1 — causal ablation matrix

Start with a small factorial design, holding everything else fixed:

| Factor | Off | On |
| --- | --- | --- |
| Context handoff | accumulated source | manifest plus interfaces |
| Worker reasoning | think | no-think |
| Architecture | fixed deterministic option | Jev Choice |
| Promotion | objective tests only | objective tests plus calibrated Jev ranking |
| Repair | none/full regeneration | constrained local diff |
| Sampling | one candidate | two or three candidates |

Do not combine all factors in the first run.  Begin with handoff and no-think,
then add Jev Choice and gates.  This is the shortest route to discovering
whether Jev contributes beyond prompt compression and decoding settings.

### P2 — calibrate Jev gates

Build a blinded set of valid and invalid candidates, labelled only by hidden
objective evaluators.  For each Noul threshold and task/model stratum, measure
false-accept rate, false-reject rate, precision/recall, reliability curve and
Brier score.  The current `0.70` threshold is a configuration value in
`jev_swarm.py` 321-339, not an empirically calibrated operating point.

### P3 — repair and scaling studies

Use a frozen, naturally occurring defect corpus plus separately labelled
synthetic defects.  Compare exact local patch versus full regeneration at equal
budgets; record changed lines and semantic regression.  For concurrency, add
semantic validation, queue p95/p99, timeout/retry rate, repeated bursts and
resource/thermal telemetry.  Preserve the existing HTTP stress test as a
transport-availability benchmark only.

## Promotion standard for future claims

Use these labels in the README, demo, and reports:

| Label | Required proof |
| --- | --- |
| **Generated** | Raw model response saved with model/config/run ID. |
| **Syntax-valid** | Parser/compiler result. |
| **Runtime-valid** | Isolated task-specific tests pass. |
| **Integrated** | Assembly and end-to-end/browser tests pass. |
| **Jev-ranked** | Jev output recorded; does not imply validity. |
| **Human-repaired** | Human change recorded separately; excluded from autonomous rate. |

Only “integrated” artifacts may be presented as autonomous end-to-end success.
All other artifacts are valuable research evidence, but must retain their
qualifier.

## Recommended next implementation slice

Implement the run ledger and a Docker-only benchmark runner before adding more
agents or prompts.  It should execute P0 on a small corpus with direct and
guided arms, persist redacted records, and produce a single comparison table.
That gives the project a trustworthy feedback loop for deciding whether to
invest in Jev gates, interface extraction, arenas, or repair next.

