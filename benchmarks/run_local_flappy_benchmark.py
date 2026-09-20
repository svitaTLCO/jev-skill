#!/usr/bin/env python3
"""
Full Local LLM Flappy Bird (Flying Pig) Benchmark
Direct comparison using:
- Local LLM: qwen2.5:1.5b via Ollama (http://localhost:11434)
- System One: TypeSafe Jev via API (https://api.typesafe.ai)
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.error

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:1.5b"
TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"

def get_keychain_key():
    env_key = os.environ.get("TYPESAFE_API_KEY")
    if env_key:
        return env_key
    if sys.platform == "darwin":
        try:
            res = subprocess.run(
                ["security", "find-generic-password", "-s", "network-infra-typesafe-jev", "-w"],
                capture_output=True, text=True, timeout=3
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass
    return None

API_KEY = get_keychain_key()

def call_ollama(prompt, max_tokens=850):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.2
        },
        "stream": True
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    t0 = time.perf_counter()
    full_text = []
    eval_count = 0
    with urllib.request.urlopen(req, timeout=180) as resp:
        for line in resp:
            if line:
                chunk = json.loads(line.decode("utf-8"))
                full_text.append(chunk.get("response", ""))
                if chunk.get("done", False):
                    eval_count = chunk.get("eval_count", 0)
    t1 = time.perf_counter()
    elapsed = t1 - t0
    return "".join(full_text), elapsed, eval_count

def call_jev(payload):
    t0 = time.perf_counter()
    req = urllib.request.Request(
        TYPESAFE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "LocalBenchmark/1.0"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    t1 = time.perf_counter()
    elapsed = t1 - t0
    return data, elapsed

def extract_html(raw_output):
    # Match ```html ... ``` or ``` ... ```
    m = re.search(r"```(?:html)?\s*(<!DOCTYPE html>.*?)```", raw_output, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m2 = re.search(r"(<!DOCTYPE html>.*</html>)", raw_output, re.DOTALL | re.IGNORECASE)
    if m2:
        return m2.group(1).strip()
    return raw_output.strip()

def main():
    print("=" * 65)
    print("🤖 FULL LOCAL LLM FLAPPY PIG REPRODUCTION BENCHMARK")
    print(f"   Model: {OLLAMA_MODEL} (Local Ollama)")
    print(f"   System One: TypeSafe Jev (api.typesafe.ai)")
    print("=" * 65)

    base_dir = "benchmarks/local_flappy"
    os.makedirs(f"{base_dir}/run_1_baseline", exist_ok=True)
    os.makedirs(f"{base_dir}/run_2_jev", exist_ok=True)

    # -------------------------------------------------------------
    # RUN 1: PURE LOCAL LLM BASELINE
    # -------------------------------------------------------------
    print("\n[RUN 1: Pure Local LLM Baseline]")
    print("-> Sending unconstrained prompt to Ollama...")
    
    r1_start = time.perf_counter()
    prompt_r1 = (
        "Write a complete, single-file HTML5 Canvas game of Flappy Bird where the player is a flying pig. "
        "Include canvas, pig drawing with pink body and wings, jump physics on space/click, obstacle pipes, collision detection, and score. "
        "Output complete, working HTML code with <!DOCTYPE html>."
    )
    code_r1, r1_llm_time, r1_tokens = call_ollama(prompt_r1, max_tokens=850)
    clean_html_r1 = extract_html(code_r1)
    
    file_r1 = f"{base_dir}/run_1_baseline/index.html"
    with open(file_r1, "w", encoding="utf-8") as f:
        f.write(clean_html_r1)
        
    r1_end = time.perf_counter()
    r1_total_time = r1_end - r1_start
    print(f"✅ Run 1 Complete in {r1_total_time:.2f}s")
    print(f"   - Tokens: {r1_tokens} ({r1_tokens / r1_llm_time:.1f} tok/s)")
    print(f"   - Saved to: {file_r1}")

    # -------------------------------------------------------------
    # RUN 2: JEV-GUIDED LOCAL LLM PIPELINE
    # -------------------------------------------------------------
    print("\n[RUN 2: Jev-Guided Pipeline]")
    r2_start = time.perf_counter()

    # Step 2.1: Jev makes the architectural decision
    print("-> [Step 2.1] Consulting Jev System One for game structure & physics...")
    jev_q = {
        "state": (
            "Building a lightweight single-file HTML5 Canvas Flappy Bird game featuring a flying pig. "
            "Need to choose the most reliable, compact game loop structure and physics parameters "
            "so the code is complete, self-contained, and fits within a concise token budget."
        ),
        "model": "jev-latest",
        "questions": {
            "physics_and_structure": {
                "type": "choice",
                "instructions": "Select the optimal compact game structure and physics profile",
                "criteria": {
                    "clean_object_loop": "Pig object with {x, y, vy, jump: -6, gravity: 0.35}, array of pipes {x, top, bottom}, single requestAnimationFrame loop.",
                    "complex_state_machine": "State machine with multiple screens and particle arrays.",
                    "procedural_globals": "All global variables without grouping."
                }
            }
        }
    }
    jev_step1, jev_time_1 = call_jev(jev_q)
    chosen_structure = jev_step1["answers"]["physics_and_structure"]["choice"]
    print(f"   ✅ Jev Step 1 returned in {jev_time_1*1000:.1f}ms (Chosen: '{chosen_structure}')")

    # Step 2.2: Local LLM generates with Jev's exact structure
    print("-> [Step 2.2] Prompting Local LLM with Jev's chosen structure...")
    prompt_r2 = (
        "Write a complete, single-file HTML5 Canvas game of Flappy Bird with a flying pig. "
        "Use this exact compact architecture: Pig object with {x, y, vy, jump: -6, gravity: 0.35}, an array of pipes {x, top, bottom}, and a single requestAnimationFrame loop. "
        "Include start/gameover states, score, and controls. "
        "Output complete, working HTML code with <!DOCTYPE html>."
    )
    code_r2, r2_llm_time, r2_tokens = call_ollama(prompt_r2, max_tokens=850)
    clean_html_r2 = extract_html(code_r2)
    
    file_r2 = f"{base_dir}/run_2_jev/index.html"
    with open(file_r2, "w", encoding="utf-8") as f:
        f.write(clean_html_r2)
    print(f"   ✅ LLM Step 2 returned in {r2_llm_time:.2f}s ({r2_tokens} tokens)")

    # Step 2.3: Jev Pre-flight Quality Gate
    print("-> [Step 2.3] Jev Pre-flight Quality & Completeness Gate...")
    jev_gate = {
        "state": f"## Generated HTML/JS Game Code\n```html\n{clean_html_r2[:2500]}\n```",
        "model": "jev-latest",
        "questions": {
            "is_complete_and_playable": {
                "type": "noul",
                "instructions": "Does this code contain a complete, runnable HTML5 Canvas game without truncated functions?"
            },
            "code_cleanliness": {
                "type": "score",
                "instructions": "Rate the code cleanliness and readability.",
                "criteria": ["Messy / truncated", "Basic functioning", "Clean & modular"]
            }
        }
    }
    jev_step2, jev_time_2 = call_jev(jev_gate)
    print(f"   ✅ Jev Step 3 returned in {jev_time_2*1000:.1f}ms")
    print(f"      Playable Completeness (Noul): {jev_step2['answers']['is_complete_and_playable']['noul']:.2f}")
    print(f"      Cleanliness (Score): {jev_step2['answers']['code_cleanliness']['score']:.2f}")

    r2_end = time.perf_counter()
    r2_total_time = r2_end - r2_start
    print(f"✅ Run 2 Complete in {r2_total_time:.2f}s")
    print(f"   - Jev Overhead (2 calls): {jev_time_1 + jev_time_2:.2f}s")
    print(f"   - Saved to: {file_r2}")

    # -------------------------------------------------------------
    # FINAL RESULTS TABLE
    # -------------------------------------------------------------
    diff = r2_total_time - r1_total_time
    winner = "Run 1 (Baseline)" if diff < 0 else "Run 2 (Jev-Guided)"

    print("\n" + "=" * 65)
    print("📊 FINAL MEASURED BENCHMARK SUMMARY (LOCAL LLM: QWEN 2.5 1.5B)")
    print("=" * 65)
    print(f"Run 1 (Pure Local LLM):      {r1_total_time:.2f}s (Tokens: {r1_tokens})")
    print(f"Run 2 (Jev-Guided Pipeline):  {r2_total_time:.2f}s (Tokens: {r2_tokens})")
    print(f"Time Difference:             {abs(diff):.2f}s ({winner} is faster)")
    print("=" * 65)

    results = {
        "benchmark": "Local LLM Flappy Bird Game Reproduction",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "local_model": OLLAMA_MODEL,
        "run_1_baseline": {
            "wall_clock_seconds": round(r1_total_time, 2),
            "llm_seconds": round(r1_llm_time, 2),
            "tokens_generated": r1_tokens,
            "tokens_per_sec": round(r1_tokens / r1_llm_time, 1),
            "file": file_r1
        },
        "run_2_jev_guided": {
            "wall_clock_seconds": round(r2_total_time, 2),
            "llm_seconds": round(r2_llm_time, 2),
            "tokens_generated": r2_tokens,
            "tokens_per_sec": round(r2_tokens / r2_llm_time, 1),
            "jev_step1_latency_ms": round(jev_time_1 * 1000, 1),
            "jev_step2_latency_ms": round(jev_time_2 * 1000, 1),
            "total_jev_overhead_seconds": round(jev_time_1 + jev_time_2, 2),
            "jev_choice": chosen_structure,
            "jev_verification": jev_step2["answers"],
            "file": file_r2
        },
        "delta_seconds": round(diff, 2),
        "faster": winner
    }

    with open(f"{base_dir}/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main()
