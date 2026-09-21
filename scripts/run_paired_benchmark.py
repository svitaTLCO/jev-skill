#!/usr/bin/env python3
"""Run a paired direct-versus-Jev evaluation with auditable, redacted records.

The runner deliberately supports Python micro-contracts only because that is the
only runtime for which this repository currently has an isolated oracle test
adapter.  It sends actual generation requests in both arms; it never substitutes
historical artifacts for either result.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:  # Supports both `python scripts/...` and package imports in tests.
    from scripts.jev_swarm import DEFAULT_TYPESAFE_URL, GenericRuntimeValidator, JevClient
except ModuleNotFoundError:  # pragma: no cover - exercised by the standalone container command
    from jev_swarm import DEFAULT_TYPESAFE_URL, GenericRuntimeValidator, JevClient


RUNNER_VERSION = 1
SAFE_TASK_ID = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class WorkerResponseError(RuntimeError):
    def __init__(self, message: str, metadata: dict | None = None):
        super().__init__(message)
        self.metadata = metadata or {}


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def git_revision() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=3
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except OSError:
        return None


def load_env_value(path: str, key: str) -> str | None:
    """Read one dotenv value without importing unrelated values into process env."""
    try:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key}="):
                value = line.split("=", 1)[1].strip().strip("'\"")
                return value or None
    except OSError:
        return None
    return None


def resolve_jev_client(url: str) -> JevClient:
    key = os.environ.get("TYPESAFE_API_KEY")
    if not key:
        secret_file = os.environ.get("JEV_PAIRED_TYPESAFE_ENV_FILE")
        if secret_file:
            key = load_env_value(secret_file, "TYPESAFE_API_KEY")
    return JevClient(api_key=key, url=url)


def extract_code(raw: str) -> str:
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)(?:```|$)", raw, re.DOTALL | re.IGNORECASE)
    return max((block.strip() for block in blocks if block.strip()), key=len, default=raw.strip())


def generate_ollama(worker_url: str, model: str, prompt: str, seed: int, max_tokens: int,
                    temperature: float, think: bool, timeout: int) -> tuple[str, dict, float]:
    payload = {
        "model": model,
        "prompt": prompt,
        "think": think,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
            "seed": seed,
        },
    }
    started = time.perf_counter()
    request = urllib.request.Request(
        worker_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    elapsed = time.perf_counter() - started
    raw = data.get("response")
    if not isinstance(raw, str) or not raw.strip():
        raise WorkerResponseError("Worker response did not contain a non-empty response string", {
            "done_reason": data.get("done_reason"),
            "eval_count": data.get("eval_count"),
        })
    return extract_code(raw), data, elapsed


def generate_openai(worker_url: str, model: str, prompt: str, max_tokens: int,
                    temperature: float, think: bool, timeout: int, api_key: str) -> tuple[str, dict, float]:
    if not api_key:
        raise RuntimeError("OpenAI-compatible worker requires a Galene API key")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "reasoning_effort": "high" if think else "none",
    }
    if not think:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    started = time.perf_counter()
    request = urllib.request.Request(
        worker_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    elapsed = time.perf_counter() - started
    choices = data.get("choices") or []
    usage = data.get("usage") or {}
    content = choices[0].get("message", {}).get("content") if choices else None
    if not isinstance(content, str) or not content.strip():
        details = usage.get("completion_tokens_details") if isinstance(usage, dict) else {}
        raise WorkerResponseError("OpenAI-compatible worker response did not contain completion content", {
            "request_id": data.get("id"),
            "finish_reason": choices[0].get("finish_reason") if choices else None,
            "completion_tokens": usage.get("completion_tokens") if isinstance(usage, dict) else None,
            "reasoning_tokens": details.get("reasoning_tokens") if isinstance(details, dict) else None,
        })
    data["eval_count"] = usage.get("completion_tokens")
    return extract_code(content), data, elapsed


def choose_implementation(client: JevClient, task: dict) -> tuple[dict, float]:
    questions = {
        "implementation_shape": {
            "type": "choice",
            "instructions": "Select the smallest implementation shape that meets this micro-contract. Do not add behavior beyond the stated requirement.",
            "criteria": {
                "minimal_pure_function": "One pure function, no helper functions, imports, classes, I/O, or mutable global state.",
                "single_explicit_loop": "One pure function with a single explicit loop when iteration is needed; no helpers, imports, classes, I/O, or mutable global state.",
            },
        }
    }
    answer, elapsed = client.evaluate(
        f"## Task\n{task['prompt']}\n\n## Tests are an oracle; do not infer extra requirements.\n{task['tests']}",
        questions,
    )
    choice = answer.get("implementation_shape", {})
    if choice.get("choice") not in questions["implementation_shape"]["criteria"]:
        raise RuntimeError("Jev returned an invalid implementation_shape choice")
    return choice, elapsed


def raw_path(raw_root: Path, run_id: str, arm: str, task_id: str, seed: int) -> Path:
    if not SAFE_TASK_ID.fullmatch(task_id):
        raise ValueError(f"Unsafe task id: {task_id!r}")
    path = raw_root / run_id / arm / f"{task_id}-seed-{seed}.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def run_arm(arm: str, task: dict, args: argparse.Namespace, run_id: str,
            raw_root: Path, jev: JevClient | None, worker_key: str | None) -> dict:
    record = {
        "arm": arm,
        "task_id": task["id"],
        "split": task["split"],
        "seed_requested": args.seed,
        "worker": {"provider": args.provider, "url": args.worker_url, "model": args.model, "think": args.think,
                   "max_tokens": args.max_tokens, "temperature": args.temperature},
        "status": "infrastructure_error",
    }
    prompt = task["prompt"]
    try:
        if arm == "guided":
            if jev is None:
                raise RuntimeError("Jev client is required for the guided arm")
            choice, choice_latency = choose_implementation(jev, task)
            record["jev"] = {
                "implementation_shape": choice.get("choice"),
                "latency_ms": round(choice_latency * 1000, 3),
            }
            prompt += "\n\nJev-selected implementation shape: " + choice["choice"] + ". Preserve the original scope exactly."

        if args.provider == "ollama":
            candidate, provider_response, elapsed = generate_ollama(
                args.worker_url, args.model, prompt, args.seed, args.max_tokens,
                args.temperature, args.think, args.timeout,
            )
        else:
            candidate, provider_response, elapsed = generate_openai(
                args.worker_url, args.model, prompt, args.max_tokens,
                args.temperature, args.think, args.timeout, worker_key or "",
            )
        destination = raw_path(raw_root, run_id, arm, task["id"], args.seed)
        destination.write_text(candidate + "\n", encoding="utf-8")
        passed, reason = GenericRuntimeValidator.validate_with_tests(
            candidate, task["tests"], task["language"]
        )
        provider_seed = provider_response.get("seed")
        record.update({
            "status": "completed",
            "passed": passed,
            "validation_reason": reason,
            "generation_latency_ms": round(elapsed * 1000, 3),
            "output_tokens": provider_response.get("eval_count"),
            "provider_seed": provider_seed if isinstance(provider_seed, int) else None,
            "provider_seed_confirmed": provider_seed == args.seed,
            "candidate_sha256": sha256(candidate),
            "raw_candidate_path": str(destination),
        })
    except Exception as exc:
        record["error_type"] = type(exc).__name__
        record["error"] = str(exc)[:500]
        if isinstance(exc, WorkerResponseError):
            record["provider_response_metadata"] = exc.metadata
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="benchmarks/evaluation_manifest.json")
    parser.add_argument("--provider", choices=("ollama", "openai"), default=os.environ.get("JEV_BENCHMARK_PROVIDER", "ollama"))
    parser.add_argument("--worker-url", default=os.environ.get("JEV_BENCHMARK_WORKER_URL") or os.environ.get("JEV_OLLAMA_URL", "http://host.docker.internal:11435/api/generate"))
    parser.add_argument("--model", required=True, help="Exact worker model identifier or digest")
    parser.add_argument("--seed", required=True, type=int, help="One seed per invocation; invoke repeatedly for paired seeds")
    parser.add_argument("--output-dir", default="benchmark-runs", help="Ignored directory for records and raw candidates")
    parser.add_argument("--max-tokens", type=int, default=1200)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--think", action="store_true", help="Enable worker thinking in both arms")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--typesafe-url", default=DEFAULT_TYPESAFE_URL)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_tokens <= 0 or args.timeout <= 0 or not 0.0 <= args.temperature <= 2.0:
        raise SystemExit("max-tokens/timeout must be positive and temperature must be between 0 and 2")
    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tasks = manifest.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise SystemExit("Manifest must contain at least one task")
    for task in tasks:
        required = {"id", "split", "language", "prompt", "tests"}
        if not required.issubset(task) or task["language"] not in {"python", "py"}:
            raise SystemExit("Paired runner supports only complete Python task manifests")

    output_dir = Path(args.output_dir)
    raw_root = output_dir / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"paired-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    jev = resolve_jev_client(args.typesafe_url)
    worker_key = None
    if args.provider == "openai":
        worker_key = os.environ.get("GALENE_API_KEY")
        if not worker_key:
            worker_file = os.environ.get("JEV_PAIRED_GALENE_ENV_FILE")
            if worker_file:
                worker_key = load_env_value(worker_file, "GALENE_API_KEY")
    records = []
    for task in tasks:
        records.append(run_arm("direct", task, args, run_id, raw_root, None, worker_key))
        records.append(run_arm("guided", task, args, run_id, raw_root, jev, worker_key))

    report = {
        "schema_version": RUNNER_VERSION,
        "run_id": run_id,
        "timestamp_utc": utc_now(),
        "git_revision": os.environ.get("JEV_GIT_REVISION") or git_revision(),
        "manifest_sha256": sha256(json.dumps(manifest, sort_keys=True)),
        "model": args.model,
        "cache_state_policy": "caller-controlled; record whether the worker/provider reports cache state externally",
        "records": records,
        "summary": {
            "completed": sum(record["status"] == "completed" for record in records),
            "passed": sum(record.get("passed", False) for record in records),
            "total": len(records),
        },
    }
    report_path = output_dir / f"{run_id}.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(report_path), "summary": report["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
