#!/usr/bin/env python3
"""
Experiment 3: Full-Stack Multi-File Architecture Swarm
Stack: FastAPI Backend + SQLite Storage + HTML5 Analytical Dashboard
Orchestration: TypeSafe Jev System One
Workers: Huihui-Qwen3.5-2B-abliterated-GGUF:Q4_K_M

Micro-Workers:
1. models.py (Pydantic & SQLite Schemas) - Worker 1
2. server.py (FastAPI Routes & In-Memory Store) - Worker 2
3. dashboard.html & JS (Visual Telemetry Client) - Worker 3
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "hf.co/mradermacher/Huihui-Qwen3.5-2B-abliterated-GGUF:Q4_K_M"
TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"

def get_key():
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

KEY = get_key()

def call_jev(payload):
    t0 = time.perf_counter()
    req = urllib.request.Request(
        TYPESAFE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data, time.perf_counter() - t0

def generate_code(lang, prompt, num_predict=1000):
    t0 = time.perf_counter()
    chatml = f"""<|im_start|>system
You are an expert full-stack developer. Generate ONLY valid {lang} code enclosed in ```{lang} ... ``` code fences. Do not add conversational explanations.<|im_end|>
<|im_start|>user
{prompt}
<|im_end|>
<|im_start|>assistant
<think>
"""
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps({
            "model": MODEL,
            "prompt": chatml,
            "options": {"num_predict": num_predict, "temperature": 0.1},
            "stream": False
        }).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    elapsed = time.perf_counter() - t0
    raw = data.get("response", "")
    tokens = data.get("eval_count", 0)

    after_think = raw.split("</think>")[-1] if "</think>" in raw else raw
    # Match markdown code block
    m = re.findall(r"```(?:[a-zA-Z0-9_-]+)?\s*\n?(.*?)(?:```|$)", after_think, re.DOTALL)
    # Find longest block if multiple exist, else fall back to after_think
    valid_blocks = [b.strip() for b in m if b.strip()]
    code = max(valid_blocks, key=len) if valid_blocks else after_think.strip()

    return code, elapsed, tokens

def main():
    print("=" * 75)
    print("🌐 EXPERIMENT 3: FULL-STACK MULTI-FILE SWARM")
    print(f"   Architecture: FastAPI + SQLite + HTML5 Telemetry Dashboard")
    print(f"   Worker Model: {MODEL}")
    print(f"   Governance: TypeSafe Jev System One")
    print("=" * 75)

    out_dir = "benchmarks/fullstack_swarm"
    os.makedirs(out_dir, exist_ok=True)
    t_global_start = time.perf_counter()

    # Step 1: Jev Blueprint
    print("\n[Phase 1: Jev Hivemind API Spec & Schema Architecture]")
    plan_res, t_plan = call_jev({
        "state": "Building full-stack telemetry and high-score service for arcade swarms.",
        "model": "jev-latest",
        "questions": {
            "api_framework": {
                "type": "choice",
                "instructions": "Select the optimal lightweight Python API framework",
                "criteria": {
                    "fastapi": "FastAPI with Pydantic typing and uvicorn ASGI.",
                    "flask": "Flask synchronous WSGI.",
                    "raw_http": "Python http.server."
                }
            },
            "persistence_model": {
                "type": "choice",
                "instructions": "Select the persistence strategy",
                "criteria": {
                    "sqlite_file": "SQLite local database with automatic table initialization.",
                    "in_memory": "Ephemeral in-memory dictionary."
                }
            }
        }
    })
    print(f"   ✅ Jev resolved in {t_plan*1000:.1f}ms:")
    print(f"      - Framework: '{plan_res['answers']['api_framework']['choice']}'")
    print(f"      - Persistence: '{plan_res['answers']['persistence_model']['choice']}'")

    results = {}

    # Worker 1: models.py
    print("\n[Phase 2: Micro-Worker 1 -> models.py (Pydantic & SQLite)]")
    p1 = (
        "Write python code for models.py:\n"
        "from pydantic import BaseModel\n"
        "from typing import Optional\n"
        "class ScoreEntry(BaseModel):\n"
        "    player_name: str\n"
        "    score: int\n"
        "    wave: int\n"
        "class TelemetryEvent(BaseModel):\n"
        "    event_type: str\n"
        "    timestamp: float\n"
        "    data: dict\n"
    )
    code_models, t1, tok1 = generate_code("python", p1)
    v1, tv1 = call_jev({
        "state": code_models,
        "model": "jev-latest",
        "questions": {"valid": {"type": "noul", "instructions": "Does this define valid Pydantic models for ScoreEntry and TelemetryEvent?"}}
    })
    noul1 = v1.get("answers", {}).get("valid", {}).get("noul", 0.0)
    print(f"   ✅ models.py: {len(code_models)} chars in {t1:.2f}s ({tok1} tok) | Jev Gate: {noul1:.2f}")
    results["models"] = {"code": code_models, "time": t1, "tokens": tok1, "noul": noul1}
    with open(f"{out_dir}/models.py", "w") as f:
        f.write(code_models)

    # Worker 2: server.py
    print("\n[Phase 2: Micro-Worker 2 -> server.py (FastAPI Routes)]")
    p2 = (
        "Write python code for server.py using FastAPI:\n"
        "from fastapi import FastAPI\n"
        "from models import ScoreEntry, TelemetryEvent\n"
        "import sqlite3\n"
        "import json\n"
        "app = FastAPI(title='Swarm Telemetry API')\n"
        "Initialize SQLite database 'swarm_telemetry.db' on startup or module load with tables:\n"
        "- scores (player_name TEXT, score INTEGER, wave INTEGER)\n"
        "- telemetry (event_type TEXT, timestamp REAL, data TEXT)\n"
        "Provide:\n"
        "1. @app.get('/api/health') returning {'status': 'ok'}\n"
        "2. @app.get('/api/scores') returning list of scores from SQLite as dicts\n"
        "3. @app.post('/api/scores') accepting ScoreEntry and inserting into SQLite\n"
        "4. @app.get('/api/telemetry') returning recent events from SQLite as dicts\n"
        "5. @app.post('/api/telemetry') accepting TelemetryEvent and inserting into SQLite\n"
    )
    code_server, t2, tok2 = generate_code("python", p2, num_predict=1000)
    v2, tv2 = call_jev({
        "state": code_server,
        "model": "jev-latest",
        "questions": {"valid": {"type": "noul", "instructions": "Does this implement a valid FastAPI app with health, scores, and telemetry endpoints?"}}
    })
    noul2 = v2.get("answers", {}).get("valid", {}).get("noul", 0.0)
    print(f"   ✅ server.py: {len(code_server)} chars in {t2:.2f}s ({tok2} tok) | Jev Gate: {noul2:.2f}")
    results["server"] = {"code": code_server, "time": t2, "tokens": tok2, "noul": noul2}
    with open(f"{out_dir}/server.py", "w") as f:
        f.write(code_server)

    # Worker 3: dashboard.html
    print("\n[Phase 2: Micro-Worker 3 -> dashboard.html (Responsive Dashboard)]")
    p3 = (
        "Write html code for a clean, futuristic dark-mode telemetry dashboard dashboard.html:\n"
        "Include CSS and JavaScript in the same file.\n"
        "The page should:\n"
        "1. Display a header: '🛰️ SWARM REAL-TIME TELEMETRY'\n"
        "2. Display a High Scores Table fetching from '/api/scores'\n"
        "3. Display Live Telemetry Feed fetching from '/api/telemetry'\n"
        "4. Include a status badge 'SYSTEM ONLINE'\n"
    )
    code_dash, t3, tok3 = generate_code("html", p3, num_predict=1000)
    v3, tv3 = call_jev({
        "state": code_dash,
        "model": "jev-latest",
        "questions": {"valid": {"type": "noul", "instructions": "Is this a valid HTML5 dark-theme telemetry dashboard fetching from /api/scores and /api/telemetry?"}}
    })
    noul3 = v3.get("answers", {}).get("valid", {}).get("noul", 0.0)
    print(f"   ✅ dashboard.html: {len(code_dash)} chars in {t3:.2f}s ({tok3} tok) | Jev Gate: {noul3:.2f}")
    results["dashboard"] = {"code": code_dash, "time": t3, "tokens": tok3, "noul": noul3}
    with open(f"{out_dir}/dashboard.html", "w") as f:
        f.write(code_dash)

    # Verification: Syntax checks
    print("\n[Phase 3: Automated Verification]")
    py_check1 = subprocess.run([sys.executable, "-m", "py_compile", f"{out_dir}/models.py"], capture_output=True, text=True)
    py_check2 = subprocess.run([sys.executable, "-m", "py_compile", f"{out_dir}/server.py"], capture_output=True, text=True)
    print(f"   - models.py compilation: {'✅ PASS' if py_check1.returncode == 0 else '❌ FAIL'}")
    print(f"   - server.py compilation: {'✅ PASS' if py_check2.returncode == 0 else '❌ FAIL'}")
    if py_check2.returncode != 0:
        print("     Server syntax error:\n", py_check2.stderr)

    # Final Jev Full-Stack Audit
    print("\n[Phase 4: Final TypeSafe Jev System One Quality Audit]")
    total_time = time.perf_counter() - t_global_start
    total_tokens = sum(r["tokens"] for r in results.values())
    total_jev_overhead = sum([tv1, tv2, tv3]) + t_plan

    audit_payload = {
        "state": f"## Full-Stack Swarm Implementation\n\n### models.py\n```python\n{code_models}\n```\n\n### server.py\n```python\n{code_server}\n```\n\n### dashboard.html\n```html\n{code_dash[:1500]}\n```",
        "model": "jev-latest",
        "questions": {
            "api_contract_soundness": {
                "type": "noul",
                "instructions": "Do the FastAPI routes correctly consume the Pydantic models defined in models.py without contract mismatch?"
            },
            "fullstack_quality_score": {
                "type": "score",
                "instructions": "Rate the full-stack architecture quality from 0 (broken) to 3 (production-grade)",
                "range": [0, 3],
                "criteria": ["Broken code", "Fragile / syntax errors", "Functional prototype", "Clean production-grade"]
            }
        }
    }
    audit_res, t_audit = call_jev(audit_payload)
    ans = audit_res.get("answers", {})
    soundness = ans.get("api_contract_soundness", {}).get("noul", 0.0)
    quality = ans.get("fullstack_quality_score", {}).get("score", 0.0)

    print(f"   - API Contract Soundness (Noul): {soundness:.3f} {'✅' if soundness >= 0.7 else '❌'}")
    print(f"   - Full-Stack Quality Score: {quality:.2f} / 3.0")
    print(f"   - Total Swarm Time: {total_time:.2f}s | Tokens: {total_tokens} | Jev Overhead: {total_jev_overhead:.2f}s")

    metrics = {
        "experiment": "Experiment 3: Full-Stack Multi-File Architecture Swarm",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model": MODEL,
        "total_wall_clock_seconds": round(total_time, 2),
        "total_tokens": total_tokens,
        "total_jev_overhead_seconds": round(total_jev_overhead, 2),
        "results": results,
        "verification": {
            "models_py_compile": py_check1.returncode == 0,
            "server_py_compile": py_check2.returncode == 0
        },
        "final_audit": {
            "contract_soundness_noul": round(soundness, 3),
            "quality_score": round(quality, 2)
        }
    }
    with open(f"{out_dir}/exp3_results.json", "w") as f:
        json.dump(metrics, f, indent=2)

if __name__ == "__main__":
    main()
