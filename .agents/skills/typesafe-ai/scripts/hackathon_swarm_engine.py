#!/usr/bin/env python3
"""
Competitive Teams Hackathon Swarm Engine
Deploying 24 Micro-Agents across 6 Isolated Teams (4 Specialists per Team)
Supreme Jury: TypeSafe AI System One (Jev)
Hardware Optimization: Apple Silicon M1 (16GB RAM)
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
MODEL_2B = "huihui-qwen3.5:2b"
MODEL_08B = "huihui-qwen3.5:0.8b"
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

def generate_slm_code(model, prompt, lang="javascript", num_predict=650):
    t0 = time.perf_counter()
    chatml = f"""<|im_start|>system
You are a specialist coding agent. Output ONLY valid {lang} code inside ```{lang} ... ``` code fences. Do NOT add conversational prose.<|im_end|>
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
        return code, elapsed, tokens, None
    except Exception as e:
        return "", time.perf_counter() - t0, 0, str(e)

def validate_js_syntax(code_str):
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

class TeamPipeline:
    def __init__(self, team_id, team_name, architectural_theme, base_dir):
        self.team_id = team_id
        self.team_name = team_name
        self.theme = architectural_theme
        self.team_dir = os.path.join(base_dir, f"team_{team_id}")
        os.makedirs(self.team_dir, exist_ok=True)
        self.metrics = {
            "team_id": team_id,
            "team_name": team_name,
            "theme": architectural_theme,
            "tokens": 0,
            "total_time_s": 0.0,
            "syntax_valid": False,
            "healed": False
        }

    def execute_team_lifecycle(self):
        t_start = time.perf_counter()
        print(f"   🚩 [Team {self.team_id}: {self.team_name}] Starting lifecycle ({self.theme})...")

        # --- Agent 1: Lead Architect (2B) ---
        p_arch = f"""Team {self.team_id} ({self.team_name}) Challenge: Cyberpunk Neon Breakout Arcade Game.
Architectural Style: {self.theme}.
Define the global state and contracts for the game in JavaScript:
- `const canvas = document.getElementById('c'); const ctx = canvas.getContext('2d');`
- `let paddle = {{ x: 200, y: 460, width: 80, height: 12, speed: 7 }};`
- `let ball = {{ x: 240, y: 300, vx: 4, vy: -4, radius: 6 }};`
- `let bricks = []; const rows = 4, cols = 8;` (initialize rows/cols brick grid with x, y, width=48, height=16, alive=true)
- `let score = 0, lives = 3, gameOver = false, gameWon = false;`
Output ONLY clean JavaScript declarations for state initialization and brick generation.
"""
        code_arch, t1, tok1, err1 = generate_slm_code(MODEL_2B, p_arch, num_predict=500)
        self.metrics["tokens"] += tok1

        # --- Agent 2: Engine Specialist (2B) ---
        p_eng = f"""Write JavaScript update and physics functions for Breakout matching state:
{code_arch[:400]}

Provide:
1. `function updatePaddle(keys)` moving paddle within canvas boundaries (0 to 480).
2. `function updateBall()` updating ball position, bouncing off walls (left, right, top), bouncing off paddle, and losing a life if falling below bottom.
3. `function checkBrickCollisions()` checking ball collision with alive bricks, setting alive=false and incrementing score.
Output ONLY JavaScript functions. No extra explanation.
"""
        code_eng, t2, tok2, err2 = generate_slm_code(MODEL_2B, p_eng, num_predict=600)
        self.metrics["tokens"] += tok2

        # --- Agent 3: Renderer Specialist (2B) ---
        p_rend = f"""Write JavaScript rendering functions for Cyberpunk Neon Breakout:
Canvas is 480x500. Dark background `#070b14`.
Provide:
1. `function draw()` clearing canvas, drawing glowing neon paddle, ball, and colored brick grid (use bright cyan, magenta, and neon green).
2. `function drawHUD()` showing score and lives in retro monospace font.
Output ONLY JavaScript functions.
"""
        code_rend, t3, tok3, err3 = generate_slm_code(MODEL_2B, p_rend, num_predict=550)
        self.metrics["tokens"] += tok3

        # --- Agent 4: QA & Assembler (0.8B) ---
        # Assemble game HTML
        combined_js = f"""
{code_arch}

{code_eng}

{code_rend}

// Key listeners & Main Loop
const keys = {{}};
window.addEventListener('keydown', e => {{ keys[e.key] = true; keys[e.code] = true; }});
window.addEventListener('keyup', e => {{ keys[e.key] = false; keys[e.code] = false; }});

function loop() {{
  if (!gameOver && !gameWon) {{
    if (typeof updatePaddle === 'function') updatePaddle(keys);
    if (typeof updateBall === 'function') updateBall();
    if (typeof checkBrickCollisions === 'function') checkBrickCollisions();
  }}
  if (typeof draw === 'function') draw();
  if (typeof drawHUD === 'function') drawHUD();
  requestAnimationFrame(loop);
}}
requestAnimationFrame(loop);
"""
        # Node syntax check
        valid, syntax_err = validate_js_syntax(combined_js)
        if not valid:
            print(f"      ⚠️ Team {self.team_id} syntax issue: {syntax_err[:100]}. Triggering self-healing...")
            p_heal = f"""Fix this JavaScript syntax error:
Error: {syntax_err}
Code:
{combined_js[:1000]}
Return ONLY the corrected valid JavaScript code.
"""
            healed_js, th, tokh, _ = generate_slm_code(MODEL_08B, p_heal, num_predict=800)
            self.metrics["tokens"] += tokh
            valid_h, _ = validate_js_syntax(healed_js)
            if valid_h:
                combined_js = healed_js
                valid = True
                self.metrics["healed"] = True

        self.metrics["syntax_valid"] = valid

        # Wrap in full HTML5 application
        html_code = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Cyberpunk Breakout - Team {self.team_id} ({self.team_name})</title>
  <style>
    body {{
      background: #050811;
      color: #00f3ff;
      font-family: 'Courier New', monospace;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
      overflow: hidden;
    }}
    .title {{ font-size: 1.3rem; margin-bottom: 6px; letter-spacing: 2px; text-shadow: 0 0 10px #00f3ff; }}
    .badge {{ font-size: 0.75rem; color: #ff007f; margin-bottom: 10px; }}
    canvas {{
      background: #070b14;
      border: 2px solid #00f3ff;
      border-radius: 8px;
      box-shadow: 0 0 25px rgba(0, 243, 255, 0.25);
    }}
    .controls {{ margin-top: 10px; font-size: 0.8rem; color: #94a3b8; }}
  </style>
</head>
<body>
  <div class="title">⚡ CYBER-BREAKOUT // {self.team_name.upper()}</div>
  <div class="badge">Team #{self.team_id} &bull; Architecture: {self.theme}</div>
  <canvas id="c" width="480" height="500"></canvas>
  <div class="controls">&larr; &rarr; or A / D to Move Paddle &bull; ESC to Restart</div>

  <script>
  {combined_js}
  </script>
</body>
</html>
"""
        artifact_path = os.path.join(self.team_dir, "index.html")
        with open(artifact_path, "w") as f:
            f.write(html_code)

        self.metrics["total_time_s"] = round(time.perf_counter() - t_start, 2)
        self.metrics["artifact_path"] = artifact_path
        self.metrics["html_code"] = html_code
        self.metrics["combined_js"] = combined_js

        status = "✅ PASS" if valid else "❌ SYNTAX ERROR"
        print(f"   🏁 [Team {self.team_id}: {self.team_name}] Finished in {self.metrics['total_time_s']}s ({self.metrics['tokens']} tok) | {status}")
        return self.metrics

def evaluate_teams_with_jev(team_results):
    print("\n" + "=" * 80)
    print("⚖️ SUPREME HACKATHON JURY: TYPESAFE JEV SYSTEM ONE")
    print("=" * 80)

    jury_scorecard = []

    for team in team_results:
        print(f"   Evaluating Team {team['team_id']}: {team['team_name']}...")
        payload = {
            "state": f"## Team {team['team_id']} ({team['team_name']}) - Style: {team['theme']}\n\n```javascript\n{team['combined_js'][:1800]}\n```",
            "model": "jev-latest",
            "questions": {
                "spec_compliance": {
                    "type": "noul",
                    "instructions": "Does this JavaScript code implement complete Breakout game logic (paddle, ball physics, brick collision, rendering) without fatal syntax flaws?"
                },
                "code_quality": {
                    "type": "score",
                    "instructions": "Rate the code structure, maintainability, and architectural elegance from 0 (broken) to 3 (production-grade)",
                    "range": [0, 3],
                    "criteria": ["Broken code", "Fragile / syntax gaps", "Clean working prototype", "Production-grade elegance"]
                }
            }
        }
        res, t_jev = call_jev(payload)
        ans = res.get("answers", {})
        noul_val = ans.get("spec_compliance", {}).get("noul", 0.0)
        score_val = ans.get("code_quality", {}).get("score", 0.0)

        jury_scorecard.append({
            "team_id": team["team_id"],
            "team_name": team["team_name"],
            "theme": team["theme"],
            "syntax_valid": team["syntax_valid"],
            "noul_compliance": round(noul_val, 3),
            "quality_score": round(score_val, 2),
            "wall_time_s": team["total_time_s"],
            "tokens": team["tokens"],
            "artifact_path": team["artifact_path"]
        })
        print(f"      -> Jev Noul: {noul_val:.3f} | Score: {score_val:.2f}/3.0 (in {t_jev*1000:.1f}ms)")

    # Grand Champion Choice Selection
    qualified_teams = [t for t in jury_scorecard if t["syntax_valid"] and t["noul_compliance"] >= 0.60]
    if not qualified_teams:
        qualified_teams = jury_scorecard

    criteria_dict = {
        f"team_{t['team_id']}": f"{t['team_name']} ({t['theme']}): Score {t['quality_score']}, Noul {t['noul_compliance']}"
        for t in qualified_teams
    }

    choice_payload = {
        "state": f"Select the ultimate Grand Champion of the Cyberpunk Breakout Hackathon among surviving teams:\n{json.dumps(criteria_dict, indent=2)}",
        "model": "jev-latest",
        "questions": {
            "grand_champion": {
                "type": "choice",
                "instructions": "Select the single winning team with the highest quality and balance of architecture, physics, and gameplay soundness",
                "criteria": criteria_dict
            }
        }
    }
    choice_res, _ = call_jev(choice_payload)
    winner_key = choice_res.get("answers", {}).get("grand_champion", {}).get("choice", list(criteria_dict.keys())[0])

    winner_team_id = int(winner_key.replace("team_", ""))
    winner_team = next(t for t in jury_scorecard if t["team_id"] == winner_team_id)

    print("\n" + "=" * 80)
    print(f"🏆 GRAND CHAMPION PROCLAIMED: Team {winner_team['team_id']} - {winner_team['team_name'].upper()}!")
    print(f"   Architecture Style: {winner_team['theme']}")
    print(f"   Jev Quality Score: {winner_team['quality_score']} / 3.0 | Noul Compliance: {winner_team['noul_compliance']}")
    print("=" * 80)

    return jury_scorecard, winner_team

def build_hackathon_dashboard(jury_scorecard, winner_team, out_dir):
    dash_path = os.path.join(out_dir, "leaderboard.html")

    cards_html = ""
    for t in sorted(jury_scorecard, key=lambda x: x["quality_score"], reverse=True):
        is_winner = t["team_id"] == winner_team["team_id"]
        border_color = "#ff007f" if is_winner else ("#00f3ff" if t["syntax_valid"] else "#ef4444")
        crown = "👑 GRAND CHAMPION" if is_winner else f"TEAM #{t['team_id']}"
        preview_url = f"team_{t['team_id']}/index.html"

        cards_html += f"""
        <div class="card" style="border-color: {border_color};">
          <div class="card-header">
            <div>
              <div class="badge" style="color: {border_color};">{crown}</div>
              <div class="team-title">{t['team_name']}</div>
              <div class="theme-tag">{t['theme']}</div>
            </div>
            <div class="score-pill">{t['quality_score']} / 3.0</div>
          </div>
          <div class="meta-row">
            <span>Noul: <strong>{t['noul_compliance']}</strong></span>
            <span>Time: <strong>{t['wall_time_s']}s</strong></span>
            <span>Tokens: <strong>{t['tokens']}</strong></span>
            <span>Syntax: <strong style="color: {'#00ff88' if t['syntax_valid'] else '#ef4444'};">{'PASS' if t['syntax_valid'] else 'FAIL'}</strong></span>
          </div>
          <div class="preview-box">
            <iframe src="{preview_url}" scrolling="no"></iframe>
          </div>
          <a href="{preview_url}" target="_blank" class="play-btn">🎮 LAUNCH FULLSCREEN</a>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>⚡ SWARM HACKATHON ARENA // 24-AGENT SQUAD COMPETITION</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Orbitron:wght@700;900&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #050811;
      --card-bg: rgba(10, 15, 26, 0.85);
      --cyan: #00f3ff;
      --pink: #ff007f;
      --green: #00ff88;
      --dim: #94a3b8;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      background-image: radial-gradient(ellipse at 50% 0%, rgba(0,243,255,0.1) 0%, transparent 70%);
      color: #e2e8f0;
      font-family: 'JetBrains Mono', monospace;
      padding: 2rem;
    }}
    header {{
      text-align: center;
      margin-bottom: 2.5rem;
    }}
    h1 {{
      font-family: 'Orbitron', sans-serif;
      font-size: 2rem;
      letter-spacing: 3px;
      color: #fff;
      text-shadow: 0 0 20px rgba(0, 243, 255, 0.4);
    }}
    .sub {{ color: var(--dim); font-size: 0.9rem; margin-top: 0.5rem; }}
    .jury-box {{
      max-width: 800px;
      margin: 1.5rem auto 0;
      background: rgba(255, 0, 127, 0.08);
      border: 1px solid var(--pink);
      padding: 1rem 1.5rem;
      border-radius: 8px;
      box-shadow: 0 0 20px rgba(255, 0, 127, 0.15);
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
      gap: 1.5rem;
    }}
    .card {{
      background: var(--card-bg);
      border: 2px solid var(--cyan);
      border-radius: 10px;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
      backdrop-filter: blur(10px);
      transition: transform 0.2s;
    }}
    .card:hover {{ transform: translateY(-3px); }}
    .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; }}
    .badge {{ font-size: 0.75rem; font-weight: 700; letter-spacing: 1px; }}
    .team-title {{ font-family: 'Orbitron', sans-serif; font-size: 1.15rem; color: #fff; margin-top: 2px; }}
    .theme-tag {{ font-size: 0.75rem; color: var(--dim); }}
    .score-pill {{
      font-family: 'Orbitron', sans-serif;
      font-size: 1.2rem;
      color: var(--green);
      background: rgba(0,255,136,0.1);
      padding: 0.3rem 0.75rem;
      border-radius: 6px;
      border: 1px solid rgba(0,255,136,0.3);
    }}
    .meta-row {{
      display: flex;
      justify-content: space-between;
      font-size: 0.78rem;
      background: rgba(0,0,0,0.35);
      padding: 0.5rem 0.75rem;
      border-radius: 6px;
    }}
    .preview-box {{
      height: 380px;
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 6px;
      overflow: hidden;
      background: #000;
    }}
    iframe {{ width: 100%; height: 100%; border: none; }}
    .play-btn {{
      text-align: center;
      background: rgba(0,243,255,0.12);
      border: 1px solid var(--cyan);
      color: var(--cyan);
      padding: 0.6rem;
      border-radius: 6px;
      text-decoration: none;
      font-weight: 700;
      font-size: 0.85rem;
      transition: all 0.2s;
    }}
    .play-btn:hover {{ background: var(--cyan); color: #050811; }}
  </style>
</head>
<body>
  <header>
    <h1>⚡ SWARM HACKATHON ARENA</h1>
    <div class="sub">24 Autonomous Specialists &bull; 6 Competing Teams &bull; Governed by TypeSafe AI System One</div>
    <div class="jury-box">
      🏆 <strong>Grand Champion:</strong> Team {winner_team['team_id']} - {winner_team['team_name']} ({winner_team['theme']}) |
      Jev Score: <strong>{winner_team['quality_score']} / 3.0</strong> | Noul Soundness: <strong>{winner_team['noul_compliance']}</strong>
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
    print(f"\n📊 Hackathon Arena Leaderboard built: {dash_path}")
    return dash_path
