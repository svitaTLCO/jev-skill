#!/usr/bin/env python3
"""
Empirical Benchmark 2: Testing Upgraded Harness Strategies for No-Think SLM
Verifies whether:
1. Prescriptive Diagnostics & Failing Test Cases allow No-Think models to heal successfully on retry.
2. Micro-Contract Decomposition allows No-Think models to achieve 1st-pass success on complex logic.
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

MODEL = "huihui-qwen3.5:2b"

def query_no_think(prompt: str, max_tokens: int = 1200, system: str = None) -> tuple[str, float, int]:
    system_prompt = system or (
        "/no_think\n"
        "You are an expert software engineer in an autonomous micro-swarm. "
        "Output ONLY clean, production-grade code enclosed in markdown fences (```python ... ```). "
        "Do NOT add conversational prose, explanations, or thinking monologues. "
        "Keep implementation minimal, focused, and strictly compliant with the prompt."
    )
    chatml = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
    payload = {
        "model": MODEL,
        "prompt": chatml,
        "think": False,
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
    with urllib.request.urlopen(req, timeout=90) as resp:
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
    """Runs code combined with unit test assertions to verify runtime behavioral correctness."""
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
    swarm = JevSwarm(default_worker_model=MODEL)
    print("=" * 75)
    print("🔬 UPGRADED HARNESS BENCHMARK: TESTING RESILIENCE WITHOUT THINKING")
    print("Evaluating: 1) Prescriptive Test Diagnostics on Retry, 2) Micro-Decomposition")
    print("=" * 75)

    # -------------------------------------------------------------
    # EXPERIMENT 1: Task 3 (Bracket Validator with Quotes)
    # Compare:
    # A) Baseline No-Think (Failed in previous test with Spec 0.37)
    # B) Prescriptive Diagnostic Retry (feeding exact failing assertion + directive)
    # C) Micro-Contract Decomposition (2 atomic micro-workers)
    # -------------------------------------------------------------
    print("\n" + "#" * 70)
    print("TEST 1: BRACKET VALIDATOR (Quote-aware State Machine)")
    print("#" * 70)

    task3_prompt = (
        "Write a Python function `validate_nested_tokens(s: str) -> bool` that checks if parentheses (), brackets [], "
        "and braces {} are properly matched and closed in order. Also ignore any delimiters inside single quotes '...' or double quotes \"...\".\n"
        "Output ONLY the function in a markdown block."
    )
    task3_tests = """
assert validate_nested_tokens("()") == True, "Simple () failed"
assert validate_nested_tokens("([{}])") == True, "Nested failed"
assert validate_nested_tokens("([)]") == False, "Mismatched order failed"
assert validate_nested_tokens("('(')") == True, "Delimiter inside quotes failed - should be ignored!"
assert validate_nested_tokens('("]")') == True, "Closing bracket inside quotes failed - should be ignored!"
print("TEST_SUITE_SUCCESS")
"""

    print("\n--- Sub-test 1.1: No-Think First Pass ---")
    code1, t1, tok1 = query_no_think(task3_prompt)
    pass_t1, err_t1 = run_unit_test(code1, task3_tests)
    jev1 = evaluate_jev(swarm, code1, "Does validate_nested_tokens correctly ignore delimiters inside single/double quotes and validate brackets?")
    print(f"Pass 1: {t1:.1f}s | {tok1} tok | Tests: {'PASS' if pass_t1 else 'FAIL'} | Jev Ref: {jev1['ref']:.2f} | Spec: {jev1['spec']:.2f}")
    if not pass_t1:
        print(f"   [Failing Test Trace]: {err_t1.splitlines()[-1] if err_t1 else 'None'}")

    print("\n--- Sub-test 1.2: Upgraded Prescriptive Self-Healing Retry ---")
    if not pass_t1:
        prescriptive_healing_prompt = (
            f"Your previous code failed with the following test failure:\n"
            f"ERROR: {err_t1}\n\n"
            f"DEFECTIVE CODE:\n```python\n{code1}\n```\n\n"
            f"PRESCRIPTIVE ALGORITHMIC DIRECTIVE:\n"
            f"- Delimiters inside quotes MUST be ignored.\n"
            f"- Iterate through characters while tracking quote state (e.g. `in_quote = None` or quote character).\n"
            f"- If you see a quote char (' or \") when not in quotes, enter quote mode.\n"
            f"- If you see the matching quote char while in quote mode, exit quote mode.\n"
            f"- While in quote mode, DO NOT push or pop from your bracket stack.\n\n"
            f"INSTRUCTION: Apply this fix. Return ONLY the complete, corrected Python code in markdown fences."
        )
        code_healed, t_h, tok_h = query_no_think(prescriptive_healing_prompt)
        pass_healed, err_healed = run_unit_test(code_healed, task3_tests)
        jev_h = evaluate_jev(swarm, code_healed, "Does validate_nested_tokens correctly ignore delimiters inside single/double quotes and validate brackets?")
        print(f"Healed Pass: {t_h:.1f}s | {tok_h} tok | Tests: {'PASS' if pass_healed else 'FAIL'} | Jev Ref: {jev_h['ref']:.2f} | Spec: {jev_h['spec']:.2f} | Score: {jev_h['score']:.2f}/3.0")
        if not pass_healed:
            print(f"   [Healed Fail Trace]: {err_healed.splitlines()[-1] if err_healed else 'None'}")
    else:
        print("First pass surprisingly passed tests!")

    print("\n--- Sub-test 1.3: Micro-Contract Decomposition Strategy ---")
    print("Step A: Worker 1 synthesizes `strip_quoted_contents(s: str) -> str`...")
    prompt_strip = (
        "Write a Python function `strip_quoted_contents(s: str) -> str` that replaces any characters inside "
        "single quotes '...' or double quotes \"...\" with spaces, preserving the rest of the string.\n"
        "Output ONLY the function in a markdown fence."
    )
    code_strip, ts, toks = query_no_think(prompt_strip)
    test_strip = """
assert strip_quoted_contents("hello 'world'") == "hello '     '", "Single quote failed"
assert strip_quoted_contents('a "bc" d') == 'a "  " d', "Double quote failed"
assert strip_quoted_contents("no quotes") == "no quotes", "No quote failed"
"""
    pass_strip, err_strip = run_unit_test(code_strip, test_strip)
    print(f"   Worker 1: {ts:.1f}s | {toks} tok | Unit Test: {'PASS' if pass_strip else 'FAIL'}")

    print("Step B: Worker 2 synthesizes `validate_clean_brackets(s: str) -> bool`...")
    prompt_brackets = (
        "Write a Python function `validate_clean_brackets(s: str) -> bool` that checks if parentheses (), brackets [], "
        "and braces {} in the string are properly matched and closed in order. Non-bracket characters are ignored.\n"
        "Output ONLY the function in a markdown fence."
    )
    code_brackets, tb, tokb = query_no_think(prompt_brackets)
    test_brackets = """
assert validate_clean_brackets("()") == True
assert validate_clean_brackets("([{}])") == True
assert validate_clean_brackets("([)]") == False
"""
    pass_brackets, err_brackets = run_unit_test(code_brackets, test_brackets)
    print(f"   Worker 2: {tb:.1f}s | {tokb} tok | Unit Test: {'PASS' if pass_brackets else 'FAIL'}")

    print("Step C: Compose atomic workers into `validate_nested_tokens`...")
    composed_code = f"{code_strip}\n\n{code_brackets}\n\ndef validate_nested_tokens(s: str) -> bool:\n    clean = strip_quoted_contents(s)\n    return validate_clean_brackets(clean)\n"
    pass_comp, err_comp = run_unit_test(composed_code, task3_tests)
    jev_comp = evaluate_jev(swarm, composed_code, "Does this modular implementation correctly ignore quoted delimiters and validate nested brackets?")
    print(f"   Composite Verification: Tests: {'PASS' if pass_comp else 'FAIL'} | Jev Ref: {jev_comp['ref']:.2f} | Spec: {jev_comp['spec']:.2f} | Score: {jev_comp['score']:.2f}/3.0")


    # -------------------------------------------------------------
    # EXPERIMENT 2: Task 2 (LRU Cache without OrderedDict)
    # Compare:
    # A) Baseline No-Think
    # B) Prescriptive Unit Test Healing (feeding exact eviction assertion failure)
    # -------------------------------------------------------------
    print("\n" + "#" * 70)
    print("TEST 2: LRU CACHE WITH CONCRETE UNIT TEST HARNESS")
    print("#" * 70)

    lru_prompt = (
        "Write a complete Python class `LRUCache` without using `functools` or `collections.OrderedDict`:\n"
        "- `__init__(self, capacity: int)`\n"
        "- `get(self, key: int) -> int`: returns value and marks as most recently used, or -1 if missing.\n"
        "- `put(self, key: int, value: int) -> None`: inserts/updates key-value, evicting the least recently used item if capacity exceeded.\n"
        "Output ONLY the complete class in a markdown block."
    )
    lru_tests = """
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
print("LRU_TEST_SUITE_SUCCESS")
"""

    print("\n--- Sub-test 2.1: No-Think First Pass ---")
    lru1_code, lru1_t, lru1_tok = query_no_think(lru_prompt)
    lru1_pass, lru1_err = run_unit_test(lru1_code, lru_tests)
    lru1_jev = evaluate_jev(swarm, lru1_code, "Does LRUCache correctly evict the least recently used item on capacity overflow?")
    print(f"Pass 1: {lru1_t:.1f}s | {lru1_tok} tok | Tests: {'PASS' if lru1_pass else 'FAIL'} | Jev Ref: {lru1_jev['ref']:.2f} | Spec: {lru1_jev['spec']:.2f}")

    if not lru1_pass:
        print(f"   [Failing Test Trace]: {lru1_err.splitlines()[-1] if lru1_err else 'None'}")
        print("\n--- Sub-test 2.2: Prescriptive Healing with Exact Traceback ---")
        lru_healing_prompt = (
            f"Your previous `LRUCache` implementation failed this test case:\n"
            f"ERROR: {lru1_err}\n\n"
            f"DEFECTIVE CODE:\n```python\n{lru1_code}\n```\n\n"
            f"PRESCRIPTIVE FIX DIRECTIVE:\n"
            f"- Ensure `get()` updates the access order so the accessed key becomes the most recently used.\n"
            f"- When `put()` exceeds capacity, evict the key that was accessed least recently.\n"
            f"- You can implement this using a standard dict and tracking access timestamps or a custom doubly-linked Node (prev, next).\n\n"
            f"INSTRUCTION: Return ONLY the corrected, fully working `LRUCache` class in markdown fences."
        )
        lru_healed_code, lru_ht, lru_htok = query_no_think(lru_healing_prompt)
        lru_h_pass, lru_h_err = run_unit_test(lru_healed_code, lru_tests)
        lru_h_jev = evaluate_jev(swarm, lru_healed_code, "Does LRUCache correctly evict the least recently used item on capacity overflow?")
        print(f"Healed Pass: {lru_ht:.1f}s | {lru_htok} tok | Tests: {'PASS' if lru_h_pass else 'FAIL'} | Jev Ref: {lru_h_jev['ref']:.2f} | Spec: {lru_h_jev['spec']:.2f} | Score: {lru_h_jev['score']:.2f}/3.0")
        if not lru_h_pass:
            print(f"   [Healed Fail Trace]: {lru_h_err.splitlines()[-1] if lru_h_err else 'None'}")
    else:
        print("LRU Cache passed unit tests on first pass!")

    print("\n" + "=" * 75)
    print("🏁 UPGRADED HARNESS EXPERIMENT COMPLETE")
    print("=" * 75)


if __name__ == "__main__":
    main()
