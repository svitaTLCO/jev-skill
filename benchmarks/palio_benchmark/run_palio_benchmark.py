#!/usr/bin/env python3
"""
Palio di Siena 3D Game - TypeSafe AI (Jev) Architectural Decider & Benchmark
"""

import json
import os
import sys
import time
import urllib.request

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
            "User-Agent": "TypeSafe-Palio-Benchmark/1.0"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        elapsed = time.time() - start
        return data, elapsed

def main():
    print("==================================================")
    print("🏇 PALIO DI SIENA 3D - JEV SYSTEM ONE GUIDANCE")
    print("==================================================")

    # STEP 1: ARCHITECTURAL & RULES DECISION VIA JEV
    print("\n[Step 2.1] Consulting Jev System One for Physics & Rules Decisions...")
    step1_payload = {
        "state": (
            "## Task Specification\n"
            "Build a full playable 3D browser game of Palio di Siena in Piazza del Campo.\n"
            "Constraints: Must achieve steady 60 FPS in WebGL/Three.js, embody real physics, and reflect real Palio rules.\n"
            "Historical Context: Piazza del Campo has a steep downhill slope into the sharp Curva di San Martino where horses slip on tufo clay if taking the corner at full speed without braking or leaning. The race is 3 laps, involves intense Contrada rivalry, a whip (nerbo), and the historic 'Cavallo Scosso' rule where a riderless horse can win."
        ),
        "model": "jev-latest",
        "questions": {
            "physics_architecture": {
                "type": "choice",
                "instructions": "Select the optimal physics architecture to achieve realistic centrifugal drift and downhill slope at 60 FPS on browser.",
                "criteria": {
                    "rigid_spline_rail": "Simple forward progress along spline with no lateral slip or slope physics. High FPS, low realism.",
                    "centrifugal_tufo_drift": "Custom raycast vehicle/horse kinematics with slope acceleration, lateral centrifugal drift on tufo clay, San Martino wipeout risk, and stamina-governed gallop. Fast, 60fps stable, highly realistic feel.",
                    "wasm_rigid_ragdoll": "Heavy Cannon/Rapier WASM 3D physics with individual bone joints. High CPU load, potential frame drops on low-end devices."
                }
            },
            "palio_rules_fidelity": {
                "type": "choice",
                "instructions": "Select the rule set configuration for true Palio di Siena authenticity.",
                "criteria": {
                    "arcade_laps_only": "3 laps around the track without authentic Palio mechanics.",
                    "authentic_palio_mechanics": "3 laps with San Martino mattress barriers, stamina-based Nerbo whip boost, dynamic Contrade AI overtaking, Sunto bell tolling sound, and 'Cavallo Scosso' (rider ejection on high-speed wall crash, horse continues galloping)."
                }
            }
        }
    }

    step1_resp, step1_latency = call_jev(step1_payload)
    print(f"✅ Jev Step 1 received in {step1_latency*1000:.1f}ms")
    print(f"- Selected Physics: {step1_resp['answers']['physics_architecture']['choice']} (Confidence: {step1_resp['answers']['physics_architecture']['confidence']:.2f})")
    print(f"- Selected Rules: {step1_resp['answers']['palio_rules_fidelity']['choice']} (Confidence: {step1_resp['answers']['palio_rules_fidelity']['confidence']:.2f})")

    # Save decisions
    with open("benchmarks/palio_benchmark/step1_decisions.json", "w", encoding="utf-8") as f:
        json.dump(step1_resp, f, indent=2)

    # STEP 2: PRE-FLIGHT VERIFICATION & QUALITY GATE ON RUN 2 CODE
    print("\n[Step 2.3] Sending Implementation to Jev for Pre-Flight Quality & Rules Verification...")
    with open("benchmarks/palio_benchmark/run_2_jev_guided/index.html", "r", encoding="utf-8") as f:
        run2_code = f.read()

    step2_payload = {
        "state": (
            "## Task Specification\n"
            "Build a full playable 3D browser game of Palio di Siena in Piazza del Campo with real physics, real rules, and 60 FPS in browser.\n\n"
            "## Implementation\n```html\n" + run2_code + "\n```"
        ),
        "model": "jev-latest",
        "questions": {
            "maintainability": {
                "type": "score",
                "instructions": "Rate the code cleanliness, modularity, and WebGL rendering performance structure.",
                "criteria": [
                    "Level 0: Monolithic procedural mess, memory leaks, unoptimized loops.",
                    "Level 1: Working but coupled, basic error handling.",
                    "Level 2: Clean structure, clear separation of physics, audio, and Three.js scene, proper delta-time.",
                    "Level 3: Production excellence, highly optimized 60fps rendering, elegant shader/particle management."
                ]
            },
            "authenticity_of_palio_rules": {
                "type": "noul",
                "instructions": "Does this implementation faithfully embody authentic Palio rules: 3 laps, Curva di San Martino drop/danger, stamina/nerbo management, and Cavallo Scosso riderless continuation?"
            },
            "achieves_stable_60fps": {
                "type": "noul",
                "instructions": "Does the WebGL implementation use lightweight buffer geometries and requestAnimationFrame to ensure smooth 60 FPS in standard browsers?"
            }
        }
    }

    step2_resp, step2_latency = call_jev(step2_payload)
    print(f"✅ Jev Pre-Flight Gate received in {step2_latency*1000:.1f}ms")
    print(f"- Maintainability Score: {step2_resp['answers']['maintainability']['score']:.2f} (Confidence: {step2_resp['answers']['maintainability']['confidence']:.2f})")
    print(f"- Palio Rules Authenticity (Noul): {step2_resp['answers']['authenticity_of_palio_rules']['noul']:.3f}")
    print(f"- 60 FPS WebGL Stability (Noul): {step2_resp['answers']['achieves_stable_60fps']['noul']:.3f}")

    total_latency_ms = (step1_latency + step2_latency) * 1000
    benchmark_report = {
        "benchmark": "Palio di Siena 3D Game",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "run_1_baseline": {
            "description": "Standard 3D Three.js generation without Jev assistance",
            "jev_api_calls": 0,
            "jev_latency_ms": 0.0,
            "target_file": "benchmarks/palio_benchmark/run_1_baseline/index.html"
        },
        "run_2_jev_guided": {
            "description": "Jev-driven physics & authentic Palio rules development",
            "jev_api_calls": 2,
            "total_jev_latency_ms": round(total_latency_ms, 1),
            "step_1_architecture": {
                "latency_ms": round(step1_latency * 1000, 1),
                "decisions": step1_resp["answers"]
            },
            "step_2_verification": {
                "latency_ms": round(step2_latency * 1000, 1),
                "evaluations": step2_resp["answers"]
            },
            "target_file": "benchmarks/palio_benchmark/run_2_jev_guided/index.html"
        }
    }

    with open("benchmarks/palio_benchmark/benchmark_report.json", "w", encoding="utf-8") as f:
        json.dump(benchmark_report, f, indent=2)

    print("\n==================================================")
    print("📊 PALIO BENCHMARK COMPLETED")
    print(f"Total Jev latency overhead: {total_latency_ms:.1f}ms (~{total_latency_ms/1000:.1f}s)")
    print("Results saved to 'benchmarks/palio_benchmark/benchmark_report.json'")

if __name__ == "__main__":
    main()

