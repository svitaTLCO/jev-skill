# WSL Galene Paired Study — 2026-09-21

**Runner revision:** `3292490`  
**Host:** Windows/WSL2, Docker-based runner and nested network-disabled Python
sandbox  
**Worker:** Galene OpenAI-compatible `Galene/LLM`, no-think, temperature 0.2,
maximum 1,200 output tokens  
**Arms:** direct generation; Jev Choice-guided generation  
**Corpus:** two Python micro-contracts (`sum_positive_integers` development,
`clamp_value` holdout)  
**Requested seeds:** 1–20

## Result

Twenty committed-run ledgers yielded 80 arm/task records.

| Metric | Direct | Jev-guided |
| --- | ---: | ---: |
| Requested executions | 40 | 40 |
| Completed executions | 38 | 36 |
| Objective sandbox passes | 38 | 35 |
| No-completion infrastructure errors | 2 | 4 |
| Completed-run generation median | 12.03 s | 11.20 s |
| Completed-run end-to-end median | 12.03 s | 12.06 s |
| Mean output tokens (completed) | 533.5 | 526.1 |

There were 34 matched pairs where both arms completed.  Across those pairs,
direct median generation latency was **11.18 s** and Jev-guided median
end-to-end latency was **10.67 s**.  The median Jev Choice call itself was
**0.81 s**.  Guided was faster in 19/34 matched pairs.

## Interpretation

This is **not evidence that Jev improves latency or reliability**:

- Galene did not return/confirm the requested seed for any record.  The 20
  requests are repeated samples, not a reproducible paired-seed experiment.
- The guided arm had more no-content failures (4 versus 2), all on
  `sum_positive_integers`.  A generated answer with no completion content is
  an infrastructure failure, not a failed task or a successful abstention.
- One guided `clamp_value` candidate reached the sandbox but timed out.  It is
  correctly a failed objective evaluation.
- The corpus contains only two very small Python tasks.  It cannot support
  claims about architecture, multi-file assembly, browser applications, repair,
  or general coding quality.
- The latency figures are descriptive only.  A valid comparison needs a
  seed-capable provider or independently verifiable request IDs and repeated
  randomized trials, plus confidence intervals.

The raw redacted run ledgers and candidate artifacts are deliberately ignored
under `benchmark-runs/`; this document records the aggregate, reproducible
method and limits without committing generated source or credentials.

## Actionable result

The immediate instrumentation gap is response observability.  The runner must
preserve non-secret completion metadata (for example finish reason, refusal,
reasoning-token usage, and provider request ID) when content is missing.  Only
then can no-content outcomes be separated into provider truncation, reasoning
exhaustion, content filtering, transport failure, or runner parsing failure.

Before another model comparison, extend the corpus with hidden integration and
browser oracles and select a provider/API that confirms deterministic seeds.

