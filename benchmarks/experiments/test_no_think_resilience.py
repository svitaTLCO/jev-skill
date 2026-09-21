#!/usr/bin/env python3
"""
Empirical Benchmark: Testing Swarm Resilience with Thinking Disabled
Tests whether the harness, instructions, and self-healing loops are sufficient
to catch failures and heal/retry when SLM reasoning is turned off.
"""

import ast
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(line_buffering=True)

# Import existing swarm primitives
from jev_swarm import JevSwarm, JevClient, GenericRuntimeValidator, DEFAULT_OLLAMA_URL

MODEL = "huihui-qwen3.5:2b"

def query_ollama(prompt: str, think: bool = False, max_tokens: int = 1000, model: str = MODEL) -> tuple[str, float, int]:
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
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        elapsed = time.perf_counter() - t0
        raw = data.get("response", "")
        tokens = data.get("eval_count", 0)
    except Exception as e:
        elapsed = time.perf_counter() - t0
        return f"# ERROR: {e}", elapsed, 0

    # Extract code from markdown fences
    after_think = raw.split("</think>")[-1] if "</think>" in raw else raw
    import re
    m = re.findall(r"```(?:[a-zA-Z0-9_-]+)?\s*\n?(.*?)(?:```|$)", after_think, re.DOTALL)
    valid_blocks = [b.strip() for b in m if b.strip()]
    code = max(valid_blocks, key=len) if valid_blocks else after_think.strip()
    return code, elapsed, tokens


def run_benchmark():
    swarm = JevSwarm(default_worker_model=MODEL)
    print("=" * 70)
    print(f"🔬 EMPIRICAL TEST: NO-THINK SLM WITH JEV GOVERNANCE & RETRY HARNESS")
    print(f"Worker Model: {MODEL} | Supervisor: TypeSafe Jev System One")
    print("=" * 70)

    test_tasks = [
        {
            "id": "T1_TOKEN_BUCKET",
            "title": "Stateful Rate Limiter (Concurrency + Math)",
            "prompt": (
                "Write a complete Python class `TokenBucket` for rate limiting with:\n"
                "- `__init__(self, capacity: int, refill_rate: float)`: initializes bucket with capacity and tokens-per-second refill rate.\n"
                "- `allow_request(self, tokens: int = 1) -> bool`: refills tokens based on elapsed time (`time.monotonic()`), "
                "caps at capacity, and consumes tokens if available. Thread-safe using `threading.Lock`.\n"
                "Output ONLY the complete class in a markdown block."
            ),
            "spec": "Does TokenBucket use time.monotonic() to refill tokens up to capacity, acquire a threading.Lock, and consume tokens properly?"
        },
        {
            "id": "T2_LRU_CACHE",
            "title": "LRU Cache Implementation (Pointers / Dict)",
            "prompt": (
                "Write a complete Python class `LRUCache` without using `functools` or `collections.OrderedDict`:\n"
                "- `__init__(self, capacity: int)`\n"
                "- `get(self, key: int) -> int`: returns value and marks as most recently used, or -1 if missing.\n"
                "- `put(self, key: int, value: int) -> None`: inserts/updates key-value, evicting the least recently used item if capacity exceeded.\n"
                "Output ONLY the complete class in a markdown block."
            ),
            "spec": "Does LRUCache correctly evict the least recently used item on capacity overflow without using OrderedDict?"
        },
        {
            "id": "T3_BRACKET_VALIDATOR",
            "title": "Recursive / Stack Parsing Validator",
            "prompt": (
                "Write a Python function `validate_nested_tokens(s: str) -> bool` that checks if parentheses (), brackets [], "
                "and braces {} are properly matched and closed in order. Also ignore any characters inside single quotes '...' or double quotes \"...\".\n"
                "Output ONLY the function in a markdown block."
            ),
            "spec": "Does validate_nested_tokens properly handle nested delimiters and ignore delimiters inside quotes?"
        }
    ]

    results = []

    for task in test_tasks:
        print(f"\n▶️ Running Task: {task['id']} - {task['title']}")
        
        # 1. Test WITH THINKING (Baseline)
        print("   [Mode A: THINKING ON (Default)] Generating...")
        t0 = time.perf_counter()
        code_think, elapsed_think, tokens_think = query_ollama(task["prompt"], think=True, max_tokens=1200)
        valid_think, err_think = GenericRuntimeValidator.validate_code(code_think, lang="python")
        print(f"   -> Result: {elapsed_think:.1f}s | {tokens_think} tok | Syntax: {'PASS' if valid_think else 'FAIL'}")

        # 2. Test WITHOUT THINKING (Single Shot)
        print("   [Mode B: THINKING OFF (Single Shot)] Generating...")
        code_nothink, elapsed_nothink, tokens_nothink = query_ollama(task["prompt"], think=False, max_tokens=1200)
        valid_nothink, err_nothink = GenericRuntimeValidator.validate_code(code_nothink, lang="python")
        print(f"   -> Result: {elapsed_nothink:.1f}s | {tokens_nothink} tok | Syntax: {'PASS' if valid_nothink else 'FAIL'}")

        # Evaluate Jev Noul & Score for No-Think Single Shot
        eval_payload = {
            "state": f"## Code Under Review (Python)\n```python\n{code_nothink}\n```",
            "model": "jev-latest",
            "questions": {
                "reference_integrity": {
                    "type": "noul",
                    "instructions": "Are all variables, imports, and methods defined and valid?"
                },
                "spec_compliance": {
                    "type": "noul",
                    "instructions": task["spec"]
                },
                "no_scope_creep": {
                    "type": "noul",
                    "instructions": "Does this code strictly stay within bounds without inventing unasked extra methods?"
                },
                "code_quality": {
                    "type": "score",
                    "instructions": "Rate code elegance and correctness from 0 to 3",
                    "range": [0, 3],
                    "criteria": ["Broken", "Rough", "Clean modular", "Production-grade"]
                }
            }
        }
        ans_b, t_jev_b = swarm.jev.evaluate(eval_payload["state"], eval_payload["questions"])
        ref_b = ans_b.get("reference_integrity", {}).get("noul", 0.0)
        spec_b = ans_b.get("spec_compliance", {}).get("noul", 0.0)
        score_b = ans_b.get("code_quality", {}).get("score", 0.0)
        pass_b = valid_nothink and (ref_b >= 0.70) and (spec_b >= 0.70)

        print(f"   -> Jev Gate: Ref={ref_b:.2f} | Spec={spec_b:.2f} | Score={score_b:.2f}/3.0 | Passed={pass_b}")

        # 3. Test WITHOUT THINKING + HARNESS RETRY / SELF-HEALING (if needed, or verify recovery)
        healed = False
        final_code = code_nothink
        final_elapsed = elapsed_nothink
        final_tokens = tokens_nothink

        if not pass_b:
            print("   ⚠️ Mode B did not pass all gates. Testing Harness Self-Healing / Targeted Retry...")
            retry_reason = err_nothink if not valid_nothink else (
                f"Failed Jev Spec: {task['spec']} (Spec compliance was {spec_b:.2f} < 0.70, Ref was {ref_b:.2f})"
            )
            healing_prompt = (
                f"Your previous code had the following defect:\n"
                f"DEFECT: {retry_reason}\n\n"
                f"PREVIOUS CODE:\n```python\n{code_nothink}\n```\n\n"
                f"TASK SPEC:\n{task['prompt']}\n\n"
                f"INSTRUCTION: Fix the defect. Output ONLY the complete, corrected Python code in markdown fences. Do NOT include thinking or commentary."
            )
            h_code, h_el, h_tok = query_ollama(healing_prompt, think=False, max_tokens=1200)
            final_elapsed += h_el
            final_tokens += h_tok
            h_valid, h_err = GenericRuntimeValidator.validate_code(h_code, lang="python")

            if h_valid:
                eval_h = {
                    "state": f"## Healed Code Under Review\n```python\n{h_code}\n```",
                    "model": "jev-latest",
                    "questions": eval_payload["questions"]
                }
                ans_h, _ = swarm.jev.evaluate(eval_h["state"], eval_h["questions"])
                h_ref = ans_h.get("reference_integrity", {}).get("noul", 0.0)
                h_spec = ans_h.get("spec_compliance", {}).get("noul", 0.0)
                h_score = ans_h.get("code_quality", {}).get("score", 0.0)
                h_passed = (h_ref >= 0.70) and (h_spec >= 0.70)
                print(f"   -> Healed Jev Gate: Ref={h_ref:.2f} | Spec={h_spec:.2f} | Score={h_score:.2f} | Passed={h_passed}")
                if h_passed:
                    healed = True
                    final_code = h_code
        else:
            print("   ✅ Passed Tier 1 and Tier 2 on first attempt without thinking!")

        # 4. Test ARENA (2 Candidates without thinking)
        print("   [Mode C: THINKING OFF + 2-Candidate Arena] Generating 2 candidates in parallel...")
        with ThreadPoolExecutor(max_workers=2) as ex:
            f1 = ex.submit(query_ollama, task["prompt"], False, 1200)
            f2 = ex.submit(query_ollama, task["prompt"], False, 1200)
            c1_code, c1_t, c1_tok = f1.result()
            c2_code, c2_t, c2_tok = f2.result()
        arena_wall_t = max(c1_t, c2_t)
        
        # Jev Choice between Arena candidates
        arena_payload = {
            "state": f"## Task Specification\n{task['prompt']}\n\n### Candidate 1\n```python\n{c1_code}\n```\n\n### Candidate 2\n```python\n{c2_code}\n```",
            "model": "jev-latest",
            "questions": {
                "winning_candidate": {
                    "type": "choice",
                    "instructions": "Select the candidate with superior implementation correctness and cleanliness:",
                    "criteria": {"candidate_1": "Candidate 1 is superior", "candidate_2": "Candidate 2 is superior"}
                }
            }
        }
        ans_arena, _ = swarm.jev.evaluate(arena_payload["state"], arena_payload["questions"])
        winner = ans_arena.get("winning_candidate", {}).get("choice", "candidate_1")
        winning_code = c1_code if winner == "candidate_1" else c2_code
        print(f"   -> Arena Wall Time: {arena_wall_t:.1f}s | Promoted: {winner}")

        results.append({
            "task": task["id"],
            "think_time": elapsed_think,
            "think_tokens": tokens_think,
            "think_syntax": valid_think,
            "nothink_time": elapsed_nothink,
            "nothink_tokens": tokens_nothink,
            "nothink_passed_first": pass_b,
            "nothink_healed": healed,
            "arena_time": arena_wall_t,
            "score": score_b
        })

    print("\n" + "=" * 70)
    print("📊 BENCHMARK SUMMARY & EMPIRICAL FINDINGS")
    print("=" * 70)
    print(f"{'Task':<22} | {'Think Mode':<16} | {'No-Think Mode':<16} | {'Harness Recovered?':<18} | {'Arena Time':<10}")
    print("-" * 90)
    for r in results:
        status_recovery = "N/A (Passed 1st)" if r["nothink_passed_first"] else ("YES (Healed)" if r["nothink_healed"] else "NO")
        print(f"{r['task']:<22} | {r['think_time']:<5.1f}s ({r['think_tokens']:<4} tok) | {r['nothink_time']:<5.1f}s ({r['nothink_tokens']:<4} tok) | {status_recovery:<18} | {r['arena_time']:<5.1f}s")
    print("=" * 70)

if __name__ == "__main__":
    run_benchmark()
