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

from scripts.jev_swarm import JevClient

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


def ollama_generate(prompt: str, thinking: bool, max_tokens: int | None = None) -> tuple[str, int]:
    """Call the local worker directly so Qwen's think control is unambiguous."""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "think": thinking,
        "options": {"temperature": 0.2, "num_predict": max_tokens or 1800},
    }
    request = urllib.request.Request(
        f"{WORKER_BASE_URL}/api/generate", data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request, timeout=420) as response:
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
        return ollama_generate(prompt, thinking, max_tokens)
    if WORKER_PROVIDER == "openai":
        return openai_generate(prompt, "high" if thinking else "none", max_tokens)
    raise ValueError(f"Unsupported JEV_DEMO_WORKER_PROVIDER: {WORKER_PROVIDER!r}")


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


def run_direct(run_id: str) -> None:
    try:
        update_lane(run_id, "direct", status="generating", detail="Sending one broad prompt to local Qwen with thinking enabled…")
        raw, tokens = worker_generate(GAME_REQUIREMENT, thinking=True)
        artifact_url = persist_artifact(run_id, "direct", extract_html(raw))
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
        html = extract_html(raw)
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
            raise ValueError(f"Jev gate rejected candidate: contract={contract:.2f}, scope={scope:.2f}, quality={quality:.2f}")
        artifact_url = persist_artifact(run_id, "guided", html)
        update_lane(run_id, "guided", status="ready", tokens=tokens, artifact_url=artifact_url, detail=(
            f"Generated {tokens} tokens; Jev {plan_seconds + review_seconds:.2f}s; contract={contract:.2f}, scope={scope:.2f}, quality={quality:.2f}."))
    except Exception as exc:
        update_lane(run_id, "guided", status="failed", detail=str(exc))
    finish_run_if_complete(run_id)


def finish_run_if_complete(run_id: str) -> None:
    with LOCK:
        run = RUNS[run_id]
        if all(lane["status"] in {"ready", "failed"} for lane in run["lanes"].values()):
            run["status"] = "complete"


def create_run() -> dict:
    run_id = uuid.uuid4().hex
    now = time.perf_counter()
    run = {"id": run_id, "status": "running", "model": MODEL, "provider_url": WORKER_BASE_URL, "lanes": {
        lane: {"status": "queued", "detail": "Queued.", "elapsed_seconds": 0.0, "started_at": now, "tokens": 0}
        for lane in ("direct", "guided")
    }}
    with LOCK:
        RUNS[run_id] = run
    threading.Thread(target=run_direct, args=(run_id,), daemon=True).start()
    threading.Thread(target=run_guided, args=(run_id,), daemon=True).start()
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

    def do_POST(self):
        if self.path != "/api/runs":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_json(HTTPStatus.CREATED, create_run())

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
