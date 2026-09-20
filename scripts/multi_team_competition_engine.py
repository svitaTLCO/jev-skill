#!/usr/bin/env python3
"""
Multi-Team Swarm + Jev Competition Engine
Each team independently executes the full (Agent Swarm + Jev Orchestrator) pipeline
competing on the identical task: Space Invaders Deluxe.
"""

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

def get_jev_key():
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

KEY = get_jev_key()

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

def generate_worker_code(prompt, num_predict=1000):
    t0 = time.perf_counter()
    chatml = f"""<|im_start|>system
You are a precise JavaScript game developer. Output ONLY valid JavaScript code enclosed in ```javascript ... ``` code fences. Do NOT add conversational prose.<|im_end|>
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
            "options": {"num_predict": num_predict, "temperature": 0.2},
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
        return code, elapsed, tokens
    except Exception as e:
        return "", time.perf_counter() - t0, 0

def check_js_syntax(code_str):
    try:
        res = subprocess.run(
            ["node", "-e", "const vm = require('vm'); try { new vm.Script(process.argv[1]); } catch (e) { console.error(e.message); process.exit(1); }", code_str],
            capture_output=True, text=True, timeout=5
        )
        if res.returncode == 0:
            return True, "Valid syntax"
        err = res.stderr.strip() or res.stdout.strip()
        return False, err
    except Exception as e:
        return False, str(e)

class CompetitiveTeam:
    def __init__(self, team_id, team_name, base_dir):
        self.team_id = team_id
        self.team_name = team_name
        self.team_dir = os.path.join(base_dir, f"team_{team_id}_{team_name.lower()}")
        os.makedirs(self.team_dir, exist_ok=True)
        self.metrics = {
            "team_id": team_id,
            "team_name": team_name,
            "total_tokens": 0,
            "total_time_s": 0.0,
            "jev_gate_overhead_s": 0.0,
            "worker_scores": {},
            "final_noul": 0.0,
            "final_quality_score": 0.0,
            "syntax_valid": False
        }

    def run_team_pipeline(self):
        t_start = time.perf_counter()
        print(f"\n{'='*70}")
        print(f"🚀 [Team {self.team_id}: {self.team_name}] Starting Swarm + Jev Pipeline")
        print(f"{'='*70}")

        # --- JEV PHASE 0: Team Architectural Blueprint (Jev Choice) ---
        print(f"   [Team {self.team_id}] Jev Blueprint: Selecting architectural pattern...")
        arch_res, t_arch = call_jev({
            "state": f"Team {self.team_id} ({self.team_name}) is building Space Invaders Deluxe.",
            "model": "jev-latest",
            "questions": {
                "pattern": {
                    "type": "choice",
                    "instructions": "Select the optimal game architecture pattern for micro-specialists",
                    "criteria": {
                        "modular_state": "Single clean global state object with modular updater functions.",
                        "entity_component": "Independent entity arrays with functional update passes."
                    }
                }
            }
        })
        self.metrics["jev_gate_overhead_s"] += t_arch
        selected_pattern = arch_res.get("answers", {}).get("pattern", {}).get("choice", "modular_state")
        print(f"   [Team {self.team_id}] Jev selected: '{selected_pattern}' ({t_arch*1000:.1f}ms)")

        # --- WORKER 1: Player Cannon & Movement Physics ---
        print(f"   [Team {self.team_id}] Micro-Worker 1: Player Cannon...")
        p1 = (
            "Write JavaScript code for the player cannon in Space Invaders:\n"
            "- Declare canvas and 2d context: `const canvas = document.getElementById('c'); const ctx = canvas.getContext('2d');`\n"
            "- Declare player object: `let player = { x: 180, y: 450, width: 40, height: 18, speed: 6 };`\n"
            "- Function `updatePlayer(keys)` moving player left/right with ArrowLeft/KeyA and ArrowRight/KeyD clamped to canvas width (400px).\n"
            "Output ONLY the JavaScript code."
        )
        code1, t1, tok1 = generate_worker_code(p1)
        self.metrics["total_tokens"] += tok1
        
        # Jev Micro-Gate 1
        g1, tg1 = call_jev({
            "state": f"## Worker 1 Output:\n```javascript\n{code1}\n```",
            "model": "jev-latest",
            "questions": {
                "valid": {"type": "noul", "instructions": "Does this define a valid player object and updatePlayer function without syntax errors?"}
            }
        })
        self.metrics["jev_gate_overhead_s"] += tg1
        noul1 = g1.get("answers", {}).get("valid", {}).get("noul", 0.0)
        print(f"      -> Worker 1: {len(code1)} chars in {t1:.2f}s ({tok1} tok) | Jev Gate: {noul1:.2f}")
        self.metrics["worker_scores"]["worker1_player"] = noul1

        # --- WORKER 2: Invaders Fleet Generation & Marching Vector ---
        print(f"   [Team {self.team_id}] Micro-Worker 2: Invader Fleet & Marching...")
        p2 = (
            "Write JavaScript code for the invader fleet in Space Invaders:\n"
            "- `let invaders = []; let invaderDir = 1; let invaderSpeed = 1.2;`\n"
            "- Function `initInvaders()` generating a 3-row x 6-column grid of invaders with x, y, width=28, height=18, alive=true, points=10.\n"
            "- Function `updateInvaders()` moving all alive invaders horizontally by invaderDir * invaderSpeed. "
            "If any alive invader reaches the left edge (< 10) or right edge (> 360), reverse invaderDir and drop all invaders down by 14px.\n"
            "Output ONLY the JavaScript code."
        )
        code2, t2, tok2 = generate_worker_code(p2)
        self.metrics["total_tokens"] += tok2

        # Jev Micro-Gate 2
        g2, tg2 = call_jev({
            "state": f"## Worker 2 Output:\n```javascript\n{code2}\n```",
            "model": "jev-latest",
            "questions": {
                "valid": {"type": "noul", "instructions": "Does this correctly implement initInvaders and updateInvaders with edge-bounce and drop logic?"}
            }
        })
        self.metrics["jev_gate_overhead_s"] += tg2
        noul2 = g2.get("answers", {}).get("valid", {}).get("noul", 0.0)
        print(f"      -> Worker 2: {len(code2)} chars in {t2:.2f}s ({tok2} tok) | Jev Gate: {noul2:.2f}")
        self.metrics["worker_scores"]["worker2_fleet"] = noul2

        # --- WORKER 3: Projectiles & Collision Detection ---
        print(f"   [Team {self.team_id}] Micro-Worker 3: Ballistics & Collision Grid...")
        p3 = (
            "Write JavaScript code for bullets and collisions in Space Invaders:\n"
            "- `let bullets = []; let score = 0; let lives = 3; let gameOver = false; let gameWon = false;`\n"
            "- Function `shootBullet()` adding `{ x: player.x + player.width/2 - 2, y: player.y - 4, width: 4, height: 10, speed: 8 }` to bullets array.\n"
            "- Function `updateBullets()` moving bullets up by speed, removing off-screen bullets (< 0).\n"
            "- Function `checkCollisions()` checking AABB collision between each bullet and each alive invader. "
            "On hit, set invader.alive = false, remove bullet, and add invader.points to score. If all invaders dead, set gameWon = true.\n"
            "Output ONLY the JavaScript code."
        )
        code3, t3, tok3 = generate_worker_code(p3)
        self.metrics["total_tokens"] += tok3

        # Jev Micro-Gate 3
        g3, tg3 = call_jev({
            "state": f"## Worker 3 Output:\n```javascript\n{code3}\n```",
            "model": "jev-latest",
            "questions": {
                "valid": {"type": "noul", "instructions": "Does this implement shootBullet, updateBullets, and checkCollisions correctly mutating score and alive status?"}
            }
        })
        self.metrics["jev_gate_overhead_s"] += tg3
        noul3 = g3.get("answers", {}).get("valid", {}).get("noul", 0.0)
        print(f"      -> Worker 3: {len(code3)} chars in {t3:.2f}s ({tok3} tok) | Jev Gate: {noul3:.2f}")
        self.metrics["worker_scores"]["worker3_bullets"] = noul3

        # --- WORKER 4: Retro Neon Renderer & HUD ---
        print(f"   [Team {self.team_id}] Micro-Worker 4: Retro Canvas Renderer...")
        p4 = (
            "Write JavaScript rendering code for Space Invaders (Canvas 400x500):\n"
            "- Function `draw()` clearing canvas, drawing retro green player cannon, colored invader rectangles (neon cyan/magenta), and yellow bullets.\n"
            "- Function `drawHUD()` drawing Score and Lives at the top in monospace font, and 'GAME OVER' or 'YOU WIN' if game finished.\n"
            "Output ONLY the JavaScript functions."
        )
        code4, t4, tok4 = generate_worker_code(p4)
        self.metrics["total_tokens"] += tok4

        # Jev Micro-Gate 4
        g4, tg4 = call_jev({
            "state": f"## Worker 4 Output:\n```javascript\n{code4}\n```",
            "model": "jev-latest",
            "questions": {
                "valid": {"type": "noul", "instructions": "Does this define valid draw() and drawHUD() functions rendering player, invaders, bullets, and score?"}
            }
        })
        self.metrics["jev_gate_overhead_s"] += tg4
        noul4 = g4.get("answers", {}).get("valid", {}).get("noul", 0.0)
        print(f"      -> Worker 4: {len(code4)} chars in {t4:.2f}s ({tok4} tok) | Jev Gate: {noul4:.2f}")
        self.metrics["worker_scores"]["worker4_renderer"] = noul4

        # --- TEAM ASSEMBLY & GAME PACKAGING ---
        print(f"   [Team {self.team_id}] Assembling team deliverable...")
        combined_js = f"""
// --- Team {self.team_id} ({self.team_name}) Game Implementation ---

// 1. Player
{code1}

// 2. Invaders Fleet
{code2}

// 3. Bullets & Collisions
{code3}

// 4. Renderer & HUD
{code4}

// Initialize invaders
if (typeof initInvaders === 'function') {{
  initInvaders();
}}

// Keyboard Controls
const keys = {{}};
window.addEventListener('keydown', e => {{
  keys[e.key] = true;
  keys[e.code] = true;
  if (e.code === 'Space' && !gameOver && !gameWon) {{
    if (typeof shootBullet === 'function') shootBullet();
  }}
}});
window.addEventListener('keyup', e => {{
  keys[e.key] = false;
  keys[e.code] = false;
}});

// Main Game Loop
function gameLoop() {{
  if (!gameOver && !gameWon) {{
    if (typeof updatePlayer === 'function') updatePlayer(keys);
    if (typeof updateInvaders === 'function') updateInvaders();
    if (typeof updateBullets === 'function') updateBullets();
    if (typeof checkCollisions === 'function') checkCollisions();
  }}
  if (typeof draw === 'function') draw();
  if (typeof drawHUD === 'function') drawHUD();
  requestAnimationFrame(gameLoop);
}}
requestAnimationFrame(gameLoop);
"""
        is_syntax_valid, syntax_err = check_js_syntax(combined_js)
        if not is_syntax_valid:
            print(f"      ⚠️ Team {self.team_id} syntax issue: {syntax_err[:80]}. Applying Jev compiler-in-the-loop repair...")
            p_repair = f"""Fix syntax error in this JavaScript Space Invaders game:
Error: {syntax_err}
Code:
{combined_js}
Return ONLY valid JavaScript."""
            repaired_js, _, tokh = generate_worker_code(p_repair, num_predict=1200)
            self.metrics["total_tokens"] += tokh
            is_valid_h, _ = check_js_syntax(repaired_js)
            if is_valid_h:
                combined_js = repaired_js
                is_syntax_valid = True

        self.metrics["syntax_valid"] = is_syntax_valid

        # Full HTML file
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Space Invaders Deluxe - Team {self.team_id} ({self.team_name})</title>
  <style>
    body {{
      background: #060913;
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
    h2 {{ margin: 0 0 6px 0; font-size: 1.3rem; letter-spacing: 2px; text-shadow: 0 0 10px #00ff88; }}
    .badge {{ font-size: 0.8rem; color: #00f3ff; margin-bottom: 10px; }}
    canvas {{
      background: #0a0e1a;
      border: 2px solid #00ff88;
      border-radius: 6px;
      box-shadow: 0 0 25px rgba(0, 255, 136, 0.25);
    }}
    .footer {{ margin-top: 10px; font-size: 0.8rem; color: #94a3b8; }}
  </style>
</head>
<body>
  <h2>👾 SPACE INVADERS // {self.team_name.upper()}</h2>
  <div class="badge">Team #{self.team_id} &bull; Powered by Swarm + Jev Pipeline</div>
  <canvas id="c" width="400" height="500"></canvas>
  <div class="footer">&larr; &rarr; or A / D to Move &bull; SPACEBAR to Shoot</div>

  <script>
  {combined_js}
  </script>
</body>
</html>
"""
        game_path = os.path.join(self.team_dir, "space_invaders.html")
        with open(game_path, "w") as f:
            f.write(html_content)

        self.metrics["total_time_s"] = round(time.perf_counter() - t_start, 2)
        self.metrics["artifact_path"] = game_path
        self.metrics["combined_js"] = combined_js
        self.metrics["html_content"] = html_content

        # --- JEV FINAL TEAM EVALUATION ---
        print(f"   [Team {self.team_id}] Jev Final Quality Audit on complete build...")
        audit_res, ta = call_jev({
            "state": f"## Complete Space Invaders Game by Team {self.team_id} ({self.team_name})\n```javascript\n{combined_js[:2500]}\n```",
            "model": "jev-latest",
            "questions": {
                "playability": {
                    "type": "noul",
                    "instructions": "Is this a complete, playable Space Invaders game with functional player movement, marching invaders, laser ballistics, and collision detection?"
                },
                "code_quality": {
                    "type": "score",
                    "instructions": "Rate the code cleanliness, modularity, and correctness from 0 (broken) to 3 (production-grade)",
                    "range": [0, 3],
                    "criteria": ["Broken / unplayable", "Rough prototype", "Clean playable game", "Polished production-grade"]
                }
            }
        })
        self.metrics["jev_gate_overhead_s"] += ta
        fans = audit_res.get("answers", {})
        self.metrics["final_noul"] = round(fans.get("playability", {}).get("noul", 0.0), 3)
        self.metrics["final_quality_score"] = round(fans.get("code_quality", {}).get("score", 0.0), 2)

        print(f"   🏁 [Team {self.team_id}: {self.team_name}] Completed in {self.metrics['total_time_s']}s | Tokens: {self.metrics['total_tokens']}")
        print(f"      -> Final Jev Playable Noul: {self.metrics['final_noul']} | Quality Score: {self.metrics['final_quality_score']}/3.0")
        return self.metrics

def build_competition_leaderboard(team_metrics, out_dir):
    dash_path = os.path.join(out_dir, "leaderboard.html")
    sorted_teams = sorted(team_metrics, key=lambda x: (x["final_noul"] >= 0.7, x["final_quality_score"]), reverse=True)
    winner = sorted_teams[0]

    cards_html = ""
    for idx, t in enumerate(sorted_teams):
        is_winner = t["team_id"] == winner["team_id"]
        border_color = "#00ff88" if is_winner else "#00f3ff"
        rank_badge = "👑 1st PLACE (WINNER)" if idx == 0 else f"#{idx+1} PLACE"
        preview_rel = f"team_{t['team_id']}_{t['team_name'].lower()}/space_invaders.html"

        cards_html += f"""
        <div class="team-card" style="border-color: {border_color};">
          <div class="card-top">
            <div>
              <div class="rank-tag" style="color: {border_color};">{rank_badge}</div>
              <div class="team-name">Team {t['team_name']}</div>
              <div class="team-meta">Time: {t['total_time_s']}s &bull; Tokens: {t['total_tokens']} &bull; Jev Overhead: {t['jev_gate_overhead_s']:.2f}s</div>
            </div>
            <div class="score-box">
              <div class="score-val">{t['final_quality_score']} / 3.0</div>
              <div class="noul-val">Noul: {t['final_noul']}</div>
            </div>
          </div>
          
          <div class="gates-row">
            <span>Player: <strong>{t['worker_scores'].get('worker1_player', 0.0):.2f}</strong></span>
            <span>Fleet: <strong>{t['worker_scores'].get('worker2_fleet', 0.0):.2f}</strong></span>
            <span>Bullets: <strong>{t['worker_scores'].get('worker3_bullets', 0.0):.2f}</strong></span>
            <span>Renderer: <strong>{t['worker_scores'].get('worker4_renderer', 0.0):.2f}</strong></span>
          </div>

          <div class="game-frame">
            <iframe src="{preview_rel}" scrolling="no"></iframe>
          </div>

          <a href="{preview_rel}" target="_blank" class="play-link">🎮 PLAY FULLSCREEN</a>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>🏆 MULTI-TEAM SWARM + JEV COMPETITION LEADERBOARD</title>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&family=Orbitron:wght@700;900&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #050811;
      --card-bg: rgba(11, 16, 30, 0.85);
      --green: #00ff88;
      --cyan: #00f3ff;
      --pink: #ff007f;
      --dim: #94a3b8;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      background-image: radial-gradient(circle at 50% 0%, rgba(0, 255, 136, 0.08) 0%, transparent 70%);
      color: #e2e8f0;
      font-family: 'JetBrains Mono', monospace;
      padding: 2rem;
    }}
    header {{
      text-align: center;
      margin-bottom: 2rem;
    }}
    h1 {{
      font-family: 'Orbitron', sans-serif;
      font-size: 2.2rem;
      letter-spacing: 3px;
      color: #fff;
      text-shadow: 0 0 25px rgba(0, 255, 136, 0.4);
    }}
    .sub {{ color: var(--dim); margin-top: 0.5rem; font-size: 0.95rem; }}
    .winner-banner {{
      max-width: 820px;
      margin: 1.5rem auto 0;
      background: rgba(0, 255, 136, 0.08);
      border: 1px solid var(--green);
      padding: 1rem 1.5rem;
      border-radius: 8px;
      box-shadow: 0 0 25px rgba(0, 255, 136, 0.15);
      font-size: 1rem;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
      gap: 1.5rem;
    }}
    .team-card {{
      background: var(--card-bg);
      border: 2px solid var(--cyan);
      border-radius: 12px;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
      backdrop-filter: blur(10px);
    }}
    .card-top {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }}
    .rank-tag {{ font-size: 0.8rem; font-weight: 800; letter-spacing: 1px; }}
    .team-name {{
      font-family: 'Orbitron', sans-serif;
      font-size: 1.3rem;
      color: #fff;
      margin-top: 3px;
    }}
    .team-meta {{ font-size: 0.75rem; color: var(--dim); margin-top: 2px; }}
    .score-box {{ text-align: right; }}
    .score-val {{
      font-family: 'Orbitron', sans-serif;
      font-size: 1.25rem;
      color: var(--green);
      font-weight: 900;
    }}
    .noul-val {{ font-size: 0.8rem; color: var(--cyan); margin-top: 2px; }}
    .gates-row {{
      display: flex;
      justify-content: space-between;
      font-size: 0.75rem;
      background: rgba(0,0,0,0.35);
      padding: 0.5rem 0.75rem;
      border-radius: 6px;
    }}
    .game-frame {{
      height: 480px;
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 8px;
      overflow: hidden;
      background: #060913;
    }}
    iframe {{ width: 100%; height: 100%; border: none; }}
    .play-link {{
      text-align: center;
      background: rgba(0,255,136,0.1);
      border: 1px solid var(--green);
      color: var(--green);
      padding: 0.65rem;
      border-radius: 6px;
      text-decoration: none;
      font-weight: 700;
      font-size: 0.85rem;
      transition: all 0.2s;
    }}
    .play-link:hover {{
      background: var(--green);
      color: #050811;
      box-shadow: 0 0 16px rgba(0,255,136,0.4);
    }}
  </style>
</head>
<body>
  <header>
    <h1>🏆 SWARM + JEV MULTI-TEAM ARENA</h1>
    <div class="sub">Identical Challenge: Space Invaders Deluxe &bull; Autonomous Swarm + Jev Gating per Team</div>
    <div class="winner-banner">
      🥇 <strong>Grand Champion:</strong> Team {winner['team_name']} | 
      Jev Quality Score: <strong>{winner['final_quality_score']} / 3.0</strong> | 
      Playable Probability (Noul): <strong>{winner['final_noul']}</strong>
    </div>
  </header>

  <div class="grid">
    {cards_html}
  </div>
</body>
</html>
"""
    with open(dash_path, "w") as f:
        f.write(html)
    return dash_path
