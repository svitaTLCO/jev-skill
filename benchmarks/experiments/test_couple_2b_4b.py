#!/usr/bin/env python3
"""
Benchmark: Evaluating the 2B - 4B Model Couple
Tier 1 Agile Worker: `qwen3.5:2b` (Speed, API contracts, Concurrency)
Tier 2 Deep Brain: `qwen3.5:4b` (Complex State Machines, Data Structures, Algorithms)
Supervisor: TypeSafe Jev System One
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

MODEL_2B = "qwen3.5:2b"
MODEL_4B = "qwen3.5:4b"

def query_model(model: str, prompt: str, think: bool = False, max_tokens: int = 1400) -> tuple[str, float, int]:
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
        "state": f"## Code Under Review (Python)\n```python\n{code}\n```",
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


def main():
    swarm = JevSwarm(default_worker_model=MODEL_2B)
    print("=" * 75)
    print(f"🔬 HETEROGENEOUS SWARM BENCHMARK: COUPLE 2B (`{MODEL_2B}`) + 4B (`{MODEL_4B}`)")
    print("Evaluating Cognitive Division: 2B (Agile Contracts) + 4B (Complex Logic)")
    print("=" * 75)

    # -------------------------------------------------------------
    # 1. AGILE WORKER (2B): TOKEN BUCKET
    # -------------------------------------------------------------
    print("\n" + "#" * 65)
    print("PHASE 1: AGILE WORKER (2B) -> TOKEN BUCKET (Concurrency + Math)")
    print("#" * 65)
    t1_prompt = (
        "Write a complete Python class `TokenBucket` for rate limiting with:\n"
        "- `__init__(self, capacity: int, refill_rate: float)`: initializes bucket with capacity and tokens-per-second refill rate.\n"
        "- `allow_request(self, tokens: int = 1) -> bool`: refills tokens based on elapsed time (`time.monotonic()`), "
        "caps at capacity, and consumes tokens if available. Thread-safe using `threading.Lock`.\n"
        "Output ONLY the complete class in a markdown block."
    )
    t1_tests = """
import time
tb = TokenBucket(10, 10.0)
assert tb.allow_request(5) == True, "First 5 failed"
assert tb.allow_request(5) == True, "Next 5 failed"
assert tb.allow_request(1) == False, "Over-capacity request should fail"
time.sleep(0.15)
assert tb.allow_request(1) == True, "Refill after sleep failed"
print("TOKEN_BUCKET_SUCCESS")
"""
    c1, t1, tok1 = query_model(MODEL_2B, t1_prompt, think=False)
    p1, err1 = run_unit_test(c1, t1_tests)
    j1 = evaluate_jev(swarm, c1, "Does TokenBucket correctly refill tokens and acquire threading.Lock?")
    print(f"2B Worker [No-Think]: {t1:.1f}s | {tok1} tok | Tests: {'PASS' if p1 else 'FAIL'} | Jev Ref: {j1['ref']:.2f} | Spec: {j1['spec']:.2f} | Score: {j1['score']:.2f}/3.0")

    # -------------------------------------------------------------
    # 2. DEEP BRAIN (4B): LRU CACHE (Custom Without OrderedDict)
    # -------------------------------------------------------------
    print("\n" + "#" * 65)
    print("PHASE 2: DEEP BRAIN (4B) -> LRU CACHE (Custom Doubly-Linked / Hash)")
    print("#" * 65)
    t2_prompt = (
        "Write a complete Python class `LRUCache` without using `functools` or `collections.OrderedDict`:\n"
        "- `__init__(self, capacity: int)`\n"
        "- `get(self, key: int) -> int`: returns value and marks as most recently used, or -1 if missing.\n"
        "- `put(self, key: int, value: int) -> None`: inserts/updates key-value, evicting the least recently used item if capacity exceeded.\n"
        "Output ONLY the complete class in a markdown block."
    )
    t2_tests = """
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
print("LRU_SUCCESS")
"""
    print("-> Testing 4B [No-Think] on LRU Cache...")
    c2_nt, t2_nt, tok2_nt = query_model(MODEL_4B, t2_prompt, think=False)
    p2_nt, err2_nt = run_unit_test(c2_nt, t2_tests)
    j2_nt = evaluate_jev(swarm, c2_nt, "Does LRUCache evict least recently used item properly without OrderedDict?")
    print(f"   4B [No-Think]: {t2_nt:.1f}s | {tok2_nt} tok | Tests: {'PASS' if p2_nt else 'FAIL'} | Jev Ref: {j2_nt['ref']:.2f} | Spec: {j2_nt['spec']:.2f}")
    if not p2_nt:
        print(f"   [4B No-Think Error]: {err2_nt.splitlines()[-1] if err2_nt else ''}")

    print("-> Testing 4B [Thinking Mode] on LRU Cache...")
    c2_th, t2_th, tok2_th = query_model(MODEL_4B, t2_prompt, think=True)
    p2_th, err2_th = run_unit_test(c2_th, t2_tests)
    j2_th = evaluate_jev(swarm, c2_th, "Does LRUCache evict least recently used item properly without OrderedDict?")
    print(f"   4B [Think Mode]: {t2_th:.1f}s | {tok2_th} tok | Tests: {'PASS' if p2_th else 'FAIL'} | Jev Ref: {j2_th['ref']:.2f} | Spec: {j2_th['spec']:.2f} | Score: {j2_th['score']:.2f}/3.0")
    if not p2_th:
        print(f"   [4B Think Error]: {err2_th.splitlines()[-1] if err2_th else ''}")

    # -------------------------------------------------------------
    # 3. DEEP BRAIN (4B): QUOTE-AWARE BRACKET VALIDATOR
    # -------------------------------------------------------------
    print("\n" + "#" * 65)
    print("PHASE 3: DEEP BRAIN (4B) -> QUOTE-AWARE BRACKET VALIDATOR")
    print("#" * 65)
    t3_prompt = (
        "Write a Python function `validate_nested_tokens(s: str) -> bool` that checks if parentheses (), brackets [], "
        "and braces {} are properly matched and closed in order. Also ignore any delimiters inside single quotes '...' or double quotes \"...\".\n"
        "Output ONLY the function in a markdown block."
    )
    t3_tests = """
assert validate_nested_tokens("()") == True, "Simple () failed"
assert validate_nested_tokens("([{}])") == True, "Nested failed"
assert validate_nested_tokens("([)]") == False, "Mismatched order failed"
assert validate_nested_tokens("('(')") == True, "Delimiter inside quotes failed - should be ignored!"
assert validate_nested_tokens('("]")') == True, "Closing bracket inside quotes failed - should be ignored!"
print("BRACKET_SUCCESS")
"""
    print("-> Testing 4B [No-Think] on Bracket Validator...")
    c3_nt, t3_nt, tok3_nt = query_model(MODEL_4B, t3_prompt, think=False)
    p3_nt, err3_nt = run_unit_test(c3_nt, t3_tests)
    j3_nt = evaluate_jev(swarm, c3_nt, "Does validate_nested_tokens correctly ignore quoted delimiters?")
    print(f"   4B [No-Think]: {t3_nt:.1f}s | {tok3_nt} tok | Tests: {'PASS' if p3_nt else 'FAIL'} | Jev Ref: {j3_nt['ref']:.2f} | Spec: {j3_nt['spec']:.2f}")
    if not p3_nt:
        print(f"   [4B No-Think Error]: {err3_nt.splitlines()[-1] if err3_nt else ''}")

    print("-> Testing 4B [Thinking Mode] on Bracket Validator...")
    c3_th, t3_th, tok3_th = query_model(MODEL_4B, t3_prompt, think=True)
    p3_th, err3_th = run_unit_test(c3_th, t3_tests)
    j3_th = evaluate_jev(swarm, c3_th, "Does validate_nested_tokens correctly ignore quoted delimiters?")
    print(f"   4B [Think Mode]: {t3_th:.1f}s | {tok3_th} tok | Tests: {'PASS' if p3_th else 'FAIL'} | Jev Ref: {j3_th['ref']:.2f} | Spec: {j3_th['spec']:.2f} | Score: {j3_th['score']:.2f}/3.0")
    if not p3_th:
        print(f"   [4B Think Error]: {err3_th.splitlines()[-1] if err3_th else ''}")

    print("\n" + "=" * 75)
    print("🏁 BENCHMARK COMPLETE FOR COUPLE 2B + 4B")
    print("=" * 75)


if __name__ == "__main__":
    main()
