#!/usr/bin/env python3
"""Live, evidence-first comparison between direct and Jev-guided local generation."""

import json
import os
import re
import threading
import time
import urllib.request
import uuid
from http import HTTPStatus
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from scripts.jev_swarm import GenericRuntimeValidator, JevClient

ROOT = Path(__file__).resolve().parent.parent
DEMO_ROOT = ROOT / "demo"
RUN_ROOT = DEMO_ROOT / "runs"
WORKER_PROVIDER = os.environ.get("JEV_DEMO_WORKER_PROVIDER", "ollama")
WORKER_BASE_URL = os.environ.get("JEV_DEMO_WORKER_BASE_URL", "http://host.docker.internal:11434").rstrip("/")
MODEL = os.environ.get("JEV_DEMO_MODEL", "qwen3.5:4b")
PORT = int(os.environ.get("JEV_DEMO_PORT", "8088"))
LOCK = threading.Lock()
RUNS = {}

GAME_REQUIREMENT = """Create a complete, single-file HTML5 Canvas Flappy Bird clone starring a flying pig.
It must run without external assets, support Space/click input, have gravity, pipes, scoring,
collision detection, start and restart states, and return only a complete <!doctype html> document."""
GUIDED_REQUIREMENT = """Output only a compact, complete <!doctype html> Canvas Flappy Pig game in under 900 tokens.
Use one canvas, an emoji pig, Space/click flap, gravity, moving pipes, collision, score, and restart.
No libraries, assets, CSS framework, comments, or explanations."""

# Arm B (Guided-v2): the de-compressed requirement. No size language at all —
# cap-free policy (2026-09-22): generation arms set no soft prompt targets.
GUIDED_REQUIREMENT_V2 = """Output only a complete <!doctype html> Canvas Flappy Pig game.
Use one canvas, an emoji pig, Space/click flap, gravity, moving pipes, collision, score, and restart.
No libraries, assets, CSS framework, or explanations."""

# Per AGENTS.md invariant #1 the worker receives concise interface declarations,
# not accumulated prose. Contracts are deterministic so paired seeds stay
# comparable across runs; the Choice step picks the architecture they instantiate.
INTERFACE_CONTRACTS = {
    "canvas_state_machine": """state: one gameState variable holding START | PLAYING | GAME_OVER.
pig: object with x, y, vy; methods draw(), update(), flap() where flap sets an upward velocity change.
pipes: list of obstacles, each with x and gapY; spawn() appends an obstacle on a fixed frame interval, update() moves them left, draw() renders the top and bottom rectangles, collides(pig) returns bool.
score: integer incremented when the player passes an obstacle; collision sets gameState to GAME_OVER; input in that state resets score and returns to START.
input: window keydown for Space plus mousedown and touchstart trigger flap, or start/restart depending on gameState.
loop: requestAnimationFrame-driven gameLoop that updates the current state, draws the background, entities, and the HUD.""",
    "framework": """structure: plain single-file modules without any framework.
state machine: object holding START | PLAYING | GAME_OVER with event-driven transitions.
pig entity: object with x, y, vy plus draw(), update(), flap() methods where flap applies an upward velocity change.
pipes manager: spawn() appends obstacles with x and gapY on a fixed interval, update() moves them left, draw() renders top/bottom rectangles, collides(pig) returns bool.
score counter: integer incremented per passed obstacle; collision triggers GAME_OVER; restart resets score and state to START.
shared input dispatch: one handler binding Space keydown, mousedown, and touchstart routes to the current state's action.
game loop: one requestAnimationFrame callback updating the state machine then rendering background, entities, and HUD each tick.""",
}

# Arm A′ (semantic-critic repair), added 2026-09-22 after the repair PoC refuted
# parser-diagnostic-only self-repair on this worker. The critic therefore feeds each
# repair round an enumerable list of violated sub-contracts instead of a global score;
# every repair prompt always carries the canonical gate feedback line, so no round ever
# re-submits unchanged content plus an unresolved diagnostic (the proven fixed point).
MAX_REPAIR_ROUNDS = 3  # declared cost governance (serial inference-slot budget), not a content limit
BATTERY_FAIL_THRESHOLD = 0.70
SUBCONTRACT_BATTERY = {
    "start_flow": "Does the specified input (Space/click/tap) actually transition the game from its initial state into play?",
    "play_update": "During play, do gravity update the pig's motion and the pipes move toward the player every frame?",
    "collision": "Do collisions with pipes or screen boundaries end the run in a game-over state?",
    "scoring": "Is the score incremented when a pipe is passed and visible on screen during play?",
    "restart": "After game over, does the specified input reset the game so it can be played again from zero?",
    "asset_freedom": "Does the game run entirely without external libraries, asset files, or network requests?",
}
REPAIR_PROMPT_TEMPLATE = """You are repairing a JavaScript game inside a single-file HTML document. Make MINIMAL localized edits that fix the listed issues while preserving everything that already works.

Automated review report (repair round {round} of at most {max_rounds}):

{issues}

Current full document:
----- DOCUMENT BEGIN -----
{doc}
----- DOCUMENT END -----

Rules:
- Apply the smallest possible changes; do not rewrite working sections or rename existing identifiers.
- Keep the requirements intact: a canvas Flappy Pig game with an emoji pig, Space/click flap, gravity, moving pipes, collision, a visible score, and restart after game over. No libraries, assets, CSS framework, or explanations.
- Return ONLY the complete corrected <!doctype html> document. No markdown fences, no wrapper tags, no change commentary."""

CANONICAL_GATE_QUESTIONS = {
    "contract": {"type": "noul", "instructions": "Does the candidate satisfy every stated game requirement?"},
    "scope": {"type": "noul", "instructions": "Does the candidate avoid external dependencies and unrequested scope?"},
    "quality": {"type": "score", "instructions": "Rate functional clarity and maintainability from 0 to 3.", "criteria": ["broken", "rough", "solid", "excellent"]},
}


def read_env_file_value(file_variable: str, key: str) -> str | None:
    """Read exactly one dotenv value from an explicitly mounted read-only secret file."""
    path = os.environ.get(file_variable)
    if not path:
        return None
    try:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip("\"'") or None
    except OSError:
        return None
    return None


TYPESAFE_KEY = os.environ.get("TYPESAFE_API_KEY") or read_env_file_value("JEV_DEMO_TYPESAFE_ENV_FILE", "TYPESAFE_API_KEY")
TYPESAFE_URL = os.environ.get("JEV_DEMO_TYPESAFE_URL") or read_env_file_value("JEV_DEMO_TYPESAFE_ENV_FILE", "TYPESAFE_BASE_URL") or "https://api.typesafe.ai/v1/systemone"
GALENE_API_KEY = os.environ.get("JEV_DEMO_GALENE_API_KEY") or read_env_file_value("JEV_DEMO_GALENE_ENV_FILE", "GALENE_API_KEY")


def extract_html(raw: str) -> str:
    match = re.search(r"((?:<!doctype html[^>]*>\s*)?<html\b.*?</html>)", raw, re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError("model response did not contain a complete HTML document")
    return match.group(1).strip()


def ollama_generate(prompt: str, thinking: bool) -> tuple[str, int]:
    """Call the local worker directly so Qwen's think control is unambiguous."""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "think": thinking,
        # Cap-free policy (2026-09-22): no num_predict ceiling in any
        # experimental payload; the worker generates until its own stop token.
        # (The probe of that day measured a natural stop at 4202 tokens for the
        # think-on task; there is deliberately no budget derived from it.)
        "options": {"temperature": 0.2},
    }
    # The iGPU-backed worker sustains ~3.4 tok/s and the lanes share one
    # inference slot serially, so a slow lane can hold the other in Ollama's
    # queue. The 2400 s client deadline is a wall-clock hang guard only: it
    # covers queue wait plus full generation and never limits content length.
    request = urllib.request.Request(
        f"{WORKER_BASE_URL}/api/generate", data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request, timeout=2400) as response:
        payload = json.loads(response.read().decode("utf-8"))
    content = payload.get("response")
    if not isinstance(content, str) or not content.strip():
        raise ValueError(f"Ollama returned no final content (done_reason={payload.get('done_reason')})")
    return content, int(payload.get("eval_count", 0))


def openai_generate(prompt: str, reasoning_effort: str = "none", max_tokens: int | None = None) -> tuple[str, int]:
    """Optional compatibility path for the historical Galene demonstration."""
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "temperature": 0.2,
        "reasoning_effort": reasoning_effort,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if reasoning_effort == "none":
        # Galene serves Qwen3.8 through vLLM; this is its native control for
        # suppressing the reasoning channel before it consumes the code budget.
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    headers = {"Content-Type": "application/json"}
    if GALENE_API_KEY:
        headers["Authorization"] = f"Bearer {GALENE_API_KEY}"
    request = urllib.request.Request(
        f"{WORKER_BASE_URL}/chat/completions", data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    with urllib.request.urlopen(request, timeout=240) as response:
        payload = json.loads(response.read().decode("utf-8"))
    choices = payload.get("choices", [])
    if not choices or not isinstance(choices[0].get("message", {}).get("content"), str):
        choice = choices[0] if choices else {}
        reasoning_length = len(choice.get("message", {}).get("reasoning") or "")
        raise ValueError(
            "OpenAI-compatible worker returned no final content "
            f"(finish_reason={choice.get('finish_reason')}, reasoning_chars={reasoning_length})"
        )
    return choices[0]["message"]["content"], int(payload.get("usage", {}).get("completion_tokens", 0))


def worker_generate(prompt: str, thinking: bool, max_tokens: int | None = None) -> tuple[str, int]:
    if WORKER_PROVIDER == "ollama":
        # Ollama path is cap-free by policy; max_tokens applies only to the
        # optional OpenAI-compatible path, which demo lanes never set.
        return ollama_generate(prompt, thinking)
    if WORKER_PROVIDER == "openai":
        return openai_generate(prompt, "high" if thinking else "none", max_tokens)
    raise ValueError(f"Unsupported JEV_DEMO_WORKER_PROVIDER: {WORKER_PROVIDER!r}")


def syntax_check(html: str) -> tuple[bool, str]:
    """Tier-0 mechanical check (node vm.Script) on every executable script block.

    GenericRuntimeValidator fails closed on any input containing a <script tag, so it
    only receives extracted bodies; every non-empty block must parse. Tooling exceptions
    mean "check unavailable" and are never reported as parse-ok — a failed tool must not
    be mistaken for passing code.
    """
    blocks = [match.group(1) for match in re.finditer(r"<script[^>]*>(.*?)</script>", html, re.IGNORECASE | re.DOTALL)]
    blocks = [block for block in blocks if block.strip()]
    if not blocks:
        return False, "no executable <script> block found"
    for js in blocks:
        try:
            ok, message = GenericRuntimeValidator.validate_code(js.strip(), lang="javascript")
        except Exception as exc:  # node missing / timeout / unexpected validator error
            return False, f"mechanical check unavailable ({exc})"
        if not ok:
            return False, message
    return True, "all script blocks parse"


def canonical_gate(jev: JevClient, html: str) -> tuple[float, float, float, float]:
    """The frozen three-question acceptance gate shared by every guided arm."""
    answers, seconds = jev.evaluate(
        f"## Trusted requirement\n{GUIDED_REQUIREMENT_V2}\n\n## Untrusted candidate\n```html\n{html}\n```",
        CANONICAL_GATE_QUESTIONS,
    )
    return float(answers["contract"]["noul"]), float(answers["scope"]["noul"]), float(answers["quality"]["score"]), seconds


def gate_passed(contract: float, scope: float, quality: float) -> bool:
    return contract >= 0.70 and scope >= 0.70 and quality >= 1.0


def gate_feedback(contract: float, scope: float, quality: float) -> str:
    """Per-dimension failure summary used as the fresh repair signal; '' when passed."""
    dims = []
    if contract < 0.70:
        dims.append(f"contract={contract:.2f} below 0.70 — one or more stated requirements are missing or wrong")
    if scope < 0.70:
        dims.append(f"scope={scope:.2f} below 0.70 — remove external dependencies or unrequested additions")
    if quality < 1.0:
        dims.append(f"quality={quality:.2f} below 1.0 — functionality is broken or unclear")
    return "; ".join(dims)


def battery_violations(jev: JevClient, html: str) -> tuple[list[str], int, float]:
    """One Jev evaluate decomposing the requirement into per-sub-contract Noul probes.

    Diagnostic only: the battery never accepts a candidate — the canonical gate does.
    Returns (violated sub-contract statements, satisfied count, seconds).
    """
    answers, seconds = jev.evaluate(
        f"## Trusted requirement\n{GUIDED_REQUIREMENT_V2}\n\n## Untrusted candidate\n```html\n{html}\n```",
        {name: {"type": "noul", "instructions": statement} for name, statement in SUBCONTRACT_BATTERY.items()},
    )
    violations = [statement for name, statement in SUBCONTRACT_BATTERY.items()
                  if float(answers[name]["noul"]) < BATTERY_FAIL_THRESHOLD]
    return violations, len(SUBCONTRACT_BATTERY) - len(violations), seconds


def assemble_repair_issues(gate_summary: str, violations: list[str], parse_ok: bool, parse_err: str) -> str:
    """Layered issue block for a repair prompt: gate feedback always first (a fresh,
    guaranteed signal even when the battery and parser have nothing new to report)."""
    lines = [f"GATE FEEDBACK: {gate_summary}"] if gate_summary else ["GATE FEEDBACK: acceptance gate failing; see violation reports below"]
    if not parse_ok:
        lines.append(f"PARSER ERROR: {parse_err}")
    lines.extend(f"VIOLATES REQUIREMENT: {violation}" for violation in violations)
    return "\n".join(lines)


def update_lane(run_id: str, lane_id: str, **changes: object) -> None:
    with LOCK:
        lane = RUNS[run_id]["lanes"][lane_id]
        lane.update(changes)
        lane["elapsed_seconds"] = round(time.perf_counter() - lane["started_at"], 2)


def persist_artifact(run_id: str, lane_id: str, html: str) -> str:
    run_dir = RUN_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / f"{lane_id}.html"
    path.write_text(html, encoding="utf-8")
    return f"/runs/{run_id}/{lane_id}.html"


def persist_raw(run_id: str, lane_id: str, raw: str) -> None:
    """Keep truncated or gate-rejected raw output in the run ledger (gitignored)."""
    run_dir = RUN_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / f"{lane_id}.raw.txt").write_text(raw, encoding="utf-8")


def run_direct(run_id: str) -> None:
    try:
        update_lane(run_id, "direct", status="generating", detail="Sending one broad prompt to local Qwen with thinking enabled…")
        raw, tokens = worker_generate(GAME_REQUIREMENT, thinking=True)
        # Record tokens as soon as generation completes so failed lanes keep
        # their cost evidence (extraction/gate failures must not lose it).
        update_lane(run_id, "direct", tokens=tokens)
        try:
            artifact_url = persist_artifact(run_id, "direct", extract_html(raw))
        except ValueError:
            persist_raw(run_id, "direct", raw)
            raise ValueError(f"model response did not contain a complete HTML document ({len(raw)} chars, {tokens} eval tokens)")
        update_lane(run_id, "direct", status="ready", tokens=tokens, artifact_url=artifact_url, detail=f"Generated {tokens} tokens.")
    except Exception as exc:
        update_lane(run_id, "direct", status="failed", detail=str(exc))
    finish_run_if_complete(run_id)


def run_guided(run_id: str) -> None:
    try:
        update_lane(run_id, "guided", status="planning", detail="Jev is selecting a compact game blueprint…")
        jev = JevClient(api_key=TYPESAFE_KEY, url=TYPESAFE_URL)
        answers, plan_seconds = jev.evaluate(GAME_REQUIREMENT, {
            "blueprint": {"type": "choice", "instructions": "Choose the most reliable compact implementation plan.", "criteria": {
                "canvas_state_machine": "One Canvas file with explicit start, playing and game-over states.",
                "framework": "A framework-based multi-file game.",
            }},
            "scope": {"type": "noul", "instructions": "Can this be safely completed as one asset-free HTML file?"},
        })
        blueprint = answers["blueprint"]["choice"]
        update_lane(run_id, "guided", status="generating", detail=f"Jev selected {blueprint}; local Qwen is generating constrained code…", jev_seconds=round(plan_seconds, 2))
        prompt = f"{GUIDED_REQUIREMENT}\n\nChosen blueprint: {blueprint}."
        raw, tokens = worker_generate(prompt, thinking=False)
        update_lane(run_id, "guided", tokens=tokens)
        try:
            html = extract_html(raw)
        except ValueError:
            persist_raw(run_id, "guided", raw)
            raise ValueError(f"model response did not contain a complete HTML document ({len(raw)} chars, {tokens} eval tokens)")
        update_lane(run_id, "guided", status="reviewing", detail="Jev is checking contract compliance and scope…")
        answers, review_seconds = jev.evaluate(
            f"## Trusted requirement\n{GUIDED_REQUIREMENT}\n\n## Untrusted candidate\n```html\n{html}\n```",
            {
                "contract": {"type": "noul", "instructions": "Does the candidate satisfy every stated game requirement?"},
                "scope": {"type": "noul", "instructions": "Does the candidate avoid external dependencies and unrequested scope?"},
                "quality": {"type": "score", "instructions": "Rate functional clarity and maintainability from 0 to 3.", "criteria": ["broken", "rough", "solid", "excellent"]},
            },
        )
        contract = float(answers["contract"]["noul"])
        scope = float(answers["scope"]["noul"])
        quality = float(answers["quality"]["score"])
        if contract < 0.70 or scope < 0.70 or quality < 1.0:
            persist_raw(run_id, "guided", html)
            raise ValueError(
                f"Jev gate rejected candidate ({tokens} eval tokens): "
                f"contract={contract:.2f}, scope={scope:.2f}, quality={quality:.2f}")
        artifact_url = persist_artifact(run_id, "guided", html)
        update_lane(run_id, "guided", status="ready", tokens=tokens, artifact_url=artifact_url, detail=(
            f"Generated {tokens} tokens; Jev {plan_seconds + review_seconds:.2f}s; contract={contract:.2f}, scope={scope:.2f}, quality={quality:.2f}."))
    except Exception as exc:
        update_lane(run_id, "guided", status="failed", detail=str(exc))
    finish_run_if_complete(run_id)


def guided_plan(jev: JevClient) -> tuple[str, float]:
    """Planning step shared by guided_v2/guided_a: Jev picks the blueprint choice."""
    answers, plan_seconds = jev.evaluate(GAME_REQUIREMENT, {
        "blueprint": {"type": "choice", "instructions": "Choose the most reliable compact implementation plan.", "criteria": {
            "canvas_state_machine": "One Canvas file with explicit start, playing and game-over states.",
            "framework": "A framework-based multi-file game.",
        }},
        "scope": {"type": "noul", "instructions": "Can this be safely completed as one asset-free HTML file?"},
    })
    return answers["blueprint"]["choice"], plan_seconds


def guided_generation_prompt(blueprint: str) -> tuple[str, str]:
    """Generation prompt shared by guided_v2/guided_a: deterministic interface-contract
    handoff (AGENTS.md invariant #1 — declarations downstream, never accumulated prose)."""
    # The output format is always one self-contained HTML document, so any
    # blueprint outside the single-file contracts maps to the state-machine
    # one; the mapping is recorded in the lane detail for the study record.
    contract_key = blueprint if blueprint in INTERFACE_CONTRACTS else "canvas_state_machine"
    fallback_note = "" if contract_key == blueprint else f" (blueprint {blueprint!r} mapped to single-file contract {contract_key!r})"
    prompt = (f"{GUIDED_REQUIREMENT_V2}\n\nImplement exactly this interface contract:\n{INTERFACE_CONTRACTS[contract_key]}\n\n"
              "Return only the complete HTML document.")
    return prompt, fallback_note


def run_guided_v2(run_id: str) -> None:
    """Arm B (Guided-v2): same Jev planning, de-compressed cap-free generation."""
    try:
        update_lane(run_id, "guided_v2", status="planning", detail="Jev is selecting a game architecture…")
        jev = JevClient(api_key=TYPESAFE_KEY, url=TYPESAFE_URL)
        blueprint, plan_seconds = guided_plan(jev)
        prompt, fallback_note = guided_generation_prompt(blueprint)
        update_lane(run_id, "guided_v2", status="generating",
                    detail=f"Jev selected {blueprint}{fallback_note}; local Qwen implements the interface contract, no size limits…",
                    jev_seconds=round(plan_seconds, 2))
        raw, tokens = worker_generate(prompt, thinking=False)
        update_lane(run_id, "guided_v2", tokens=tokens)
        try:
            html = extract_html(raw)
        except ValueError:
            persist_raw(run_id, "guided_v2", raw)
            raise ValueError(f"model response did not contain a complete HTML document ({len(raw)} chars, {tokens} eval tokens)")
        update_lane(run_id, "guided_v2", status="reviewing", detail="Jev is checking contract compliance and scope against the cap-free requirement…")
        contract_score, scope_score, quality_score, review_seconds = canonical_gate(jev, html)
        if not gate_passed(contract_score, scope_score, quality_score):
            persist_raw(run_id, "guided_v2", html)
            raise ValueError(
                f"Jev gate rejected candidate ({tokens} eval tokens): "
                f"contract={contract_score:.2f}, scope={scope_score:.2f}, quality={quality_score:.2f}")
        artifact_url = persist_artifact(run_id, "guided_v2", html)
        update_lane(run_id, "guided_v2", status="ready", tokens=tokens, artifact_url=artifact_url, detail=(
            f"Cap-free arm · blueprint={blueprint}: generated {tokens} tokens; Jev {plan_seconds + review_seconds:.2f}s; "
            f"contract={contract_score:.2f}, scope={scope_score:.2f}, quality={quality_score:.2f}."))
    except Exception as exc:
        update_lane(run_id, "guided_v2", status="failed", detail=str(exc))
    finish_run_if_complete(run_id)


def run_guided_a(run_id: str) -> None:
    """Arm A′ (semantic-critic repair) on top of B-style generation.

    Seed: fresh B generation (Choice + interface contract, uncapped no-think). Critic:
    the canonical three-question gate plus a sub-contract Noul battery that decomposes
    the failure into enumerable violations (diagnostic only — the gate alone accepts).
    Repairs ask for MINIMAL localized edits, receive the layered issue block (gate
    feedback line always first = fresh guaranteed signal per round), and return the full
    HTML document so no splicing confound can arise. Fixed-point candidates short-
    circuit early because retrying without new information is proven worthless (PoC v2).
    MAX_REPAIR_ROUNDS is declared cost governance, not a content limit.
    """
    history: list[dict] = []
    total_tokens = 0
    try:
        update_lane(run_id, "guided_a", status="planning", detail="Jev is selecting a game architecture…")
        jev = JevClient(api_key=TYPESAFE_KEY, url=TYPESAFE_URL)
        blueprint, plan_seconds = guided_plan(jev)
        prompt, fallback_note = guided_generation_prompt(blueprint)
        update_lane(run_id, "guided_a", status="generating",
                    detail=f"Jev selected {blueprint}{fallback_note}; local Qwen implements the interface contract, no size limits…",
                    jev_seconds=round(plan_seconds, 2))
        raw, tokens = worker_generate(prompt, thinking=False)
        total_tokens = tokens
        update_lane(run_id, "guided_a", tokens=total_tokens)
        try:
            candidate = extract_html(raw)
        except ValueError:
            persist_raw(run_id, "guided_a", raw)
            raise ValueError(f"model response did not contain a complete HTML document ({len(raw)} chars, {tokens} eval tokens)")
        update_lane(run_id, "guided_a", status="reviewing", detail="Jev gate is reviewing the seed candidate…")
        contract, scope, quality, _seed_gate_seconds = canonical_gate(jev, candidate)
        summary = gate_feedback(contract, scope, quality)
        history.append({"round": 0, "seed": True, "contract": round(contract, 2), "scope": round(scope, 2), "quality": round(quality, 2)})
        if not gate_passed(contract, scope, quality):
            outcome = None
            for rnd in range(1, MAX_REPAIR_ROUNDS + 1):
                update_lane(run_id, "guided_a", status="repairing",
                            detail=f"Repair round {rnd}/{MAX_REPAIR_ROUNDS}: Jev critic decomposes violated sub-contracts…")
                violations, satisfied_count, _battery_seconds = battery_violations(jev, candidate)
                parse_ok, parse_err = syntax_check(candidate)
                issues = assemble_repair_issues(summary, violations, parse_ok, parse_err)
                previous = candidate
                repair_prompt = REPAIR_PROMPT_TEMPLATE.format(round=rnd, max_rounds=MAX_REPAIR_ROUNDS, issues=issues, doc=candidate)
                raw_r, tokens_r = worker_generate(repair_prompt, thinking=False)
                total_tokens += tokens_r
                update_lane(run_id, "guided_a", tokens=total_tokens)
                persist_raw(run_id, f"guided_a.r{rnd}", raw_r)
                try:
                    candidate = extract_html(raw_r)
                except ValueError:
                    persist_raw(run_id, "guided_a", raw_r)
                    raise ValueError(f"repair round {rnd} returned no complete HTML document ({len(raw_r)} chars, {tokens_r} eval tokens)")
                if candidate.strip() == previous.strip():
                    history.append({"round": rnd, "fixed_point": True,
                                    "battery_satisfied": f"{satisfied_count}/{len(SUBCONTRACT_BATTERY)}", "parse_ok": parse_ok})
                    outcome = ("fixed_point", rnd)
                    break
                contract, scope, quality, _gate_seconds = canonical_gate(jev, candidate)
                summary = gate_feedback(contract, scope, quality)
                history.append({"round": rnd, "fixed_point": False,
                                "battery_satisfied": f"{satisfied_count}/{len(SUBCONTRACT_BATTERY)}", "parse_ok": parse_ok,
                                "contract": round(contract, 2), "scope": round(scope, 2), "quality": round(quality, 2)})
                if gate_passed(contract, scope, quality):
                    outcome = ("passed", rnd)
                    break
            if outcome is None:
                persist_raw(run_id, "guided_a", candidate)
                raise ValueError(
                    f"repair bound exhausted ({MAX_REPAIR_ROUNDS} declared rounds); last gate: {summary}; "
                    f"history={json.dumps(history)}")
            if outcome[0] == "fixed_point":
                persist_raw(run_id, "guided_a", candidate)
                raise ValueError(
                    f"worker hit a fixed point at repair round {outcome[1]} (returned an unchanged document); "
                    f"last gate: {summary}; history={json.dumps(history)}")
            artifact_url = persist_artifact(run_id, "guided_a", candidate)
            update_lane(run_id, "guided_a", status="ready", tokens=total_tokens, artifact_url=artifact_url, detail=(
                f"Critic-repaired after {outcome[1]} round(s); {total_tokens} tokens; "
                f"contract={contract:.2f}, scope={scope:.2f}, quality={quality:.2f}; history={json.dumps(history)}"))
        else:
            artifact_url = persist_artifact(run_id, "guided_a", candidate)
            update_lane(run_id, "guided_a", status="ready", tokens=total_tokens, artifact_url=artifact_url, detail=(
                f"Gate passed on the seed candidate (0 repair rounds); {total_tokens} tokens; "
                f"contract={contract:.2f}, scope={scope:.2f}, quality={quality:.2f}; history={json.dumps(history)}"))
    except Exception as exc:
        update_lane(run_id, "guided_a", status="failed", detail=str(exc))
    finish_run_if_complete(run_id)


def finish_run_if_complete(run_id: str) -> None:
    with LOCK:
        run = RUNS[run_id]
        if all(lane["status"] in {"ready", "failed"} for lane in run["lanes"].values()):
            run["status"] = "complete"


LANE_ORDER = ("direct", "guided", "guided_v2", "guided_a")
LANE_RUNNERS = {"direct": run_direct, "guided": run_guided, "guided_v2": run_guided_v2, "guided_a": run_guided_a}


def create_run(lanes: list[str] | None = None) -> dict:
    """Start a race. Defaults to the historical direct/guided pair; research
    probes may request subsets (e.g. ["guided_v2", "guided_a"]) to control the
    serial-slot wall clock."""
    selected = list(dict.fromkeys(lanes)) if lanes else list(LANE_ORDER[:2])
    unknown = [lane for lane in selected if lane not in LANE_RUNNERS]
    if not selected or unknown:
        raise ValueError(f"unsupported lanes: {', '.join(unknown) if unknown else 'none requested'}")
    ordered = [lane for lane in LANE_ORDER if lane in selected]
    run_id = uuid.uuid4().hex
    now = time.perf_counter()
    run = {"id": run_id, "status": "running", "model": MODEL, "provider_url": WORKER_BASE_URL, "lanes": {
        lane: {"status": "queued", "detail": "Queued.", "elapsed_seconds": 0.0, "started_at": now, "tokens": 0}
        for lane in ordered
    }}
    with LOCK:
        RUNS[run_id] = run
    for lane in ordered:
        threading.Thread(target=LANE_RUNNERS[lane], args=(run_id,), daemon=True).start()
    return public_run(run)


def public_run(run: dict) -> dict:
    result = {key: value for key, value in run.items() if key != "lanes"}
    result["lanes"] = {}
    for name, lane in run["lanes"].items():
        result["lanes"][name] = {key: value for key, value in lane.items() if key != "started_at"}
        if lane["status"] not in {"ready", "failed"}:
            result["lanes"][name]["elapsed_seconds"] = round(time.perf_counter() - lane["started_at"], 2)
    return result


class DemoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DEMO_ROOT), **kwargs)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            parsed = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("malformed JSON body")
        if not isinstance(parsed, dict):
            raise ValueError("body must be a JSON object")
        return parsed

    def do_POST(self):
        if self.path != "/api/runs":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            payload = create_run(self._read_json_body().get("lanes"))
        except (TypeError, ValueError) as exc:
            self.send_error(HTTPStatus.BAD_REQUEST, f"body must be JSON like {{\"lanes\": [\"direct\", \"guided\"]}} ({exc})")
            return
        self.send_json(HTTPStatus.CREATED, payload)

    def do_GET(self):
        match = re.fullmatch(r"/api/runs/([a-f0-9]{32})", self.path)
        if match:
            with LOCK:
                run = RUNS.get(match.group(1))
                if not run:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                payload = public_run(run)
            self.send_json(HTTPStatus.OK, payload)
            return
        if self.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def send_json(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    print(f"Jev demo: http://0.0.0.0:{PORT} · provider={WORKER_PROVIDER} · model={MODEL} · worker={WORKER_BASE_URL}")
    ThreadingHTTPServer(("0.0.0.0", PORT), DemoHandler).serve_forever()
