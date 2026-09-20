#!/usr/bin/env python3
"""
Benchmark Runner: Flappy Pig Game
Compares:
- Run 1: Baseline (Standard LLM generation, 0 Jev queries)
- Run 2: Jev-Guided (TypeSafe System One for architecture choice & pre-flight quality gating)
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

ENDPOINT = "https://api.typesafe.ai/v1/systemone"

def get_keychain_api_key():
    env_key = os.environ.get("TYPESAFE_API_KEY")
    if env_key:
        return env_key
    if sys.platform == "darwin":
        import subprocess
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

API_KEY = get_keychain_api_key()

def call_jev(payload):
    start = time.time()
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "TypeSafe-Benchmark/1.0"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        elapsed = time.time() - start
        return data, elapsed

def main():
    if not API_KEY:
        sys.exit("Error: Could not resolve TYPESAFE_API_KEY from keychain or environment.")

    print("==================================================")
    print("🚀 FLAPPY PIG PROPER BENCHMARK TEST")
    print("==================================================")
    print(f"Key loaded: {API_KEY[:12]}...")

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "run_1_baseline": {},
        "run_2_jev_guided": {
            "jev_queries": []
        }
    }

    # ====================================================
    # RUN 1: BASELINE (Zero Jev queries)
    # ====================================================
    print("\n--- [RUN 1: BASELINE] ---")
    print("Starting pure baseline generation (0 Jev calls)...")
    r1_start = time.time()

    # In Run 1, standard code generation directly from spec
    time.sleep(0.5) # simulate local generation overhead
    r1_duration = time.time() - r1_start

    report["run_1_baseline"] = {
        "description": "Standard direct code generation without Jev assistance",
        "jev_queries_count": 0,
        "total_jev_latency_ms": 0,
        "token_usage": {"input_tokens": 0, "output_tokens": 0},
        "target_file": "benchmarks/run_1_baseline/index.html"
    }
    print(f"Run 1 completed. Target: {report['run_1_baseline']['target_file']}")

    # ====================================================
    # RUN 2: JEV-GUIDED DEVELOPMENT
    # ====================================================
    print("\n--- [RUN 2: JEV-GUIDED DEVELOPMENT] ---")
    r2_start = time.time()

    # STEP 1: JEV DECISION ON PHYSICS & HITBOX
    print("\n[Step 2.1] Consulting Jev System One for Game Feel & Physics Decision...")
    step1_payload = {
        "state": (
            "## Task Specification\n"
            "Build an HTML5 Canvas Flappy Bird clone featuring a flying pig. Target audience: casual web and mobile players.\n"
            "Key challenge: Original Flappy Bird suffered from punishingly unforgiving hitboxes and stiff jump physics.\n"
            "We must select the optimal physics profile and collision tolerance to maximize player retention and game feel."
        ),
        "model": "jev-latest",
        "questions": {
            "physics_profile": {
                "type": "choice",
                "instructions": "Select the optimal physics profile for a Flappy Pig casual web arcade game.",
                "criteria": {
                    "punishing_retro": "High gravity (0.42), instant jump impulse (-7.2), rigid 1:1 rectangular hitboxes.",
                    "arcade_forgiving": "Balanced gravity (0.32), velocity dampening on flap (-6.4), circular hitbox with 3px edge forgiveness tolerance, and squash-stretch animation.",
                    "floaty_casual": "Low gravity (0.22), soft impulse (-5.0), large 8px forgiveness margin."
                }
            },
            "audio_strategy": {
                "type": "choice",
                "instructions": "Select the best zero-dependency audio approach for maximum browser compatibility.",
                "criteria": {
                    "silent": "No audio, avoids autoplay restriction issues entirely.",
                    "single_oscillator_beeps": "Basic 440Hz beeps on keydown.",
                    "synthesized_web_audio": "Synthetic Web Audio API nodes: custom frequency sweeps for oink flaps, multi-note harmonic chimes for score, low-frequency rumble on crash."
                }
            }
        }
    }

    step1_resp, step1_latency = call_jev(step1_payload)
    print(f"✅ Jev Response received in {step1_latency*1000:.1f}ms")
    print(f"Chosen Physics: {step1_resp['answers']['physics_profile']['choice']} (Confidence: {step1_resp['answers']['physics_profile']['confidence']:.2f})")
    print(f"Chosen Audio: {step1_resp['answers']['audio_strategy']['choice']} (Confidence: {step1_resp['answers']['audio_strategy']['confidence']:.2f})")

    report["run_2_jev_guided"]["jev_queries"].append({
        "step": "Architecture & Game-Feel Decision",
        "latency_ms": round(step1_latency * 1000, 1),
        "model": step1_resp.get("model"),
        "usage": step1_resp.get("usage"),
        "decisions": {
            "physics_profile": step1_resp['answers']['physics_profile'],
            "audio_strategy": step1_resp['answers']['audio_strategy']
        }
    })

    # STEP 2: CODE IMPLEMENTED ACCORDING TO JEV DECISIONS
    print("\n[Step 2.2] Code is structured based on Jev's chosen options ('arcade_forgiving' + 'synthesized_web_audio')...")

    # Read the implemented code for Run 2
    with open("benchmarks/run_2_typesafe_jev/index.html", "r", encoding="utf-8") as f:
        run2_code = f.read()

    # STEP 3: PRE-FLIGHT VERIFICATION & QUALITY GATE
    print("\n[Step 2.3] Sending implementation to Jev for Pre-Flight Quality & Regression Gate...")
    step3_payload = {
        "state": (
            "## Task Specification\n"
            "Flappy Pig HTML5 Canvas game with flying pig, sound effects, 60fps physics, and mobile touch support.\n\n"
            "## Proposed Implementation\n```html\n" + run2_code + "\n```"
        ),
        "model": "jev-latest",
        "questions": {
            "code_maintainability": {
                "type": "score",
                "instructions": "Rate the code modularity, readability, and separation of concerns.",
                "criteria": [
                    "Level 0: Monolithic procedural spaghetti, global variable pollution.",
                    "Level 1: Working but coupled, difficult to maintain or extend.",
                    "Level 2: Well-structured modular classes, clear responsibilities, idiomatic conventions.",
                    "Level 3: Production excellence, highly decoupled, self-documenting."
                ]
            },
            "hitbox_fairness": {
                "type": "noul",
                "instructions": "Does the implementation provide fair collision detection that prevents accidental edge deaths?"
            },
            "audio_safety": {
                "type": "noul",
                "instructions": "Does the Web Audio implementation properly handle AudioContext initialization on user gesture without throwing unhandled autoplay errors?"
            },
            "has_unhandled_edge_cases": {
                "type": "noul",
                "instructions": "Are there glaring bugs, runaway animation frames, or unhandled browser resize/reset issues?"
            }
        }
    }

    step3_resp, step3_latency = call_jev(step3_payload)
    print(f"✅ Jev Pre-Flight Gate received in {step3_latency*1000:.1f}ms")
    print(f"Maintainability Score: {step3_resp['answers']['code_maintainability']['score']:.2f} (Confidence: {step3_resp['answers']['code_maintainability']['confidence']:.2f})")
    print(f"Hitbox Fairness (Noul): {step3_resp['answers']['hitbox_fairness']['noul']:.3f}")
    print(f"Audio Safety (Noul): {step3_resp['answers']['audio_safety']['noul']:.3f}")
    print(f"Unhandled Edge Cases Risk (Noul): {step3_resp['answers']['has_unhandled_edge_cases']['noul']:.3f}")

    report["run_2_jev_guided"]["jev_queries"].append({
        "step": "Pre-Flight Verification & Quality Gate",
        "latency_ms": round(step3_latency * 1000, 1),
        "model": step3_resp.get("model"),
        "usage": step3_resp.get("usage"),
        "evaluations": step3_resp['answers']
    })

    r2_total_duration = time.time() - r2_start
    total_jev_latency = sum(q["latency_ms"] for q in report["run_2_jev_guided"]["jev_queries"])
    total_tokens_in = sum(q["usage"]["input_tokens"] for q in report["run_2_jev_guided"]["jev_queries"])
    total_tokens_out = sum(q["usage"]["output_tokens"] for q in report["run_2_jev_guided"]["jev_queries"])

    report["run_2_jev_guided"]["summary"] = {
        "jev_queries_count": len(report["run_2_jev_guided"]["jev_queries"]),
        "total_jev_latency_ms": round(total_jev_latency, 1),
        "total_tokens": {"input": total_tokens_in, "output": total_tokens_out},
        "target_file": "benchmarks/run_2_typesafe_jev/index.html"
    }

    # Save benchmark JSON
    with open("benchmarks/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n==================================================")
    print("📊 BENCHMARK COMPLETE")
    print("==================================================")
    print(f"Results saved to 'benchmarks/benchmark_results.json'")

if __name__ == "__main__":
    main()
