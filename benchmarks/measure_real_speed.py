#!/usr/bin/env python3
"""
Real, Un-estimated Benchmark:
Direct LLM (Ollama) vs Jev-Guided LLM Pipeline
Measures exact wall-clock execution time down to the millisecond using time.perf_counter().
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:1.5b"
TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"

def get_typesafe_key():
    try:
        res = subprocess.run(
            ["security", "find-generic-password", "-s", "network-infra-typesafe-jev", "-w"],
            capture_output=True, text=True, timeout=3
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return os.environ.get("TYPESAFE_API_KEY")

API_KEY = get_typesafe_key()

def call_ollama(prompt):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    t0 = time.perf_counter()
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    t1 = time.perf_counter()
    elapsed = t1 - t0
    return data.get("response", ""), elapsed, data

def call_jev(payload):
    t0 = time.perf_counter()
    req = urllib.request.Request(
        TYPESAFE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "RealSpeedTest/1.0"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    t1 = time.perf_counter()
    elapsed = t1 - t0
    return data, elapsed

def main():
    print("=" * 60)
    print("🔬 SCIENTIFIC WALL-CLOCK SPEED BENCHMARK (ZERO ESTIMATES)")
    print("=" * 60)
    print(f"Local LLM: {OLLAMA_MODEL} on {OLLAMA_URL}")
    print(f"System One: Jev (api.typesafe.ai) via macOS Keychain")
    print("=" * 60)

    task_spec = (
        "Write a complete, single-file HTML5 Canvas game of Flappy Bird with a flying pig character. "
        "Include jump physics on space/click, pipe generation, collision detection, and score tracking."
    )

    # ----------------------------------------------------
    # RUN 1: PURE LLM BASELINE
    # ----------------------------------------------------
    print("\n⏱️  [STARTING RUN 1: Pure LLM Baseline]")
    run1_wall_start = time.perf_counter()

    prompt_run1 = (
        f"You are an expert game developer. {task_spec}\n"
        "Return ONLY the complete, working HTML code inside ```html ... ```."
    )
    code_run1, llm_time_run1, raw_run1 = call_ollama(prompt_run1)

    # Save to disk
    os.makedirs("benchmarks/measured_runs/run_1", exist_ok=True)
    with open("benchmarks/measured_runs/run_1/game.html", "w", encoding="utf-8") as f:
        f.write(code_run1)

    run1_wall_end = time.perf_counter()
    run1_total_time = run1_wall_end - run1_wall_start
    print(f"✅ RUN 1 Finished in: {run1_total_time:.3f} seconds")
    print(f"   - LLM Generation: {llm_time_run1:.3f}s")
    print(f"   - Tokens Generated: {raw_run1.get('eval_count', 0)}")
    print(f"   - Generation Speed: {raw_run1.get('eval_count', 0) / llm_time_run1:.1f} tokens/sec")

    # ----------------------------------------------------
    # RUN 2: JEV-GUIDED PIPELINE
    # ----------------------------------------------------
    print("\n⏱️  [STARTING RUN 2: Jev-Guided Pipeline]")
    run2_wall_start = time.perf_counter()

    # Step 2.1: Jev selects optimal architecture
    print("   -> [Step 2.1] Querying Jev System One for architecture choice...")
    jev_decision_payload = {
        "state": task_spec,
        "model": "jev-latest",
        "questions": {
            "physics_and_canvas_pattern": {
                "type": "choice",
                "instructions": "Select the optimal minimal implementation pattern for a responsive canvas arcade game.",
                "criteria": {
                    "minimal_class_loop": "Object-oriented Pig and Pipe classes inside single requestAnimationFrame loop.",
                    "flat_procedural": "Flat variables with procedural update functions.",
                    "complex_subsystems": "Separated manager instances with event emitter bus."
                }
            }
        }
    }
    jev_step1_data, jev_step1_time = call_jev(jev_decision_payload)
    chosen_pattern = jev_step1_data["answers"]["physics_and_canvas_pattern"]["choice"]
    print(f"   -> Jev Step 1 returned in: {jev_step1_time:.3f}s (Chosen: '{chosen_pattern}')")

    # Step 2.2: LLM generates with Jev's chosen constraint (removes ambiguity)
    print("   -> [Step 2.2] Querying LLM with Jev-guided pattern...")
    prompt_run2 = (
        f"You are an expert game developer. {task_spec}\n"
        f"Architecture requirement: Use the '{chosen_pattern}' pattern.\n"
        "Return ONLY the complete, working HTML code inside ```html ... ```."
    )
    code_run2, llm_time_run2, raw_run2 = call_ollama(prompt_run2)

    # Save to disk
    os.makedirs("benchmarks/measured_runs/run_2", exist_ok=True)
    with open("benchmarks/measured_runs/run_2/game.html", "w", encoding="utf-8") as f:
        f.write(code_run2)

    # Step 2.3: Jev Pre-flight Quality Gate
    print("   -> [Step 2.3] Jev Pre-flight Verification Gate...")
    jev_gate_payload = {
        "state": f"## Task\n{task_spec}\n\n## Code\n```html\n{code_run2[:3000]}\n```",
        "model": "jev-latest",
        "questions": {
            "is_valid_html_canvas": {
                "type": "noul",
                "instructions": "Does this code contain a valid HTML5 canvas game with game loop and event listeners?"
            },
            "code_quality": {
                "type": "score",
                "instructions": "Rate code completeness and structure.",
                "criteria": ["Incomplete / stub", "Basic playable", "Well-structured"]
            }
        }
    }
    jev_step2_data, jev_step2_time = call_jev(jev_gate_payload)
    print(f"   -> Jev Step 2 returned in: {jev_step2_time:.3f}s")
    print(f"      Valid Game (Noul): {jev_step2_data['answers']['is_valid_html_canvas']['noul']:.2f}")
    print(f"      Quality (Score): {jev_step2_data['answers']['code_quality']['score']:.2f}")

    run2_wall_end = time.perf_counter()
    run2_total_time = run2_wall_end - run2_wall_start
    print(f"✅ RUN 2 Finished in: {run2_total_time:.3f} seconds")
    print(f"   - Jev Overhead (2 calls): {jev_step1_time + jev_step2_time:.3f}s")
    print(f"   - LLM Generation: {llm_time_run2:.3f}s")
    print(f"   - Tokens Generated: {raw_run2.get('eval_count', 0)}")

    # ----------------------------------------------------
    # FINAL UN-ESTIMATED COMPARISON
    # ----------------------------------------------------
    print("\n" + "=" * 60)
    print("📊 UN-ESTIMATED WALL-CLOCK MEASUREMENT SUMMARY")
    print("=" * 60)
    print(f"Run 1 (Pure LLM Baseline):       {run1_total_time:.3f}s")
    print(f"Run 2 (Jev-Guided Pipeline):     {run2_total_time:.3f}s")
    diff = run2_total_time - run1_total_time
    faster = "Run 1" if diff > 0 else "Run 2"
    print(f"Winner:                          {faster} is faster by {abs(diff):.3f}s")
    print("=" * 60)

    # Save exact measurement report
    report = {
        "test": "Wall-clock speed benchmark (measured with time.perf_counter)",
        "run_1_baseline_seconds": round(run1_total_time, 3),
        "run_1_tokens": raw_run1.get("eval_count", 0),
        "run_1_tokens_per_sec": round(raw_run1.get("eval_count", 0) / llm_time_run1, 1),
        "run_2_jev_guided_seconds": round(run2_total_time, 3),
        "run_2_jev_overhead_seconds": round(jev_step1_time + jev_step2_time, 3),
        "run_2_tokens": raw_run2.get("eval_count", 0),
        "run_2_tokens_per_sec": round(raw_run2.get("eval_count", 0) / llm_time_run2, 1),
        "delta_seconds": round(diff, 3),
        "faster": faster
    }
    with open("benchmarks/measured_runs/real_benchmark.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    main()
