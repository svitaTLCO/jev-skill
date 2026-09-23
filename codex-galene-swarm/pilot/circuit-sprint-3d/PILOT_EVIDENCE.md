# Circuit Sprint 3D pilot evidence

**Date:** 2026-09-23. **Status:** playable first slice; swarm quality gate did
not pass the game contracts.

## Swarm runs

Codex sent bounded JavaScript contracts through the installed MCP service to
the internal Galene `Galene/LLM` route. The service used the mandatory Jev gate
and stored responses in the dedicated local Docker volume
`circuit-sprint-swarm-ledger`. The endpoint owner has not independently
confirmed which deployment backs that route.

| Run ID | Contracts | Result |
|---|---|---|
| `6419e618df6044609494ba86f8e5c64a` | Race loop, track world, vehicle physics | Two candidates rejected by Jev; vehicle physics returned no content |
| `0a2b2202b2094b4a810179f4772ad8bf` | Car mesh, keyboard input, track math | Three candidates rejected by Jev |
| `ab6ccd40cdb64be786d1b8efb0ec3cb1` | Track module, no task token ceiling | Full 3,564-token candidate returned; Jev rejected |

The first larger contracts were also tried with a 4,000-token ceiling and
returned no usable content after consuming the budget as reasoning. A direct
provider probe showed that top-level `enable_thinking: false`, together with
the existing chat-template flag, produced answer text on this route. The
provider now requests low reasoning effort and sets both nonthinking flags.
The adapter change has a focused unit test and the full swarm suite passes.

After removing the product's fixed token ceiling, the track task returned a
12,309-character candidate with `finish_reason=stop`, 3,564 completion tokens,
zero reasoning tokens, and about 80 seconds provider latency. Jev reported
reference integrity 0.85, specification compliance 0.62, scope control 0.82,
and quality 2.4/3. The gate failed on specification compliance. This shows the
ceiling was a real research constraint, but its removal alone did not make the
track candidate acceptable. The endpoint may still impose its own limits.

Jev rejected all six nonempty game candidates. Codex manually inspected the
smaller car-mesh, keyboard-input, and track-math candidates, stripped response
fences, and used them as starting points for three modules. Codex implemented
the track, vehicle physics, race rules, UI, and integration, then validated the
whole game. **No game candidate passed the mandatory Jev gate; this is not an
autonomous swarm success or a gate-approved promotion.** The experiment
demonstrates model output and orchestration, while identifying task sizing,
contract fidelity, and gate calibration as release blockers for this workload.

## Executable evidence

| Check | Result | Boundary |
|---|---|---|
| Swarm Docker suite | 23 passed | Contract, provider, MCP, orchestration, and fake verifier tests |
| Game Node suite | 5 passed | Track, mesh, controls, car bounds, AI three-lap completion |
| Production build | Passed | Vite output generated; Three.js bundle size warning remains |
| Chromium browser suite | 2 passed | Render, solo start/drive/timer/pause, two-player controls and HUD |
| Visual inspection | Passed | Rendered 1280×800 start and paused-race screenshots inspected; [race screenshot](screenshots/racing.png) committed |

The browser check used software WebGL in
`mcr.microsoft.com/playwright:v1.63.0-noble`. Its first attempt timed out after
taking a screenshot before the solo click; moving screenshots after the
interaction checks yielded two passing runs. The race completion result is
covered by the simulation test, not by a full-length browser race. Human play
feel, sustained frame rate, real GPU behavior, and cross-machine Linux/WSL
installation remain to be evaluated with the team.

## Reproduction

Run the commands in [README.md](README.md). `npm ci` consumes the committed
lockfile. The browser test saves screenshots under ignored `artifacts/`.
Candidate text stays in the dedicated volume and ignored local `candidates/`;
the repository records only contract inputs and aggregate outcomes.
