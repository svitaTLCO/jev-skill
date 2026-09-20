#!/usr/bin/env python3
"""
Experiment 4: Self-Healing Loop Test (Jev Compiler-in-the-Loop)
Testing Autonomous Recovery of Abliterated SLMs (0.8B & 2B) from Syntax, AST, and Contract Defects.

Pipeline:
1. Generation: Abliterated SLM produces code.
2. Verification: Local compiler (Python py_compile / Node.js --check) + TypeSafe Jev System One.
3. If failure detected: Extract compiler traceback + defect context, generate healing prompt.
4. Healing: Model ingests error diagnostic and regenerates valid patch.
5. Re-Verification: Compile and score final output.
"""

import ast
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_2B = "hf.co/mradermacher/Huihui-Qwen3.5-2B-abliterated-GGUF:Q4_K_M"
MODEL_08B = "hf.co/mradermacher/Huihui-Qwen3.5-0.8B-abliterated-GGUF:Q4_K_M"
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

def generate_completion(model, prompt, num_predict=800, temperature=0.1):
    t0 = time.perf_counter()
    chatml = f"""<|im_start|>system
You are a precise coding specialist. Output ONLY the code enclosed in markdown code fences. No chatter.<|im_end|>
<|im_start|>user
{prompt}
<|im_end|>
<|im_start|>assistant
<think>
"""
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps({
            "model": model,
            "prompt": chatml,
            "options": {"num_predict": num_predict, "temperature": temperature},
            "stream": False
        }).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    elapsed = time.perf_counter() - t0
    raw = data.get("response", "")
    tokens = data.get("eval_count", 0)

    after_think = raw.split("</think>")[-1] if "</think>" in raw else raw
    m = re.findall(r"```(?:[a-zA-Z0-9_-]+)?\s*\n?(.*?)(?:```|$)", after_think, re.DOTALL)
    valid_blocks = [b.strip() for b in m if b.strip()]
    code = max(valid_blocks, key=len) if valid_blocks else after_think.strip()
    return code, elapsed, tokens

def check_python_syntax(code_str):
    try:
        ast.parse(code_str)
        return True, "Valid Python syntax", None
    except SyntaxError as e:
        return False, f"SyntaxError at line {e.lineno}: {e.msg}", e.lineno

def check_js_syntax(code_str):
    try:
        res = subprocess.run(
            ["node", "-e", "const vm = require('vm'); try { new vm.Script(process.argv[1]); } catch (e) { console.error(e.message); process.exit(1); }", code_str],
            capture_output=True, text=True, timeout=5
        )
        if res.returncode == 0:
            return True, "Valid JavaScript syntax", None
        err = res.stderr.strip() or res.stdout.strip()
        return False, f"JavaScript SyntaxError: {err}", None
    except Exception as e:
        return False, str(e), None

def run_self_healing_test(name, model, lang, initial_prompt, checker_fn, max_tokens=700):
    print(f"\n{'='*75}")
    print(f"🧪 TEST CASE: {name}")
    print(f"   Model: {model.split('/')[-1]}")
    print(f"   Language: {lang.upper()}")
    print(f"{'='*75}")

    # Round 0: Initial Generation
    print("[Round 0: Initial Inference]")
    code_r0, t_r0, tok_r0 = generate_completion(model, initial_prompt, num_predict=max_tokens)
    print(f"   Generated {len(code_r0)} chars in {t_r0:.2f}s ({tok_r0} tok)")

    is_valid, err_msg, lineno = checker_fn(code_r0)
    print(f"   Compiler Check: {'✅ PASS' if is_valid else '❌ FAIL'}")
    if not is_valid:
        print(f"   Diagnostic: {err_msg[:200]}")

    healing_record = {
        "test": name,
        "model": model,
        "lang": lang,
        "round_0": {
            "valid": is_valid,
            "error": err_msg if not is_valid else None,
            "time": t_r0,
            "tokens": tok_r0,
            "code_sample": code_r0[:300]
        },
        "healed": False
    }

    if is_valid:
        print("   -> Code passed on initial attempt. Simulating intentional defect injection to test healing...")
        # Inject an intentional syntax error to test recovery
        if lang == "python":
            lines = code_r0.split("\n")
            if len(lines) > 5:
                lines[5] = lines[5] + " { unclosed_bracket"
                code_r0 = "\n".join(lines)
        elif lang == "javascript":
            code_r0 = code_r0 + "\n  function broken( { return"
        is_valid, err_msg, lineno = checker_fn(code_r0)
        print(f"   Injected Defect Compiler Check: ❌ FAIL ({err_msg[:120]})")

    # Round 1: Self-Healing Feedback Loop
    print("\n[Round 1: Jev Compiler-in-the-Loop Self-Healing Prompt]")
    healing_prompt = f"""Your previous code has a fatal compiler error:
--- COMPILER DIAGNOSTIC ---
{err_msg}
--- FAILING CODE ---
{code_r0}

TASK:
Fix the syntax error and any missing imports or unclosed brackets/strings.
Return ONLY the corrected, complete, compilable {lang} code enclosed in ```{lang} ... ``` code fences.
Do NOT repeat the error. Do NOT add conversational prose.
"""
    code_r1, t_r1, tok_r1 = generate_completion(model, healing_prompt, num_predict=max_tokens + 200)
    print(f"   Healed Output: {len(code_r1)} chars in {t_r1:.2f}s ({tok_r1} tok)")

    is_valid_r1, err_msg_r1, _ = checker_fn(code_r1)
    print(f"   Post-Healing Compiler Check: {'✅ REPAIRED SUCCESSFULLY' if is_valid_r1 else '❌ STILL BROKEN'}")
    if not is_valid_r1:
        print(f"   Remaining Error: {err_msg_r1[:200]}")

    # Save healed artifact
    out_dir = "benchmarks/self_healing"
    os.makedirs(out_dir, exist_ok=True)
    ext = "py" if lang == "python" else "js"
    clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())
    with open(f"{out_dir}/{clean_name}.{ext}", "w") as f:
        f.write(code_r1)

    # Jev Quality Audit of Healed Output
    print("   Evaluating post-healing output via TypeSafe Jev System One...")
    audit_payload = {
        "state": f"## Code Under Audit ({lang})\n```{lang}\n{code_r1}\n```",
        "model": "jev-latest",
        "questions": {
            "syntactically_and_logically_sound": {
                "type": "noul",
                "instructions": f"Is this {lang} code syntactically sound and logically coherent?"
            },
            "production_readiness": {
                "type": "score",
                "instructions": "Rate the code quality from 0 (broken) to 3 (clean)",
                "range": [0, 3],
                "criteria": ["Broken / uncompilable", "Rough / minor issues", "Good working code", "Clean production standard"]
            }
        }
    }
    audit_res, t_audit = call_jev(audit_payload)
    ans = audit_res.get("answers", {})
    sound_noul = ans.get("syntactically_and_logically_sound", {}).get("noul", 0.0)
    score_val = ans.get("production_readiness", {}).get("score", 0.0)

    print(f"   Jev Soundness (Noul): {sound_noul:.3f} | Quality Score: {score_val:.2f} / 3.0 (in {t_audit*1000:.1f}ms)")

    healing_record["round_1"] = {
        "valid": is_valid_r1,
        "error": err_msg_r1 if not is_valid_r1 else None,
        "time": t_r1,
        "tokens": tok_r1,
        "jev_soundness_noul": sound_noul,
        "jev_quality_score": score_val
    }
    healing_record["healed"] = is_valid_r1
    return healing_record

def main():
    print("=" * 75)
    print("🔄 EXPERIMENT 4: SELF-HEALING LOOP (JEV COMPILER-IN-THE-LOOP)")
    print("   Target Models: Huihui-Qwen3.5-0.8B & 2B Abliterated")
    print("   Evaluator: AST/Compiler + TypeSafe Jev System One")
    print("=" * 75)

    records = []

    # Test 1: Python FastAPI & SQLite Data Handler (2B Model)
    p_python = (
        "Write a python class `GameTelemetryStore` that connects to SQLite, initializes a table "
        "`telemetry_logs (id INTEGER PRIMARY KEY, player TEXT, action TEXT, payload TEXT, timestamp REAL)`, "
        "and provides `log_event(player, action, payload_dict)` and `get_recent(limit=50)`."
    )
    rec1 = run_self_healing_test(
        "Python SQLite Data Handler (2B)",
        MODEL_2B,
        "python",
        p_python,
        check_python_syntax,
        max_tokens=650
    )
    records.append(rec1)

    # Test 2: JavaScript Canvas Vector Particle Physics (0.8B Model)
    p_js = (
        "Write a JavaScript object `ParticleEmitter` with:\n"
        "- `particles: []`\n"
        "- `emit(x, y, count, color)` creating particles with random velocities\n"
        "- `update(ctx)` updating positions, alpha fade, and drawing circles\n"
        "Output ONLY the JavaScript code."
    )
    rec2 = run_self_healing_test(
        "JavaScript Particle Emitter (0.8B)",
        MODEL_08B,
        "javascript",
        p_js,
        check_js_syntax,
        max_tokens=500
    )
    records.append(rec2)

    # Summary
    print("\n" + "=" * 75)
    print("📊 SELF-HEALING EXPERIMENT SUMMARY")
    print("=" * 75)
    for r in records:
        status = "✅ HEALED" if r["healed"] else "❌ FAILED HEALING"
        r0_status = "Clean" if r["round_0"]["valid"] else "Failed"
        print(f"- {r['test']}: Initial={r0_status} -> Round 1={status} (Jev Noul: {r.get('round_1', {}).get('jev_soundness_noul', 0):.2f})")

    out_file = "benchmarks/exp4_self_healing_results.json"
    with open(out_file, "w") as f:
        json.dump(records, f, indent=2)
    print(f"\nDetailed metrics written to: {out_file}")

if __name__ == "__main__":
    main()
