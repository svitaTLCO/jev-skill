#!/usr/bin/env python3
"""
8-Team Evolutionary Task-by-Task Promotion Swarm
All 8 teams compete on each internal task of the Space Invaders Deluxe project.
At every task milestone, TypeSafe Jev System One promotes the best quality code.
Hardware: Apple Silicon M1 (16GB RAM)
Model: huihui-qwen3.5:2b
"""

import concurrent.futures
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "huihui-qwen3.5:2b"
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

def generate_code_candidate(team_id, task_name, prompt, num_predict=700):
    t0 = time.perf_counter()
    chatml = f"""<|im_start|>system
You are Team #{team_id} specialist in a competitive game engine tournament. Output ONLY clean JavaScript code inside ```javascript ... ``` code fences. Do NOT re-declare variables that already exist in context. Do NOT add conversational prose.<|im_end|>
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
            "options": {"num_predict": num_predict, "temperature": 0.25},
            "stream": False
        }).encode(),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        elapsed = time.perf_counter() - t0
        raw = data.get("response", "")
        tokens = data.get("eval_count", 0)

        after_think = raw.split("</think>")[-1] if "</think>" in raw else raw
        m = re.findall(r"```(?:[a-zA-Z0-9_-]+)?\s*\n?(.*?)(?:```|$)", after_think, re.DOTALL)
        valid_blocks = [b.strip() for b in m if b.strip()]
        code = max(valid_blocks, key=len) if valid_blocks else after_think.strip()
        return {
            "team_id": team_id,
            "code": code,
            "elapsed": elapsed,
            "tokens": tokens,
            "error": None
        }
    except Exception as e:
        return {
            "team_id": team_id,
            "code": "",
            "elapsed": time.perf_counter() - t0,
            "tokens": 0,
            "error": str(e)
        }

def test_js_syntax(code_str):
    try:
        res = subprocess.run(
            ["node", "-e", "const vm = require('vm'); try { new vm.Script(process.argv[1]); } catch (e) { console.error(e.message); process.exit(1); }", code_str],
            capture_output=True, text=True, timeout=5
        )
        if res.returncode == 0:
            return True, "Valid"
        return False, res.stderr.strip() or res.stdout.strip()
    except Exception as e:
        return False, str(e)

def run_task_tournament(task_idx, task_name, task_prompt, cumulative_baseline=""):
    print(f"\n{'='*75}")
    print(f"🥊 TASK {task_idx}: {task_name.upper()} — 8-TEAM COMPETITION")
    print(f"{'='*75}")

    full_prompt = task_prompt
    if cumulative_baseline:
        full_prompt = (
            f"--- EXISTING CODE BASELINE (Do NOT re-declare these variables) ---\n"
            f"{cumulative_baseline}\n\n"
            f"--- TASK {task_idx} REQUIREMENT ---\n"
            f"{task_prompt}\n"
            f"Output ONLY the new functions/logic for Task {task_idx}."
        )

    print(f"   Dispatching Task {task_idx} to all 8 competing teams...")
    candidates = []
    # Run 4 at a time to optimize M1 GPU resource utilization
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(generate_code_candidate, i+1, task_name, full_prompt) for i in range(8)]
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            candidates.append(res)

    candidates.sort(key=lambda x: x["team_id"])

    # Syntax test and Jev Evaluation
    evaluated = []
    for c in candidates:
        team_id = c["team_id"]
        # Test cumulative syntax
        test_code = f"{cumulative_baseline}\n\n{c['code']}"
        valid, err_msg = test_js_syntax(test_code)
        
        # Jev Quality Audit
        audit_payload = {
            "state": f"## Task {task_idx}: {task_name} (Team {team_id})\n\n```javascript\n{c['code'][:1200]}\n```",
            "model": "jev-latest",
            "questions": {
                "correctness": {
                    "type": "noul",
                    "instructions": f"Does this code correctly implement {task_name} without redeclaring existing state variables?"
                },
                "quality_score": {
                    "type": "score",
                    "instructions": "Rate the code cleanliness, efficiency, and robustness from 0 (broken) to 3 (production-grade)",
                    "range": [0, 3],
                    "criteria": ["Broken / redundant", "Rough / minor issues", "Clean working code", "Elegantly engineered"]
                }
            }
        }
        res, t_jev = call_jev(audit_payload)
        ans = res.get("answers", {})
        noul = ans.get("correctness", {}).get("noul", 0.0)
        score = ans.get("quality_score", {}).get("score", 0.0)

        # Penalize syntax failure
        effective_score = score if valid else (score * 0.2)
        evaluated.append({
            "team_id": team_id,
            "code": c["code"],
            "elapsed": round(c["elapsed"], 2),
            "tokens": c["tokens"],
            "syntax_valid": valid,
            "syntax_error": err_msg if not valid else None,
            "noul": round(noul, 3),
            "score": round(score, 2),
            "effective_score": round(effective_score, 2)
        })
        status_icon = "✅" if valid else "❌"
        print(f"   Team {team_id}: {c['tokens']} tok in {c['elapsed']:.1f}s | Syntax: {status_icon} | Jev Noul: {noul:.2f} | Score: {score:.2f} (Effective: {effective_score:.2f})")

    # Select the Promoted Winner
    # Sort by syntax validity, then effective score
    valid_candidates = [e for e in evaluated if e["syntax_valid"]]
    if valid_candidates:
        winner = max(valid_candidates, key=lambda x: (x["effective_score"], x["noul"]))
    else:
        winner = max(evaluated, key=lambda x: x["effective_score"])

    print(f"\n   🏆 PROMOTED WINNER FOR TASK {task_idx}: Team #{winner['team_id']}")
    print(f"      Winning Score: {winner['score']}/3.0 | Noul: {winner['noul']} | Tokens: {winner['tokens']}")
    return winner, evaluated

def main():
    print("=" * 80)
    print("🧬 8-TEAM EVOLUTIONARY TASK-BY-TASK PROMOTION SWARM")
    print("   Project: Space Invaders Deluxe")
    print("   Infrastructure: 8 Teams Competing per Task -> Best-of-8 Promoted by Jev")
    print("   Model: huihui-qwen3.5:2b + TypeSafe AI System One (Jev)")
    print("=" * 80)

    out_dir = "benchmarks/evolutionary_swarm"
    os.makedirs(out_dir, exist_ok=True)
    t_global = time.perf_counter()

    tasks = [
        (
            1,
            "Player Cannon & Global State",
            "Write JavaScript code initializing the Space Invaders canvas and player:\n"
            "- Declare canvas and 2d context: `const canvas = document.getElementById('c'); const ctx = canvas.getContext('2d');`\n"
            "- Declare player: `let player = { x: 180, y: 450, width: 36, height: 16, speed: 6 };`\n"
            "- Declare game flags: `let score = 0, lives = 3, gameOver = false, gameWon = false;`\n"
            "- Function `updatePlayer(keys)` moving player left/right clamped between 0 and canvas.width (400)."
        ),
        (
            2,
            "Invader Fleet & Marching Vector Logic",
            "Write JavaScript for the invader fleet:\n"
            "- `let invaders = []; let invaderDir = 1; let invaderSpeed = 1.2;`\n"
            "- Function `initInvaders()` creating a 3-row x 6-col grid of invaders with x, y, width=28, height=18, alive=true, points=10.\n"
            "- Function `updateInvaders()` moving alive invaders by invaderDir * invaderSpeed. "
            "If any alive invader reaches < 10 or > 360, reverse invaderDir and drop all invaders down by 14px."
        ),
        (
            3,
            "Projectiles, Ballistics & Collision Grid",
            "Write JavaScript for bullets and collisions:\n"
            "- `let bullets = [];`\n"
            "- Function `shootBullet()` adding `{ x: player.x + player.width/2 - 2, y: player.y - 4, width: 4, height: 10, speed: 8 }` to bullets.\n"
            "- Function `updateBullets()` moving bullets up by speed, removing bullets off-screen (< 0).\n"
            "- Function `checkCollisions()` checking bounding box hit between bullets and alive invaders. On hit, set invader.alive = false, remove bullet, add points to score. If all invaders dead, set gameWon = true."
        ),
        (
            4,
            "Retro Neon Canvas Renderer & Main Game Loop",
            "Write JavaScript rendering and game loop:\n"
            "- Function `draw()` clearing canvas (400x500), drawing neon green player cannon, colored invader rectangles, and yellow bullets.\n"
            "- Function `drawHUD()` drawing Score and Lives at top, and 'GAME OVER' / 'VICTORY' if finished.\n"
            "- Setup keyboard event listeners for ArrowLeft, ArrowRight, and Spacebar calling shootBullet().\n"
            "- Function `gameLoop()` executing updaters when playing, draw(), drawHUD(), and `requestAnimationFrame(gameLoop)`."
        )
    ]

    cumulative_code = ""
    tournament_records = []

    for idx, name, prompt in tasks:
        winner, all_evals = run_task_tournament(idx, name, prompt, cumulative_code)
        tournament_records.append({
            "task_idx": idx,
            "task_name": name,
            "promoted_team_id": winner["team_id"],
            "promoted_score": winner["score"],
            "promoted_noul": winner["noul"],
            "teams": all_evals
        })
        # Append promoted code to cumulative foundation
        cumulative_code += f"\n\n// === PROMOTED FROM TASK {idx}: {name.upper()} (Team #{winner['team_id']}) ===\n" + winner["code"]

    # Wrap into Master Game HTML
    master_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Space Invaders Deluxe (8-Team Evolutionary Swarm)</title>
  <style>
    body {{
      background: #050811;
      color: #00ff88;
      font-family: monospace;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
      overflow: hidden;
    }}
    h1 {{ margin: 0 0 6px; font-size: 1.4rem; letter-spacing: 2px; text-shadow: 0 0 10px #00ff88; }}
    .badge {{ font-size: 0.8rem; color: #00f3ff; margin-bottom: 12px; }}
    canvas {{
      background: #080c18;
      border: 2px solid #00ff88;
      border-radius: 6px;
      box-shadow: 0 0 30px rgba(0, 255, 136, 0.3);
    }}
    .footer {{ margin-top: 10px; font-size: 0.85rem; color: #94a3b8; }}
  </style>
</head>
<body>
  <h1>👾 SPACE INVADERS // EVOLUTIONARY MASTER</h1>
  <div class="badge">Synthesized from 8-Team Evolutionary Promotion Tournament &bull; Governed by TypeSafe Jev</div>
  <canvas id="c" width="400" height="500"></canvas>
  <div class="footer">&larr; &rarr; / A D to Move &bull; SPACEBAR to Shoot</div>

  <script>
  {cumulative_code}

  // Safety boot trigger
  if (typeof initInvaders === 'function' && (!invaders || invaders.length === 0)) {{
    initInvaders();
  }}
  if (typeof gameLoop === 'function') {{
    requestAnimationFrame(gameLoop);
  }}
  </script>
</body>
</html>
"""
    master_path = os.path.join(out_dir, "master_game.html")
    with open(master_path, "w") as f:
        f.write(master_html)

    # Final Overall Audit
    print("\n" + "=" * 80)
    print("🏆 FINAL QUALITY AUDIT OF THE ASSEMBLED MASTER BUILD")
    print("=" * 80)
    final_audit, _ = call_jev({
        "state": f"## Master Evolutionary Game Build\n\n```html\n{master_html[:3000]}\n```",
        "model": "jev-latest",
        "questions": {
            "master_playability": {
                "type": "noul",
                "instructions": "Is this a complete, playable Space Invaders game with functional controls, marching invaders, laser ballistics, and collision detection?"
            },
            "master_quality_score": {
                "type": "score",
                "instructions": "Rate the overall cumulative architecture and code quality from 0 to 3",
                "range": [0, 3],
                "criteria": ["Broken", "Rough prototype", "Clean playable game", "Polished production-grade"]
            }
        }
    })
    fans = final_audit.get("answers", {})
    final_noul = round(fans.get("master_playability", {}).get("noul", 0.0), 3)
    final_score = round(fans.get("master_quality_score", {}).get("score", 0.0), 2)

    total_time = round(time.perf_counter() - t_global, 2)
    total_tokens = sum(sum(t["tokens"] for t in r["teams"]) for r in tournament_records)

    print(f"   Final Master Playability (Noul): {final_noul} {'✅ PASS' if final_noul >= 0.7 else '❌'}")
    print(f"   Final Master Quality Score: {final_score} / 3.0")
    print(f"   Total Wall-Clock Time: {total_time}s | Total Tokens: {total_tokens}")

    # Save summary report
    summary = {
        "architecture": "8-Team Evolutionary Task-by-Task Promotion Swarm",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_wall_clock_s": total_time,
        "total_tokens": total_tokens,
        "final_master_noul": final_noul,
        "final_master_quality_score": final_score,
        "promoted_stages": [
            {
                "task": r["task_name"],
                "winning_team": r["promoted_team_id"],
                "score": r["promoted_score"],
                "noul": r["promoted_noul"]
            }
            for r in tournament_records
        ],
        "tasks_detail": tournament_records,
        "master_game_path": master_path
    }
    with open(os.path.join(out_dir, "evolutionary_results.json"), "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n🎉 MASTER GAME BUILT: http://localhost:8080/evolutionary_swarm/master_game.html")

if __name__ == "__main__":
    main()
