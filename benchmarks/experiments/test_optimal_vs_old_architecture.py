#!/usr/bin/env python3
"""
Final Empirical Validation: Optimal Architecture vs. Old Architecture Head-to-Head

Architecture Comparison:
-----------------------------------------------------------------------------------------------------------------
Configuration         | Tier 1 Agile Worker   | Tier 2 Deep Brain    | Reasoning Mode | Gating & Routing
-----------------------------------------------------------------------------------------------------------------
OLD ARCHITECTURE      | huihui-qwen3.5:0.8b   | huihui-qwen3.5:2b    | Thinking ON    | Monolithic / Generic
OPTIMAL ARCHITECTURE  | qwen3.5:2b            | qwen3.5:4b           | Thinking OFF   | Jev Guided + Tier 1/2
-----------------------------------------------------------------------------------------------------------------
"""

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.stdout.reconfigure(line_buffering=True)

from jev_swarm import JevSwarm, JevClient, GenericRuntimeValidator, DEFAULT_OLLAMA_URL

def query_ollama(model: str, prompt: str, think: bool = False, max_tokens: int = 1400) -> tuple[str, float, int]:
    system_prompt = (
        "/no_think\n"
        "You are an expert software engineer in an autonomous micro-swarm. "
        "Output ONLY clean, production-grade code enclosed in markdown fences (```python ... ```). "
        "Do NOT add conversational prose, explanations, or thinking monologues. "
        "Keep implementation minimal, focused, and strictly compliant with the prompt."
    ) if not think else (
        "You are an expert software engineer in an autonomous micro-swarm. "
        "Output clean, production-grade code enclosed in markdown fences. "
        "Keep implementation minimal and focused."
    )

    if think:
        chatml = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n<think>\n"
    else:
        chatml = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"

    payload = {
        "model": model,
        "prompt": chatml,
        "think": think,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.2
        },
        "stream": False
    }

    t0 = time.perf_counter()
    req = urllib.request.Request(
        DEFAULT_OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    elapsed = time.perf_counter() - t0
    raw = data.get("response", "")
    tokens = data.get("eval_count", 0)

    # Extract code from markdown fences
    after_think = raw.split("</think>")[-1] if "</think>" in raw else raw
    m = re.findall(r"```(?:[a-zA-Z0-9_-]+)?\s*\n?(.*?)(?:```|$)", after_think, re.DOTALL)
    valid_blocks = [b.strip() for b in m if b.strip()]
    code = max(valid_blocks, key=len) if valid_blocks else after_think.strip()
    return code, elapsed, tokens


def run_unit_test(code_str: str, test_snippet: str) -> tuple[bool, str]:
    full_script = f"{code_str}\n\n# --- AUTOMATED TEST SUITE ---\n{test_snippet}\n"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(full_script)
        tmp_path = f.name
    try:
        res = subprocess.run([sys.executable, tmp_path], capture_output=True, text=True, timeout=5)
        if res.returncode != 0:
            err = res.stderr.strip() or res.stdout.strip()
            return False, err
        return True, "All test assertions passed cleanly"
    finally:
        try: os.unlink(tmp_path)
        except Exception: pass


def evaluate_jev(swarm: JevSwarm, code: str, spec_instructions: str):
    eval_payload = {
        "state": f"## Code Under Review (Python)\n```python\n{code[:2500]}\n```",
        "model": "jev-latest",
        "questions": {
            "reference_integrity": {
                "type": "noul",
                "instructions": "Are all variables, imports, and methods defined and valid without scope errors?"
            },
            "spec_compliance": {
                "type": "noul",
                "instructions": spec_instructions
            },
            "code_quality": {
                "type": "score",
                "instructions": "Rate code elegance and correctness from 0 to 3",
                "range": [0, 3],
                "criteria": ["Broken", "Rough", "Clean modular", "Production-grade"]
            }
        }
    }
    ans, elapsed = swarm.jev.evaluate(eval_payload["state"], eval_payload["questions"])
    return {
        "ref": ans.get("reference_integrity", {}).get("noul", 0.0),
        "spec": ans.get("spec_compliance", {}).get("noul", 0.0),
        "score": ans.get("code_quality", {}).get("score", 0.0),
        "time": elapsed
    }


TASKS = [
    {
        "id": "M1_RATE_LIMITER",
        "name": "Module 1: Concurrency Rate Limiter",
        "tier": "agile",
        "prompt": (
            "Write a complete Python class `TokenBucket` for rate limiting with:\n"
            "- `__init__(self, capacity: int, refill_rate: float)`: initializes bucket with capacity and tokens-per-second refill rate.\n"
            "- `allow_request(self, tokens: int = 1) -> bool`: refills tokens based on elapsed time (`time.monotonic()`), "
            "caps at capacity, and consumes tokens if available. Thread-safe using `threading.Lock`.\n"
            "Output ONLY the complete class in a markdown block."
        ),
        "tests": """
import time
tb = TokenBucket(10, 10.0)
assert tb.allow_request(5) == True, "First 5 tokens failed"
assert tb.allow_request(5) == True, "Second 5 tokens failed"
assert tb.allow_request(1) == False, "Request over capacity should return False"
time.sleep(0.15)
assert tb.allow_request(1) == True, "Refilled token request failed"
print("M1_PASS")
""",
        "spec": "Does TokenBucket use time.monotonic() to refill tokens up to capacity, acquire threading.Lock, and consume tokens properly?"
    },
    {
        "id": "M2_LRU_CACHE",
        "name": "Module 2: Custom Eviction Cache",
        "tier": "deep",
        "prompt": (
            "Write a complete Python class `LRUCache` without using `functools` or `collections.OrderedDict`:\n"
            "- `__init__(self, capacity: int)`\n"
            "- `get(self, key: int) -> int`: returns value and marks as most recently used, or -1 if missing.\n"
            "- `put(self, key: int, value: int) -> None`: inserts/updates key-value, evicting the least recently used item if capacity exceeded.\n"
            "Output ONLY the complete class in a markdown block."
        ),
        "tests": """
cache = LRUCache(2)
cache.put(1, 1)
cache.put(2, 2)
assert cache.get(1) == 1, "Cache get(1) failed"
cache.put(3, 3) # evicts key 2
assert cache.get(2) == -1, "Eviction of LRU key 2 failed"
cache.put(4, 4) # evicts key 1
assert cache.get(1) == -1, "Eviction of LRU key 1 failed"
assert cache.get(3) == 3, "Get 3 failed"
assert cache.get(4) == 4, "Get 4 failed"
print("M2_PASS")
""",
        "spec": "Does LRUCache correctly evict the least recently used item on capacity overflow without OrderedDict?"
    },
    {
        "id": "M3_TOKEN_PARSER",
        "name": "Module 3: Quote-Aware Bracket State Machine",
        "tier": "deep",
        "prompt": (
            "Write a Python function `validate_nested_tokens(s: str) -> bool` that checks if parentheses (), brackets [], "
            "and braces {} are properly matched and closed in order. Also ignore any delimiters inside single quotes '...' or double quotes \"...\".\n"
            "Output ONLY the function in a markdown block."
        ),
        "tests": """
assert validate_nested_tokens("()") == True, "Simple () failed"
assert validate_nested_tokens("([{}])") == True, "Nested failed"
assert validate_nested_tokens("([)]") == False, "Mismatched order failed"
assert validate_nested_tokens("('(')") == True, "Delimiter inside single quotes should be ignored"
assert validate_nested_tokens('("]")') == True, "Delimiter inside double quotes should be ignored"
print("M3_PASS")
""",
        "spec": "Does validate_nested_tokens properly handle nested delimiters and ignore delimiters inside quotes?"
    }
]


def execute_suite(suite_name: str, agile_model: str, deep_model: str, think_mode: bool, swarm: JevSwarm):
    print("\n" + "=" * 80)
    print(f"🚀 EXECUTING: {suite_name.upper()}")
    print(f"   Agile Model: {agile_model} | Deep Brain: {deep_model} | Thinking Mode: {think_mode}")
    print("=" * 80)

    suite_results = []
    total_time = 0.0
    total_tokens = 0
    passed_count = 0

    for task in TASKS:
        model = agile_model if task["tier"] == "agile" else deep_model
        print(f"\n▶️ [{task['id']}] {task['name']} (Assigned to {model})")
        
        t0 = time.perf_counter()
        code, elapsed, tokens = query_ollama(model, task["prompt"], think=think_mode)
        total_time += elapsed
        total_tokens += tokens

        # Tier 1 Runtime Unit Test
        passed_test, test_err = run_unit_test(code, task["tests"])
        
        # Tier 2 Jev System One Quality Gate
        jev_res = evaluate_jev(swarm, code, task["spec"])
        
        status_str = "✅ PASS" if passed_test else "❌ FAIL"
        if passed_test:
            passed_count += 1

        print(f"   Result: {status_str} | {elapsed:.1f}s | {tokens} tok")
        print(f"   Jev Gate: Ref={jev_res['ref']:.2f} | Spec={jev_res['spec']:.2f} | Score={jev_res['score']:.2f}/3.0")
        if not passed_test:
            print(f"   [Error Detail]: {test_err.splitlines()[-1] if test_err else 'Unknown test error'}")

        suite_results.append({
            "task_id": task["id"],
            "passed": passed_test,
            "elapsed": elapsed,
            "tokens": tokens,
            "ref": jev_res["ref"],
            "spec": jev_res["spec"],
            "score": jev_res["score"]
        })

    avg_score = sum(r["score"] for r in suite_results) / len(suite_results)
    avg_spec = sum(r["spec"] for r in suite_results) / len(suite_results)

    return {
        "suite_name": suite_name,
        "total_time": total_time,
        "total_tokens": total_tokens,
        "pass_rate": f"{passed_count}/{len(TASKS)} ({passed_count/len(TASKS)*100:.0f}%)",
        "avg_score": avg_score,
        "avg_spec": avg_spec,
        "results": suite_results
    }


def main():
    swarm = JevSwarm(default_worker_model="qwen3.5:2b")
    print("*" * 80)
    print("🏆 HEAD-TO-HEAD VALIDATION: OPTIMAL ARCHITECTURE VS. OLD ARCHITECTURE")
    print("*" * 80)

    # 1. RUN OLD ARCHITECTURE (0.8B + 2B with Thinking Mode ON)
    old_summary = execute_suite(
        suite_name="Old Architecture (0.8B + 2B, Thinking ON)",
        agile_model="huihui-qwen3.5:0.8b",
        deep_model="huihui-qwen3.5:2b",
        think_mode=True,
        swarm=swarm
    )

    # 2. RUN OPTIMAL ARCHITECTURE (2B + 4B with Thinking Mode OFF)
    optimal_summary = execute_suite(
        suite_name="Optimal Architecture (2B + 4B, Thinking OFF)",
        agile_model="qwen3.5:2b",
        deep_model="qwen3.5:4b",
        think_mode=False,
        swarm=swarm
    )

    # PRINT FINAL COMPARATIVE SCORECARD
    print("\n" + "=" * 80)
    print("📊 FINAL COMPARATIVE SCORECARD")
    print("=" * 80)
    print(f"{'Metric':<30} | {'Old Architecture':<22} | {'Optimal Architecture':<22}")
    print("-" * 80)
    print(f"{'Models Deployed':<30} | {'0.8B + 2B (Think ON)':<22} | {'2B + 4B (Think OFF)':<22}")
    print(f"{'Test Pass Rate':<30} | {old_summary['pass_rate']:<22} | {optimal_summary['pass_rate']:<22}")
    print(f"{'Total Wall Time':<30} | {old_summary['total_time']:<6.1f}s                 | {optimal_summary['total_time']:<6.1f}s")
    print(f"{'Total Tokens Generated':<30} | {old_summary['total_tokens']:<6} tok               | {optimal_summary['total_tokens']:<6} tok")
    print(f"{'Avg Jev Quality Score':<30} | {old_summary['avg_score']:<4.2f} / 3.0             | {optimal_summary['avg_score']:<4.2f} / 3.0")
    print(f"{'Avg Jev Spec Compliance':<30} | {old_summary['avg_spec']:<4.2f}                   | {optimal_summary['avg_spec']:<4.2f}")
    print("=" * 80)


if __name__ == "__main__":
    main()
