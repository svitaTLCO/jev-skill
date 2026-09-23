# Architecture Exploration — Cap-Free Arms, Race #4 & Repair-Loop PoC (2026-09-22)

Companion study to `windows_gpu_ollama_race_2026-09-22.md` (race #3). This document
records Phase 2: re-interpreting the architecture menu under the user's standing
**cap-free directive** ("re-think removing any limit or soft/hard cap"), converting
the demo itself to cap-free operation, measuring arm B (Guided-v2), and running the
corrected offline repair-loop PoC.

## 1. Standing policy applied to all arms

- **No soft caps**: generation prompts contain no size language ("compact", "under N tokens" removed from experimental requirements; legacy `GUIDED_REQUIREMENT` kept verbatim as the recorded control arm).
- **No hard caps**: `num_predict` omitted from every Ollama payload (demo lanes included). The worker generates until its own stop token.
- **Hang guards only**: wall-clock client deadlines remain (2400 s demo, 3600 s PoC) and are documented as queue-wait + hang prevention, never as content budgets.
- **Iteration bounds** on repair loops (≤4 rounds) are declared separately as cost governance against the serialized inference slot, not content limits.

Harness delta vs race #3, recorded for comparability: removal of the 8192 ceiling was
non-binding for both recorded race #3 outcomes (direct stopped at 4525 tokens; guided
well below it), so legacy-arm controls remain valid.

## 2. Setup changes

- `scripts/demo_server.py`: cap-free `ollama_generate` (no `num_predict`); new
  `GUIDED_REQUIREMENT_V2` (de-compressed, no size language) + deterministic
  `INTERFACE_CONTRACTS` per chosen blueprint (AGENTS.md invariant #1: interface
  declarations downstream, not accumulated prose); new `guided_v2` lane
  (Choice → interface-contract handoff → uncapped no-think generation → same three-question
  Jev gate evaluated against the cap-free requirement); selective-lanes API
  (`POST /api/runs {"lanes": [...]}`, default remains `direct`+`guided`); tokens now
  recorded on failed lanes too (cost evidence survives extraction/gate failure).
- `demo/index.html`: third card with skipped-state rendering; poll loop generalized.
- `tests/test_demo_server.py`: 8/8 green — asserts payload contains **no** `num_predict`,
  V2 requirement carries no size language, lane-subset selection and rejection.
- Container rebuilt twice during this session; final image verified (HTTP 200, POST of an
  unknown lane → 400 without touching the worker).

## 3. Race #4 (run `5dd2d318`) — lanes `guided` vs `guided_v2`

Single-shot directional probe (not P0): legacy `guided` re-run in-session as a drift
control against the recorded race #3 candidate; `direct` intentionally not re-run
(race #3 measurement stands as the direct control). Both lanes shared the serialized
inference slot concurrently with the repair PoC, so wall-clock includes queue wait.

| Lane | Wall clock | Gate (contract/scope/quality) | Syntax (node --check) | Promotion label |
| :--- | ---: | :--- | :--- | :--- |
| `guided` (legacy, ≤900 soft-cap prompt kept as recorded identity) | 1167.8 s | 0.04 / 0.87 / 0.21 → rejected | **invalid** (garbled statements, e.g. `let pig=ctx.font="40px serif";let px=g.x;py=g.y;`) | Gate-rejected · Syntax-invalid |
| `guided_v2` (de-compressed cap-free, interface contract) | 642.2 s | 0.30 / 0.63 / 1.69 → rejected | **valid** (first parseable candidate ever produced by a guided lane on this worker) | Generated · Syntax-valid · Gate-rejected |

### 3.1 Forensics of the `guided_v2` candidate (7.7 KB HTML, ~7 KB JS)

Complete document: IIFE-scoped script, constants block (`GRAVITY`, `FLAP_STRENGTH`,
`PIPE_SPAWN_RATE`…), state enum `START|PLAYING|GAME_OVER`, pig object with
`draw/update/flap`, pipes manager (`spawnPipe/updatePipes/checkCollisions` AABB,
`updateScore`), requestAnimationFrame loop, Space/mousedown/touchstart handlers,
HUD text. Zero external references; no libraries, no assets.

Static review identified exactly the two gaps the gate's contract dimension scored down:

1. **No START→PLAYING transition.** `handleInput` calls `pig.flap()` in both START and
   GAME_OVER states; nothing ever assigns `currentState = gameState.PLAYING`. The
   playable state is unreachable — the game cannot start.
2. **Restart not wired.** `resetGame()` exists (score/pipes/position/state reset) but
   is invoked only at initialization; pressing input after GAME_OVER flaps a stationary
   pig instead of resetting.

Both are *missing wiring* defects on an otherwise coherent implementation — the gate
caught semantics a keyword scan would miss (the word "restart" is present in the source).

`scope=0.63 < 0.70` with zero external dependencies: the penalty appears to fall on
cosmetic extras beyond the bare requirement (inline CSS/shadow, enriched HUD text).
Open calibration question for P0: does the scope criterion penalize polished
completeness? Needs paired seeds to tell systematic bias from single-sample noise.

Legacy `guided` produced the same defect class as race #3 (unparseable structural
garble); the stable rejection signature across sessions (contract 0.07→0.04→0.04)
confirms the gate's determinism at low quality levels.

**Runtime/playability: NOT claimed for either candidate.** No browser playtest was
performed; all functional claims above come from static source reading plus parser ground truth.

## 4. Repair-loop PoC (direction D)

Seed: the race #3 gate-rejected guided candidate
(`demo/runs/a3d4d70854984c28b63312a6a97cb0c1/guided.raw.txt`), baseline error
`SyntaxError: Unexpected identifier 'e'` (`function e()` + later `let …,e=0,…`
redeclaration). Worker: qwen3.5:4b, think=False, **no num_predict**. Ledger:
`benchmark-runs/repair-poc-v2-20260922T154341Z.json`.

### 4.1 v1 run invalidated (harness defect)

`repair-poc-20260922T144057Z`: the repair prompt wrapped the script in
`<script-source>` angle-bracket delimiters; the model **echoed them back**, extraction
kept them, and `node --check` then reported `Unexpected token '<'` on the leading tag.
Rounds 2–4 therefore fed the model a false diagnostic on code containing no `<`; it
returned byte-identical output each time (fixed point: identical eval_count 1341,
chars 3191, ~18 min of GPU spent). Round 1 remained valid: given the accurate baseline
diagnostic, the worker rewrote the whole file and **left the flagged redeclaration in place**.

### 4.2 v2 corrected run

Fixes: no angle-bracket delimiters (plain `----- SCRIPT BEGIN/END -----` markers),
robust cleaner (fences, echoed tags, full-HTML shell extraction — validated offline
against v1's real response, byte-identical to manual extraction), explicit
**MINIMAL localized edits** instruction, fixed-point short-circuit, degenerate-response
guard, per-round raw archive.

| Round | Wall s (slot-contended/clean) | Eval tokens | Done | Parse result |
| :--- | ---: | ---: | :--- | :--- |
| Baseline | — | — | — | FAIL `Unexpected identifier 'e'` |
| 1 (localized-edits prompt + exact diagnostic) | 1575.1 (contended) | 1329 | stop | FAIL — same error; full 3154-char script returned again |
| 2 | 387.1 (clean) | 1329 | stop | **byte-identical to round 1 → fixed point, early stop** |

Final label: **Repair-exhausted-Syntax-invalid**. Gate not reached (requires a complete
parseable document).

### 4.3 Interpretation (with honest confounds)

1. **Parser-diagnostic-driven self-repair failed on this seed, twice, across two prompt
   strategies** (generic instructions in v1 round 1; minimal-localized-edits in v2 round 1).
   Both attempts returned the entire script and preserved the flagged lexical defect.
   Per the pre-declared map, A's *original* design (Tier-0 mechanical check → parser
   diagnostic → repair) is **refuted as designed** on syntax-broken seeds.
2. **Confound — one-line target:** the seed script is minified onto a single line, where
   "minimal localized edit" and "return the complete corrected source" collapse into the
   same action. The experiment therefore measured *corrected-copy production*, not diff
   patching. Multi-line formatting could change this result; noted, not re-tested today.
3. **Fixed-point behavior is load-bearing for loop design:** re-submitting unchanged
   content plus the same unresolved error yields byte-identical output. Any iterative
   repair loop must inject genuinely new information per round (semantic feedback,
   reformulated sub-goals), or it burns serial-slot budget at zero expected gain.
4. **Cost anchors (clean slot):** uncapped no-think full-script regeneration ≈ 6–7 min
   (387 s for 1329 eval tokens); contended wall clock inflated ~4× by queueing behind
   the concurrent race lanes.

## 5. Findings

- **De-compression changed the failure mode, qualitatively.** Arm B moved guided output
  from structural corruption (never parses, contract ~0.04) to a coherent, parseable,
  near-complete game failing on two precise semantic wirings (contract 0.30, quality
  1.69). Jev's value proposition shifted accordingly: on small local workers it is best
  expressed as *specification decomposition + gating*, feeding a repair stage that works
  on already-parseable candidates.
- **Cold self-repair from parser diagnostics alone is not reliable on this worker** for
  lexical-scope defect classes (2/2 failures). Retry-without-new-information is provably
  worthless (fixed point).
- **Gate depth confirmed empirically:** the contract dimension caught missing
  state-transition wiring invisible to feature-presence scans; the quality dimension
  separated coherent (1.69) from garbled (0.21) output with margin.
- **Calibration risk isolated:** scope criterion scoring a dependency-free, feature-complete
  candidate at 0.63 suggests the "unrequested scope" question may tax cosmetic polish;
  requires P0 paired measurement before any threshold change.

## 6. Decision & next experiment

Per the interpretation map, the natural successor to A is **A′ (semantic-critic
repair)**: seed = the Syntax-valid `guided_v2` candidate (or fresh B generations),
critic = a battery of per-sub-contract Jev Noul probes decomposing the requirement
(start transition, pipe spawning, collision, scoring, restart wiring, asset-freedom) so
the repair prompt receives an enumerable list of violated sub-contracts rather than a
global score, repairs as minimal localized edits, re-check (parser + battery) each
round, iteration bound declared. Fallback if A′ does not converge within its bound:
**C (arena K=3 fresh generation + Jev promotion)** — noting the systematic weak spot
(state-transition wiring) means arena members may sample the same failure distribution,
so 0/K passes at 3× cost is a realistic outcome, not excluded.

Before P0, the regeneration/promotion semantics decision (AGENTS.md invariant #5) must
be frozen so all arms use identical configuration across ≥20 paired seeds.

## 7. Boundaries

- Single-shot measurements (one seed per arm); no bootstrap CIs yet — P0 follows.
- No runtime/playtest claims; parser + static review only.
- Raw ledgers stay gitignored (`demo/runs/`, `benchmark-runs/`); loopback-only Ollama
  binding maintained; `codex-galene-swarm/` excluded from all operations.

## 8. Race #5 — first A′ measurement (run `f7cd21ce`, 2026-09-23)

Lanes `["guided_v2", "guided_a"]`: v2 re-run as an in-session drift control against
race #4; A′ = B-style seed generation → canonical gate → critic repair loop
(MAX_REPAIR_ROUNDS=3 declared cost governance). Implementation: `SUBCONTRACT_BATTERY`
(6 per-sub-contract Noul probes in one Jev call per round; diagnostic only — the
canonical three-question gate remains the sole acceptor), layered issue block with the
gate-feedback line always first, MINIMAL localized-edit repair prompt returning the full
HTML document, fixed-point short-circuit, `syntax_check` Tier-0 mechanical check
(node `vm.Script` on every non-empty script block, now installed in the demo image).

| Lane / stage | Wall s | Eval tokens | Gate (contract/scope/quality) | Syntax ground truth (node vm.Script) | Outcome |
| :--- | ---: | ---: | :--- | :--- | :--- |
| `guided_v2` (drift control) | 317.4 | 1764 | 0.57 / 0.77 / 1.85 → rejected | **valid**, zero external refs | Generated · Syntax-valid · Gate-rejected |
| `guided_a` seed | (shared slot) | 1888 | 0.40 / 0.71 / 1.91 → rejected | **valid** (confirmed in-container and host-side) | Generated · Syntax-valid · Gate-rejected |
| `guided_a` repair r1 | 1257.0 total | 3776 total | — (short-circuited) | valid — **byte-identical to seed** (same SHA-256) | lane label: **Repair-stalled-Fixed-point-R1-Gate-rejected** |

Battery state at round 1: **6/6 sub-contracts satisfied**, parse_ok true — so the issue
block handed to the worker contained *only* the generic gate-feedback line ("one or more
stated requirements are missing or wrong").

### 8.1 Forensics (static source reading + parser ground truth; no playtest claimed)

- **v2 control candidate**: the pipe collision tests read `p.l`, a property that is
  never assigned (spawn pushes `{x, y, width, gap, passed}`); every comparison against
  `undefined` yields NaN ⇒ both collision branches are permanently false. Pipes are drawn
  and scored but never collide — the core obstacle mechanic is dead code. Additionally
  the START state runs `pig.update()` under gravity, so the pig falls to the floor within
  ≈1 s of load and auto-triggers GAME_OVER; reaching PLAYING depends on pressing during
  that window. contract=0.57 reads as "feature presence without wiring".
- **A′ seed candidate**: collision geometry inconsistent with drawing. The visible gap
  spans `[p.y − gapHeight, p.y + gapHeight]` (top pipe ends at `p.y − gapHeight`, bottom
  pipe starts at `p.y + gapHeight`), but the bottom-pipe branch flags any pig with
  `pigTop ≥ p.y` — making the lower half of the visually open gap lethal. Restart takes
  two inputs (GAME_OVER→START→PLAYING), which matches the interface contract wording
  ("returns to START"), hence scope stays near-passing (0.71).

### 8.2 Findings

1. **Drift control confirms the B profile and isolates the failure dimension.** Across
   two independent seeds the contract dimension is the consistent rejection cause
   (0.30 → 0.57, both < 0.70); scope improved 0.63 → 0.77 (passing on this seed) and
   quality holds at 1.85. B alone remains below the gate, but its deficit is now a
   stable, nameable quantity rather than structural corruption.
2. **Critic localisation gap (key finding).** The fine-grained yes/no battery reported
   6/6 satisfied on a document whose holistic contract score is 0.40. Feature-presence
   probing cannot see magnitude/geometry/wiring defects (a lethal region inside a drawn
   gap, a dead NaN-guarded collision test): the holistic question catches them while the
   decomposed ones pass. Decomposition enumerates *missing features*; it does not
   guarantee *semantic-consistency* detection.
3. **Fixed-point law refined.** The information delta between rounds was ≈0 even though
   the inputs were not byte-identical: with nothing named, the repair prompt degenerated
   to an unnamed global complaint and the worker returned the document unchanged. Fixed
   points are driven by *information* deltas, not input repetition. Design rule: a
   repair dispatch must carry at least one *named* violation or its expected gain is
   zero (the short-circuit saved ~2 further full regenerations of GPU time here).
4. **Cost.** A′ consumed 3776 eval tokens / 1257 s wall (contended slot), including one
   full-document regeneration (~1888 tokens) bought for zero information; the control
   spent 1764 / 317 s. Until the critic names something, A′ costs more than B and adds
   no acceptance.

### 8.3 Decision point

Per the pre-declared interpretation map, A′ did not converge within its bound on this
seed. The forensics, however, identify a concrete design fix before invoking the arena
fallback: make the critic **naming-based instead of boolean** — Jev must identify the
specific violated requirement (choice over the requirement dimensions plus an explicit
"state exactly what is broken" instruction), and repairs dispatch only when at least one
violation is named; if none can be named, fall back to fresh regeneration (arena-lite)
rather than a guaranteed-zero repair round. This successor is designated **A″**.
Candidate directions: (i) implement A″ naming-critic; (ii) invoke fallback C (arena
K=3, same-failure-distribution risk noted in §6); (iii) go straight to P0 paired
measurement to size the current arms' distributions first.

Boundaries for §8: single seed per arm (directional evidence only); contended-slot
wall clocks; defect diagnoses are high-confidence static readings, not executed playtests.

## 9. A″ fresh-generation arena follow-up (2026-09-23)

The first live run (`9ef4c28177f54bbebba41ab626a5f5ce`) re-ran `guided_v2` as a
control and started A″. The control was gate-rejected (contract 0.54, scope 0.67,
quality 1.91; 2265 eval tokens). A″ reached the three-candidate fallback, but the demo
container was recreated while the lane was running. Its in-memory API state was lost;
only the seed and arena candidates 1–2 had been written to disk, so the original lane
selection and candidate-3 outcome are **not recoverable**. Do not treat that run as a
completed arena or promote anything from it.

The two saved arena candidates were independently rechecked with the same syntax check
and canonical Jev gate (diagnostic re-evaluation, not the original lane ledger):

| Candidate | Syntax | Gate (contract/scope/quality) | Outcome |
| :--- | :--- | :--- | :--- |
| Arena 1 | valid | 0.57 / 0.68 / 2.05 | rejected (contract and scope below 0.70) |
| Arena 2 | valid | 0.55 / 0.67 / 2.04 | rejected (contract and scope below 0.70) |

Arena 1 was also exercised in the pinned, network-disabled Chromium sandbox. With a
deterministic safe pipe gap it started on Space, remained alive through pipe passage,
incremented the visible score, reached Game Over, cleared that state on click, and
started again on Space. The browser observed no uncaught JS errors or external requests.
This is a playable smoke test, not proof of balanced difficulty or complete collision
coverage; the Jev gate still rejects this candidate. Arena 2's source has a clear
collision-geometry defect: its vertical test compares the pig against the single
`gapY` boundary with an `OR`, making almost every pipe overlap lethal.

The demo now atomically checkpoints each run to `demo/runs/<id>/run.json` and reloads
completed runs on startup. Any nonterminal lane found after a container restart is
marked `failed` with an explicit interruption detail; raw candidates and progress fields
remain available. A″ was restarted as a single-lane run
(`be0f8eb8f96c4aecb3a15ab6d6d34d4b`) to avoid repeat queue contention; its terminal
result will be recorded here when available.

P0 remains outstanding: run the fixed nine-task corpus for at least 20 paired seeds
per task (180 task-seed pairs, 360 live generations) and inspect the resulting
ledger/report before making comparative claims.
