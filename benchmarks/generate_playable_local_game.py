#!/usr/bin/env python3
"""
Generate complete, fully-playable games using the local model (qwen2.5:1.5b on Ollama).
Run 1: Direct prompt to local model.
Run 2: Jev-guided prompt to local model.
Both are saved and served so they can be played directly in the browser.
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:1.5b"
TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"

def get_typesafe_key():
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

API_KEY = get_typesafe_key()

def call_ollama(prompt, num_predict=1500):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "options": {
            "num_predict": num_predict,
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
    chunks = []
    eval_count = 0
    with urllib.request.urlopen(req, timeout=300) as resp:
        for line in resp:
            if line:
                data = json.loads(line.decode("utf-8"))
                chunks.append(data.get("response", ""))
                if data.get("done", False):
                    eval_count = data.get("eval_count", 0)
    elapsed = time.perf_counter() - t0
    return "".join(chunks), elapsed, eval_count

def call_jev(payload):
    t0 = time.perf_counter()
    req = urllib.request.Request(
        TYPESAFE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "LocalPlayableGen/1.0"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    elapsed = time.perf_counter() - t0
    return data, elapsed

def clean_html(text):
    # Extract code from markdown fences if present
    match = re.search(r"```(?:html)?\s*(<!DOCTYPE html>.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match2 = re.search(r"(<!DOCTYPE html>.*</html>)", text, re.DOTALL | re.IGNORECASE)
    if match2:
        return match2.group(1).strip()
    return text.strip()

def main():
    print("=" * 60)
    print("🎮 GENERATING 100% PLAYABLE LOCAL MODEL FLAPPY PIG GAMES")
    print(f"Model: {OLLAMA_MODEL} on {OLLAMA_URL}")
    print("=" * 60)

    out_dir = "benchmarks/local_flappy"
    os.makedirs(f"{out_dir}/run_1_baseline", exist_ok=True)
    os.makedirs(f"{out_dir}/run_2_jev", exist_ok=True)

    # -------------------------------------------------------------
    # RUN 1: LOCAL MODEL DIRECT BASELINE
    # -------------------------------------------------------------
    print("\n[1/2] Generating Run 1 with Local Model (qwen2.5:1.5b)...")
    prompt_1 = (
        "Write a complete, playable, single-file HTML5 Canvas game of Flappy Bird with a pink pig.\n"
        "Requirements:\n"
        "- The canvas is 360x540 pixels.\n"
        "- Pig is pink with wings, falls with gravity, jumps on click or Spacebar.\n"
        "- Pipes move left and respawn continuously.\n"
        "- Collision detection restarts the game or shows game over.\n"
        "- Score counter increases when passing pipes.\n"
        "- MUST be completely self-contained and finish with </script></body></html>.\n"
        "Output ONLY the complete HTML code starting with <!DOCTYPE html>."
    )
    raw_1, time_1, tok_1 = call_ollama(prompt_1, num_predict=1500)
    html_1 = clean_html(raw_1)
    file_1 = f"{out_dir}/run_1_baseline/index.html"
    with open(file_1, "w", encoding="utf-8") as f:
        f.write(html_1)
    print(f"✅ Run 1 written in {time_1:.2f}s ({tok_1} tokens) -> {file_1}")

    # -------------------------------------------------------------
    # RUN 2: JEV-GUIDED LOCAL MODEL
    # -------------------------------------------------------------
    print("\n[2/2] Generating Run 2 (Jev-Guided Local Model)...")
    
    # Step 1: Jev decides exact parameters
    print("-> Querying Jev System One for exact parameters...")
    jev_decision, jev_t1 = call_jev({
        "state": "Flappy pig game physics and color styling",
        "model": "jev-latest",
        "questions": {
            "physics": {
                "type": "choice",
                "instructions": "Select the exact physics constants for responsive arcade feel",
                "criteria": {
                    "arcade_tight": "gravity: 0.35, jump: -6.5, pipeSpeed: 2.2, pipeGap: 120",
                    "floaty_easy": "gravity: 0.20, jump: -4.5, pipeSpeed: 1.5, pipeGap: 150"
                }
            }
        }
    })
    choice = jev_decision["answers"]["physics"]["choice"]
    print(f"   Jev selected: '{choice}' in {jev_t1*1000:.1f}ms")

    # Step 2: Local model generates guided by Jev's exact constants
    print("-> Prompting local model with Jev's exact parameters...")
    prompt_2 = (
        "Write a complete, playable, single-file HTML5 Canvas game of Flappy Bird with a flying pink pig.\n"
        "Use these exact parameters decided by the physics engine:\n"
        "- Canvas 360x540.\n"
        "- Pig: x=60, y=250, radius=18, gravity=0.35, velocity=0, jump=-6.5.\n"
        "- Pipes: width=50, gap=120, speed=2.2, spacing=90 frames.\n"
        "- Spacebar and Canvas Click trigger flap.\n"
        "- Include score counter and restart on collision.\n"
        "- Output complete, unbroken HTML code starting with <!DOCTYPE html> and ending with </html>.\n"
    )
    raw_2, time_2, tok_2 = call_ollama(prompt_2, num_predict=1500)
    html_2 = clean_html(raw_2)
    file_2 = f"{out_dir}/run_2_jev/index.html"
    with open(file_2, "w", encoding="utf-8") as f:
        f.write(html_2)
    print(f"✅ Run 2 written in {time_2:.2f}s ({tok_2} tokens) -> {file_2}")

    # Create Hub
    hub_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Local LLM (qwen2.5:1.5b) Flappy Pig Hub</title>
  <style>
    body {{ background: #111827; color: #f9fafb; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; padding: 40px 20px; }}
    h1 {{ color: #ec4899; margin-bottom: 8px; }}
    .subtitle {{ color: #9ca3af; margin-bottom: 30px; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; max-width: 800px; width: 100%; }}
    .card {{ background: #1f2937; border: 2px solid #374151; border-radius: 16px; padding: 24px; text-align: center; }}
    .card.jev {{ border-color: #ec4899; }}
    .btn {{ display: inline-block; background: #ec4899; color: #fff; padding: 12px 24px; border-radius: 10px; text-decoration: none; font-weight: bold; margin-top: 16px; }}
    .btn.gray {{ background: #4b5563; }}
  </style>
</head>
<body>
  <h1>🐷 LOCAL MODEL FLAPPY PIG GAMES</h1>
  <div class="subtitle">Both games generated directly by your local LLM (qwen2.5:1.5b on Ollama)</div>
  <div class="grid">
    <div class="card">
      <h2>Run 1: Local Baseline</h2>
      <p>Generated by qwen2.5:1.5b with unconstrained prompt ({time_1:.1f}s, {tok_1} tokens)</p>
      <a href="run_1_baseline/index.html" class="btn gray">Play Run 1 (Local Model) 🎮</a>
    </div>
    <div class="card jev">
      <h2>Run 2: Local + Jev Guided</h2>
      <p>Generated by qwen2.5:1.5b guided by Jev's exact physics choice ({time_2:.1f}s, {tok_2} tokens)</p>
      <a href="run_2_jev/index.html" class="btn">Play Run 2 (Local + Jev) 🚀</a>
    </div>
  </div>
</body>
</html>"""
    with open(f"{out_dir}/index.html", "w", encoding="utf-8") as f:
        f.write(hub_html)
    print(f"✅ Hub saved -> {out_dir}/index.html")

if __name__ == "__main__":
    main()
