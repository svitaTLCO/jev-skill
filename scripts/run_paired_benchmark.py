#!/usr/bin/env python3
"""Run an auditable paired direct-versus-Jev evaluation.

The fixed corpus exercises Python functions, multi-file Python packages, and
standalone HTML in isolated runtime oracles. Both arms send live worker requests;
historical artifacts are never substituted for experimental results.
"""

import argparse
import ast
import hashlib
import json
import os
import posixpath
import random
import re
import socket
import subprocess
import tempfile
import time
import urllib.request
import urllib.error
from urllib.parse import urlsplit, urlunsplit
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:  # Supports both `python scripts/...` and package imports in tests.
    from scripts.jev_swarm import DEFAULT_TYPESAFE_URL, GenericRuntimeValidator, JevClient
except ModuleNotFoundError:  # pragma: no cover - exercised by the standalone container command
    from jev_swarm import DEFAULT_TYPESAFE_URL, GenericRuntimeValidator, JevClient


RUNNER_VERSION = 2
SAFE_TASK_ID = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class WorkerResponseError(RuntimeError):
    def __init__(self, message: str, metadata: dict | None = None):
        super().__init__(message)
        self.metadata = metadata or {}


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def source_hashes() -> dict[str, str]:
    return {
        "runner": sha256(Path(__file__).read_text(encoding="utf-8")),
        "jev_swarm": sha256(Path(__file__).with_name("jev_swarm.py").read_text(encoding="utf-8")),
        "browser_oracle": sha256(Path(__file__).with_name("browser_oracle.py").read_text(encoding="utf-8")),
    }


def read_resume_ledger(path: Path) -> tuple[dict, list[dict], list[dict]]:
    """Load a checkpointed run ledger, excluding non-arm event records."""
    entries = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not entries or entries[0].get("record_type") != "run_start":
        raise ValueError("resume ledger has no run_start record")
    if any(item.get("record_type") == "run_complete" for item in entries[1:]):
        raise ValueError("resume ledger is already complete")
    return (entries[0], [item for item in entries[1:] if "arm" in item],
            [item for item in entries[1:] if item.get("record_type") == "run_resume"])


def validate_resume_header(header: dict, expected: dict) -> None:
    mismatches = [key for key, value in expected.items() if header.get(key) != value]
    if mismatches:
        raise ValueError("resume ledger does not match this run configuration: " + ", ".join(mismatches))


def model_digest(worker_url: str, model: str, timeout: int) -> str:
    """Resolve the model tag to the immutable digest exposed by Ollama."""
    parsed = urlsplit(worker_url)
    tags_url = urlunsplit((parsed.scheme, parsed.netloc, "/api/tags", "", ""))
    request = urllib.request.Request(tags_url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        models = json.loads(response.read().decode("utf-8")).get("models", [])
    matches = [entry.get("digest") for entry in models if entry.get("name") == model]
    if len(matches) != 1 or not matches[0]:
        raise RuntimeError(f"Could not resolve a unique immutable digest for Ollama model {model!r}")
    return matches[0]


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


def _extract_html(raw: str) -> str:
    # Mirrors scripts/demo_server.py::extract_html; kept local to avoid importing the demo server.
    match = re.search(r"((?:<!doctype html[^>]*>\s*)?<html\b.*?</html>)", raw, re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError("model response did not contain a complete HTML document")
    return match.group(1).strip()


def generate_ollama(worker_url: str, model: str, prompt: str, seed: int,
                    temperature: float, think: bool, timeout: int) -> tuple[str, dict, float]:
    payload = {
        "model": model,
        "prompt": prompt,
        "think": think,
        "stream": False,
        "options": {"temperature": temperature, "seed": seed},
        "keep_alive": "30m",
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
    return raw, data, elapsed


def warm_worker(worker_url: str, model: str, timeout: int) -> dict:
    """Load the exact worker before timing either paired arm; no generation cap."""
    payload = {"model": model, "prompt": "Reply with READY.", "think": False,
               "stream": False, "options": {"temperature": 0, "seed": 0}, "keep_alive": "30m"}
    request = urllib.request.Request(worker_url, data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data.get("response"), str) or not data["response"].strip():
        raise RuntimeError("Ollama warm-up did not return content")
    return {"eval_count": data.get("eval_count"), "done_reason": data.get("done_reason")}


def choose_implementation(client: JevClient, task: dict) -> tuple[dict, float]:
    artifact_type = task.get("artifact_type", "python")
    if artifact_type == "html":
        criteria = {
            "semantic_single_page": "One standalone semantic HTML document with local inline behavior and no network dependencies.",
            "accessible_dom_controls": "Semantic, keyboard-accessible controls and a small DOM state transition, with no external dependencies.",
        }
    elif artifact_type == "python_package_json":
        criteria = {
            "small_package_boundary": "Use exactly the named Python package modules and preserve the import boundary required by the task.",
            "direct_module_exports": "Keep the required behavior in the specified modules and export only the requested package API.",
        }
    else:
        criteria = {
            "minimal_pure_function": "One pure function, no helper functions, imports, classes, I/O, or mutable global state.",
            "single_explicit_loop": "One pure function with a single explicit loop when iteration is needed; no helpers, imports, classes, I/O, or mutable global state.",
        }
    questions = {
        "implementation_shape": {
            "type": "choice",
            "instructions": "Select the smallest implementation shape that meets this micro-contract. Do not add behavior beyond the stated requirement.",
            "criteria": criteria,
        }
    }
    answer, elapsed = client.evaluate(
        f"## Task\n{task['prompt']}", questions,
    )
    choice = answer.get("implementation_shape", {})
    if choice.get("choice") not in criteria:
        raise RuntimeError("Jev returned an invalid implementation_shape choice")
    return choice, elapsed


def guided_worker_prompt(task_prompt: str, selected_shape: str) -> str:
    """Keep the guided treatment to Jev's selected implementation shape only."""
    return task_prompt + "\n\nJev-selected implementation shape: " + selected_shape + "."


def parse_file_map(raw: str) -> dict[str, str]:
    """Parse the multi-file JSON protocol and reject unsafe or malformed paths."""
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text, re.IGNORECASE)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("multi-file response did not contain a JSON object")
    payload = json.loads(text[start:end + 1])
    files = payload.get("files") if isinstance(payload, dict) else None
    if not isinstance(files, dict) or not files:
        raise ValueError("multi-file response must contain a non-empty files object")
    result = {}
    for name, content in files.items():
        if not isinstance(name, str) or not isinstance(content, str):
            raise ValueError("multi-file paths and contents must be strings")
        normalized = posixpath.normpath(name)
        if normalized in {".", ".."} or normalized.startswith("../") or name.startswith("/") or "\\" in name:
            raise ValueError(f"unsafe candidate path: {name!r}")
        result[normalized] = content
    return result


def _sandbox_mount_paths(tmp_path: Path) -> tuple[str, str]:
    host_parent = os.environ.get("JEV_SANDBOX_HOST_DIR")
    temp_parent = os.environ.get("JEV_SANDBOX_TMPDIR")
    if bool(host_parent) != bool(temp_parent):
        raise RuntimeError("JEV_SANDBOX_TMPDIR and JEV_SANDBOX_HOST_DIR must be configured together")
    host_mount = str(Path(host_parent) / tmp_path.name) if host_parent else str(tmp_path)
    return host_mount, str(tmp_path)


def _sandbox_temp_parent() -> str | None:
    temp_parent = os.environ.get("JEV_SANDBOX_TMPDIR")
    if temp_parent:
        Path(temp_parent).mkdir(parents=True, exist_ok=True)
    return temp_parent


def validate_python_package(files: dict[str, str], tests: str, timeout: int = 30) -> tuple[bool, str]:
    """Run a generated multi-file Python package and oracle in an isolated child container."""
    temp_parent = _sandbox_temp_parent()
    with tempfile.TemporaryDirectory(prefix="jev-package-", dir=temp_parent) as directory:
        root = Path(directory)
        for name, source in files.items():
            target = root.joinpath(*name.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source, encoding="utf-8")
        (root / "_oracle_tests.py").write_text(tests + "\n", encoding="utf-8")
        root.chmod(0o755)
        host_mount, _ = _sandbox_mount_paths(root)
        command = ["docker", "run", "--rm", "--network", "none", "--read-only",
                   "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m", "--pids-limit", "64",
                   "--memory", "256m", "--cpus", "1", "--cap-drop", "ALL",
                   "--security-opt", "no-new-privileges", "-e", "PYTHONDONTWRITEBYTECODE=1",
                   "-v", f"{host_mount}:/work:ro", "-w", "/work",
                   os.environ.get("JEV_SANDBOX_IMAGE", "python:3.11-alpine"),
                   "python", "_oracle_tests.py"]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return False, f"sandbox timeout after {timeout} seconds"
        except OSError as exc:
            return False, f"sandbox launch failed: {exc}"
        if result.returncode:
            detail = (result.stderr or result.stdout).strip()[:1000]
            return False, f"multi-file sandbox test failure: {detail}"
        return True, "multi-file package tests passed in isolated Docker sandbox"


def validate_browser_html(html: str, oracle: dict, timeout: int = 90) -> tuple[bool, str]:
    """Execute an HTML candidate in a network-disabled Playwright child container."""
    temp_parent = _sandbox_temp_parent()
    with tempfile.TemporaryDirectory(prefix="jev-browser-", dir=temp_parent) as directory:
        root = Path(directory)
        (root / "index.html").write_text(html, encoding="utf-8")
        (root / "oracle.json").write_text(json.dumps(oracle), encoding="utf-8")
        browser_oracle = Path(__file__).with_name("browser_oracle.py")
        (root / "browser_oracle.py").write_text(browser_oracle.read_text(encoding="utf-8"), encoding="utf-8")
        root.chmod(0o755)
        host_mount, _ = _sandbox_mount_paths(root)
        sandbox_image = os.environ.get("JEV_BROWSER_SANDBOX_IMAGE", "jev-skill-browser-sandbox:1.63.0")
        command = ["docker", "run", "--rm", "--init", "--network", "none", "--read-only",
                   "--tmpfs", "/tmp:rw,nosuid,size=512m", "--shm-size", "1g", "--pids-limit", "96",
                   "--memory", "2g", "--cpus", "2", "--cap-drop", "ALL",
                   "--security-opt", "no-new-privileges", "--user", "pwuser",
                   "-e", "PLAYWRIGHT_BROWSERS_PATH=/ms-playwright", "-e", "HOME=/tmp/pwuser",
                   "-v", f"{host_mount}:/work:ro", "-w", "/work", sandbox_image,
                   "python", "/work/browser_oracle.py"]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return False, f"browser sandbox timeout after {timeout} seconds"
        except OSError as exc:
            return False, f"browser sandbox launch failed: {exc}"
        if result.returncode:
            detail = (result.stderr or result.stdout).strip()[:1500]
            return False, f"browser oracle failed: {detail}"
        return True, result.stdout.strip()[:1500]


def check_constraints(source: str, constraints: dict | None) -> tuple[bool, str]:
    """Apply oracle-only structural checks that must never enter worker prompts."""
    if not constraints:
        return True, "no structural constraints"
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return False, f"structural check could not parse source: {exc.msg}"
    definitions = [node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    expected = constraints.get("top_level_functions")
    if expected is not None and definitions != expected:
        return False, f"top-level functions {definitions!r} do not match required {expected!r}"
    if constraints.get("forbid_imports") and any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(tree)):
        return False, "imports are forbidden"
    forbidden = set(constraints.get("forbidden_names", []))
    found = sorted({node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id in forbidden})
    if found:
        return False, f"forbidden names used: {found!r}"
    return True, "structural constraints passed"


def raw_path(raw_root: Path, run_id: str, arm: str, task_id: str, seed: int) -> Path:
    if not SAFE_TASK_ID.fullmatch(task_id):
        raise ValueError(f"Unsafe task id: {task_id!r}")
    path = raw_root / run_id / arm / f"{task_id}-seed-{seed}.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def candidate_suffix(task: dict) -> str:
    return {"python": ".py", "py": ".py", "python_package_json": ".json", "html": ".html"}.get(
        task.get("artifact_type", "python"), ".artifact")


def run_arm(arm: str, task: dict, args: argparse.Namespace, run_id: str,
            raw_root: Path, jev: JevClient | None, seed: int) -> dict:
    started = time.perf_counter()
    record = {
        "arm": arm,
        "task_id": task["id"],
        "split": task["split"],
        "scenario": task.get("scenario", "micro-contract"),
        "prompt_sha256": sha256(task["prompt"]),
        "visible_oracle_sha256": sha256(task.get("tests", "")),
        "hidden_oracle_sha256": sha256(task.get("hidden_tests", "") + json.dumps(task.get("browser_oracle", {}), sort_keys=True)),
        "evaluator": task.get("artifact_type", "python"),
        "seed_requested": seed,
        "worker": {"provider": args.provider, "url": args.worker_url, "model": args.model, "think": args.think,
                   "temperature": args.temperature, "output_limit": None},
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
            prompt = guided_worker_prompt(prompt, choice["choice"])

        raw_response, provider_response, elapsed = generate_ollama(
            args.worker_url, args.model, prompt, seed,
            args.temperature, args.think, args.timeout,
        )
        raw_destination = raw_path(raw_root, run_id, arm, task["id"], seed).with_suffix(".raw.txt")
        raw_destination.write_text(raw_response, encoding="utf-8")
        artifact_type = task.get("artifact_type", "python")
        constraints_ok, constraints_reason = True, "no structural constraints"
        visible_ok, visible_reason = True, "not applicable"
        hidden_ok, hidden_reason = True, "no hidden oracle"
        if artifact_type in {"python", "py"}:
            candidate = extract_code(raw_response)
            constraints_ok, constraints_reason = check_constraints(candidate, task.get("constraints"))
            visible_ok, visible_reason = GenericRuntimeValidator.validate_with_tests(
                candidate, task["tests"], task["language"])
            hidden_tests = task.get("hidden_tests", "")
            hidden_ok, hidden_reason = (GenericRuntimeValidator.validate_with_tests(
                candidate, hidden_tests, task["language"]) if hidden_tests else (True, "no hidden tests"))
            passed = constraints_ok and visible_ok and hidden_ok
        elif artifact_type == "python_package_json":
            files = parse_file_map(raw_response)
            required_files = set(task.get("required_files", []))
            if required_files and set(files) != required_files:
                constraints_ok = False
                constraints_reason = f"file set {sorted(files)} does not match required {sorted(required_files)}"
            else:
                constraints_reason = "required file set passed"
            candidate = json.dumps({"files": files}, ensure_ascii=False, sort_keys=True)
            visible_ok, visible_reason = validate_python_package(files, task["tests"], timeout=30)
            hidden_tests = task.get("hidden_tests", "")
            hidden_ok, hidden_reason = (validate_python_package(files, hidden_tests, timeout=30)
                                        if hidden_tests else (True, "no hidden tests"))
            passed = constraints_ok and visible_ok and hidden_ok
        elif artifact_type == "html":
            candidate = _extract_html(raw_response)
            constraints_ok, constraints_reason = True, "external requests checked by network-disabled browser oracle"
            browser_ok, browser_reason = validate_browser_html(candidate, task["browser_oracle"], timeout=90)
            visible_ok, visible_reason = browser_ok, browser_reason
            passed = constraints_ok and browser_ok
        else:
            raise ValueError(f"unsupported artifact_type: {artifact_type!r}")
        destination = raw_path(raw_root, run_id, arm, task["id"], seed).with_suffix(candidate_suffix(task))
        destination.write_text(candidate + "\n", encoding="utf-8")
        provider_seed = provider_response.get("seed")
        record.update({
            "status": "completed",
            "passed": passed,
            "visible_passed": visible_ok,
            "visible_reason": visible_reason,
            "hidden_passed": hidden_ok,
            "hidden_reason": hidden_reason,
            "constraints_passed": constraints_ok,
            "constraints_reason": constraints_reason,
            "generation_latency_ms": round(elapsed * 1000, 3),
            "jev_latency_ms": record.get("jev", {}).get("latency_ms", 0),
        "output_tokens": provider_response.get("eval_count"),
            "input_tokens": provider_response.get("prompt_eval_count"),
            "provider_seed": provider_seed if isinstance(provider_seed, int) else None,
            "provider_seed_confirmed": provider_seed == seed,
            "done_reason": provider_response.get("done_reason"),
            "truncated": provider_response.get("done_reason") == "length",
            "candidate_sha256": sha256(candidate),
            "raw_candidate_path": str(destination),
            "raw_response_path": str(raw_destination),
        })
    except Exception as exc:
        record["status"] = "failed"
        record["error_type"] = type(exc).__name__
        record["error"] = str(exc)[:500]
        if isinstance(exc, WorkerResponseError):
            record["failure_class"] = "generation"
            record["provider_response_metadata"] = exc.metadata
        elif isinstance(exc, (TimeoutError, socket.timeout)) or "timed out" in str(exc).lower():
            record["failure_class"] = "timeout"
        elif isinstance(exc, (ValueError, json.JSONDecodeError)):
            record["failure_class"] = "candidate_or_assembly"
        elif isinstance(exc, urllib.error.URLError):
            record["failure_class"] = "infrastructure"
        elif arm == "guided":
            record["failure_class"] = "jev_orchestration"
        else:
            record["failure_class"] = "infrastructure"
    record["wall_clock_ms"] = round((time.perf_counter() - started) * 1000, 3)
    return record


def percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def paired_summary(rows: list[dict], tasks: list[dict], seed_count: int) -> dict:
    pairs = {}
    for row in rows:
        pairs.setdefault((row["task_id"], row["seed_requested"]), {})[row["arm"]] = row
    completed_pairs = [pair for pair in pairs.values() if set(pair) == {"direct", "guided"}
                       and all(item["status"] == "completed" for item in pair.values())]
    direct_wall = [pair["direct"]["wall_clock_ms"] for pair in completed_pairs]
    guided_wall = [pair["guided"]["wall_clock_ms"] for pair in completed_pairs]
    differences = [int(pair["guided"].get("passed", False)) - int(pair["direct"].get("passed", False))
                   for pair in completed_pairs]
    if differences:
        rng = random.Random(94017)
        estimates = sorted(sum(rng.choices(differences, k=len(differences))) / len(differences)
                           for _ in range(10000))
        ci = [estimates[249], estimates[9749]]
    else:
        ci = None
    by_task = {}
    for task in tasks:
        task_pairs = [pair for pair in completed_pairs if pair["direct"]["task_id"] == task["id"]]
        task_diffs = [int(pair["guided"].get("passed", False)) - int(pair["direct"].get("passed", False))
                      for pair in task_pairs]
        if task_diffs:
            rng = random.Random(94017 + len(task["id"]))
            draws = sorted(sum(rng.choices(task_diffs, k=len(task_diffs))) / len(task_diffs)
                           for _ in range(10000))
            task_ci = [draws[249], draws[9749]]
        else:
            task_ci = None
        by_task[task["id"]] = {
            "paired_seeds_completed": len(task_pairs),
            "direct_passes": sum(pair["direct"].get("passed", False) for pair in task_pairs),
            "guided_passes": sum(pair["guided"].get("passed", False) for pair in task_pairs),
            "mean_paired_pass_delta_guided_minus_direct": sum(task_diffs) / len(task_diffs) if task_diffs else None,
            "bootstrap_95_ci_paired_pass_delta": task_ci,
            "direct_wall_ms_p50_p95": [percentile([pair["direct"]["wall_clock_ms"] for pair in task_pairs], p)
                                       for p in (0.5, 0.95)],
            "guided_wall_ms_p50_p95": [percentile([pair["guided"]["wall_clock_ms"] for pair in task_pairs], p)
                                       for p in (0.5, 0.95)],
        }
    return {
        "completed_pairs": len(completed_pairs),
        "requested_pairs": len(tasks) * seed_count,
        "mean_paired_pass_delta_guided_minus_direct": sum(differences) / len(differences) if differences else None,
        "bootstrap_95_ci_paired_pass_delta": ci,
        "direct_wall_ms_p50_p95": [percentile(direct_wall, p) for p in (0.5, 0.95)],
        "guided_wall_ms_p50_p95": [percentile(guided_wall, p) for p in (0.5, 0.95)],
        "infrastructure_errors": sum(row.get("failure_class") == "infrastructure" for row in rows),
        "generation_failures": sum(row.get("failure_class") == "generation" for row in rows),
        "candidate_or_assembly_failures": sum(row.get("failure_class") == "candidate_or_assembly" for row in rows),
        "jev_orchestration_failures": sum(row.get("failure_class") == "jev_orchestration" for row in rows),
        "timeouts": sum(row.get("failure_class") == "timeout"
                        or "timeout" in (row.get("visible_reason", "") + row.get("hidden_reason", "")).lower()
                        for row in rows),
        "truncations": sum(row.get("truncated", False) for row in rows),
        "retries": 0,
        "mean_worker_output_tokens": {
            arm: (sum(row.get("output_tokens", 0) or 0 for row in rows
                      if row["arm"] == arm and row["status"] == "completed") /
                  max(1, sum(row["arm"] == arm and row["status"] == "completed" for row in rows)))
            for arm in ("direct", "guided")
        },
        "mean_worker_input_tokens": {
            arm: (sum(row.get("input_tokens", 0) or 0 for row in rows
                      if row["arm"] == arm and row["status"] == "completed") /
                  max(1, sum(row["arm"] == arm and row["status"] == "completed" for row in rows)))
            for arm in ("direct", "guided")
        },
        "mean_generation_latency_ms": {
            arm: (sum(row.get("generation_latency_ms", 0) for row in rows
                      if row["arm"] == arm and row["status"] == "completed") /
                  max(1, sum(row["arm"] == arm and row["status"] == "completed" for row in rows)))
            for arm in ("direct", "guided")
        },
        "by_task": by_task,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="benchmarks/evaluation_manifest.json")
    parser.add_argument("--provider", choices=("ollama",), default="ollama")
    parser.add_argument("--worker-url", default=os.environ.get("JEV_BENCHMARK_WORKER_URL") or "http://host.docker.internal:11434/api/generate")
    parser.add_argument("--model", required=True, help="Exact worker model identifier or digest")
    parser.add_argument("--seed", type=int, default=1, help="First paired seed (default: 1)")
    parser.add_argument("--seed-count", type=int, default=20, help="Number of consecutive paired seeds (P0 requires at least 20)")
    parser.add_argument("--output-dir", default="benchmark-runs", help="Git-ignored directory for records and raw candidates")
    parser.add_argument("--resume-ledger", help="Resume an interrupted NDJSON ledger with the exact same run configuration")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--think", action="store_true", help="Enable worker thinking in both arms")
    parser.add_argument("--timeout", type=int, default=2400,
                        help="Wall-clock hang guard per worker request in seconds (queue wait plus full uncapped generation); never a content budget")
    parser.add_argument("--allow-directional", action="store_true",
                        help="Allow fewer than 20 paired seeds; such runs are directional evidence, not P0")
    parser.add_argument("--typesafe-url", default=DEFAULT_TYPESAFE_URL)
    return parser.parse_args()


def validate_p0_seed_floor(seed_count: int, allow_directional: bool) -> None:
    """Refuse under-powered P0 runs unless they are explicitly labeled directional."""
    if seed_count < 20 and not allow_directional:
        raise SystemExit(
            "P0 requires at least 20 paired seeds per task; pass --allow-directional for smaller directional probes"
        )


def main() -> int:
    args = parse_args()
    if args.seed_count <= 0 or args.timeout <= 0 or not 0.0 <= args.temperature <= 2.0:
        raise SystemExit("seed-count/timeout must be positive and temperature must be between 0 and 2")
    validate_p0_seed_floor(args.seed_count, args.allow_directional)
    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tasks = manifest.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise SystemExit("Manifest must contain at least one task")
    for task in tasks:
        required = {"id", "split", "language", "prompt", "tests"}
        artifact_type = task.get("artifact_type", "python")
        if (not required.issubset(task) or artifact_type not in {"python", "py", "python_package_json", "html"}
                or (artifact_type in {"python", "py", "python_package_json"} and task["language"] not in {"python", "py"})
                or (artifact_type == "html" and task["language"] != "html")):
            raise SystemExit(f"Incomplete or unsupported task manifest entry: {task.get('id')!r}")
    ids = [task["id"] for task in tasks]
    if len(ids) != len(set(ids)) or not {"development", "holdout"}.issubset({task["split"] for task in tasks}):
        raise SystemExit("Manifest task IDs must be unique and include development and holdout splits")

    output_dir = Path(args.output_dir)
    raw_root = output_dir / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)
    source_digest_map = source_hashes()
    manifest_digest = sha256(json.dumps(manifest, sort_keys=True))
    jev = resolve_jev_client(args.typesafe_url)
    resolved_digest = model_digest(args.worker_url, args.model, args.timeout)
    resume_events = []
    if args.resume_ledger:
        ledger_path = Path(args.resume_ledger)
        try:
            header, records, resume_events = read_resume_ledger(ledger_path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise SystemExit(f"Cannot resume ledger: {exc}")
        expected = {
            "runner_version": RUNNER_VERSION,
            "model": args.model,
            "model_digest": resolved_digest,
            "seed_start": args.seed,
            "seed_count": args.seed_count,
            "manifest_sha256": manifest_digest,
            "source_sha256": source_digest_map,
            "worker_url": args.worker_url,
            "provider": args.provider,
            "temperature": args.temperature,
            "think": args.think,
            "timeout": args.timeout,
            "typesafe_url": args.typesafe_url,
            "python_sandbox_image": os.environ.get("JEV_SANDBOX_IMAGE", "python:3.11-alpine"),
            "browser_sandbox_image": os.environ.get("JEV_BROWSER_SANDBOX_IMAGE", "jev-skill-browser-sandbox:1.63.0"),
            "output_dir": str(output_dir.resolve()),
        }
        try:
            validate_resume_header(header, expected)
        except ValueError as exc:
            raise SystemExit(str(exc))
        run_id = header["run_id"]
        existing = {}
        task_ids = set(ids)
        for row in records:
            key = (row.get("task_id"), row.get("seed_requested"), row.get("arm"))
            if (key[0] not in task_ids or key[1] not in range(args.seed, args.seed + args.seed_count)
                    or key[2] not in {"direct", "guided"} or key in existing):
                raise SystemExit(f"Resume ledger contains an invalid or duplicate arm key: {key!r}")
            existing[key] = row
        warmup = warm_worker(args.worker_url, args.model, args.timeout)
        resume_event = {"record_type": "run_resume", "timestamp_utc": utc_now(), "model_warmup": warmup}
        with ledger_path.open("a", encoding="utf-8") as ledger:
            ledger.write(json.dumps(resume_event, sort_keys=True) + "\n")
        resume_events.append(resume_event)
        print(json.dumps({"run_id": run_id, "resuming": str(ledger_path),
                          "completed_arms": len(records), "resume_count": len(resume_events)}), flush=True)
    else:
        run_id = f"paired-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
        ledger_path = output_dir / f"{run_id}.ndjson"
        existing = {}
        warmup = warm_worker(args.worker_url, args.model, args.timeout)
        header = {
            "record_type": "run_start",
            "run_id": run_id,
            "runner_version": RUNNER_VERSION,
            "model": args.model,
            "model_digest": resolved_digest,
            "seed_start": args.seed,
            "seed_count": args.seed_count,
            "manifest_sha256": manifest_digest,
            "source_sha256": source_digest_map,
            "worker_url": args.worker_url,
            "provider": args.provider,
            "temperature": args.temperature,
            "think": args.think,
            "timeout": args.timeout,
            "typesafe_url": args.typesafe_url,
            "python_sandbox_image": os.environ.get("JEV_SANDBOX_IMAGE", "python:3.11-alpine"),
            "browser_sandbox_image": os.environ.get("JEV_BROWSER_SANDBOX_IMAGE", "jev-skill-browser-sandbox:1.63.0"),
            "output_dir": str(output_dir.resolve()),
            "warmup": warmup,
            "evidence_class": "p0" if args.seed_count >= 20 else "directional",
        }
        with ledger_path.open("w", encoding="utf-8") as ledger:
            ledger.write(json.dumps(header, sort_keys=True) + "\n")
        records = []
    for task in tasks:
        for seed in range(args.seed, args.seed + args.seed_count):
            # Alternate order to balance warm-state/order effects across paired seeds.
            order = ("direct", "guided") if (seed - args.seed) % 2 == 0 else ("guided", "direct")
            for arm in order:
                key = (task["id"], seed, arm)
                if key in existing:
                    print(json.dumps({"run_id": run_id, "task": task["id"], "seed": seed,
                                      "arm": arm, "status": existing[key]["status"],
                                      "resumed": "skipped_existing"}), flush=True)
                    continue
                record = run_arm(arm, task, args, run_id, raw_root,
                                 jev if arm == "guided" else None, seed)
                records.append(record)
                existing[key] = record
                with ledger_path.open("a", encoding="utf-8") as ledger:
                    ledger.write(json.dumps(record, sort_keys=True) + "\n")
                print(json.dumps({"run_id": run_id, "task": task["id"], "seed": seed,
                                  "arm": arm, "status": record["status"],
                                  "passed": record.get("passed"),
                                  "wall_clock_ms": record.get("wall_clock_ms")}), flush=True)

    report = {
        "schema_version": RUNNER_VERSION,
        "run_id": run_id,
        "timestamp_utc": utc_now(),
        "git_revision": os.environ.get("JEV_GIT_REVISION") or git_revision(),
        "source_sha256": source_digest_map,
        "manifest_sha256": manifest_digest,
        "model": args.model,
        "model_digest": resolved_digest,
        "model_warmup": warmup,
        "resume_count": len(resume_events),
        "resume_warmups": [event["model_warmup"] for event in resume_events],
        "seed_range": [args.seed, args.seed + args.seed_count - 1],
        "evidence_class": "p0" if args.seed_count >= 20 else "directional",
        "pair_order_policy": "alternating direct-first/guided-first by seed to balance order effects",
        "cache_state_policy": "one uncaptured warm-up before measurements; Ollama keep_alive=30m for all requests; no prompt cache control is exposed",
        "generation_budget_policy": "uncapped; num_predict/max_tokens omitted from all worker requests",
        "cost_usd": None,
        "cost_note": "local GPU inference; electricity telemetry and Jev billing data are not captured by this runner",
        "records": records,
        "paired_analysis": paired_summary(records, tasks, args.seed_count),
        "summary": {
            "completed": sum(record["status"] == "completed" for record in records),
            "passed": sum(record.get("passed", False) for record in records),
            "total": len(records),
        },
    }
    report_path = output_dir / f"{run_id}.json"
    temporary_report = report_path.with_suffix(".json.tmp")
    temporary_report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    temporary_report.replace(report_path)
    with ledger_path.open("a", encoding="utf-8") as ledger:
        ledger.write(json.dumps({"record_type": "run_complete", "timestamp_utc": utc_now(),
                                 "report_path": str(report_path), "summary": report["summary"]},
                                sort_keys=True) + "\n")
    print(json.dumps({"report": str(report_path), "summary": report["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
