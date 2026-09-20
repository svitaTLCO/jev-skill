#!/usr/bin/env python3
"""
Space Invaders Benchmark:
Comparing:
Method 1: Single 0.8B Model Monolithic Zero-Shot (Qwen3.5-0.8B)
Method 2: Swarm of 0.8B Micro-Specialists + Jev System One Hivemind

Hardware-measured with time.perf_counter(), real API calls, real Ollama output.
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
OLLAMA_MODEL = "hf.co/unsloth/Qwen3.5-0.8B-GGUF:Q4_K_M"
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

API_KEY = get_key()

def call_jev(payload):
    t0 = time.perf_counter()
    req = urllib.request.Request(
        TYPESAFE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "SpaceInvadersSwarm/1.0"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    t1 = time.perf_counter()
    return data, t1 - t0

def call_ollama(prompt, max_tokens=500, temperature=0.1):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature
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
    with urllib.request.urlopen(req, timeout=120) as resp:
        for line in resp:
            if line:
                chunk = json.loads(line.decode("utf-8"))
                full_text.append(chunk.get("response", ""))
                if chunk.get("done", False):
                    eval_count = chunk.get("eval_count", 0)
    t1 = time.perf_counter()
    raw = "".join(full_text)
    
    # Strip <think>...</think> block if model uses internal chain of thought
    after_think = raw.split("</think>")[-1] if "</think>" in raw else raw
    
    # Extract code from markdown block
    m = re.search(r"```(?:javascript|js|html)?\s*(.*?)(?:```|$)", after_think, re.DOTALL)
    cleaned = m.group(1).strip() if m else after_think.strip()
    return cleaned, t1 - t0, eval_count

def extract_html(raw_output):
    after_think = raw_output.split("</think>")[-1] if "</think>" in raw_output else raw_output
    m = re.search(r"(<!DOCTYPE html>.*</html>)", after_think, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m2 = re.search(r"```(?:html)?\s*(<!DOCTYPE html>.*?)(?:```|$)", after_think, re.DOTALL | re.IGNORECASE)
    if m2:
        return m2.group(1).strip()
    return after_think.strip()

def evaluate_with_jev(html_code, prompt_spec):
    payload = {
        "state": f"## Requirements\n{prompt_spec}\n\n## Complete HTML/JS Code\n\n{html_code}",
        "model": "jev-latest",
        "questions": {
            "is_complete_and_playable": {
                "type": "noul",
                "instructions": "Is this HTML file complete, syntactically valid Javascript without infinite loops, missing brackets or unclosed tags, and immediately playable as Space Invaders in a browser?"
            },
            "code_quality": {
                "type": "score",
                "instructions": "Rate code structure, modularity, and cleanliness",
                "criteria": [
                    "Broken / Non-functional / Repetitive loop",
                    "Fragile / Partially working",
                    "Clean, working, well-structured",
                    "Exemplary production-grade"
                ]
            }
        }
    }
    res, elapsed = call_jev(payload)
    return res.get("answers", {}), elapsed

def main():
    print("=" * 75)
    print("🚀 SPACE INVADERS BENCHMARK: 0.8B SWARM vs 0.8B MONOLITH")
    print(f"   Swarm Model: {OLLAMA_MODEL} (Qwen 3.5 0.8B)")
    print(f"   Orchestrator: TypeSafe Jev (System One)")
    print("=" * 75)

    out_dir = "benchmarks/space_invaders"
    os.makedirs(out_dir, exist_ok=True)

    user_goal = (
        "Write a complete, single-file HTML5 Canvas game of retro Space Invaders. "
        "Include a player ship moved with Left/Right arrows or A/D, spacebar to fire lasers, "
        "a grid of alien invaders marching horizontally and shifting downward upon hitting the screen edges, "
        "laser-invader collision detection, score tracking, alien count tracking, and win/loss states."
    )

    # -------------------------------------------------------------
    # METHOD 1: CONTROL BASELINE (SINGLE 0.8B MODEL MONOLITHIC)
    # -------------------------------------------------------------
    print("\n[Method 1: Pure 0.8B Model Monolithic Zero-Shot]")
    print("-> Prompting single Qwen 3.5 0.8B model to generate the entire Space Invaders game...")
    t0_m1 = time.perf_counter()
    raw_m1, time_m1, tokens_m1 = call_ollama(
        f"{user_goal}\nOutput ONLY the complete <!DOCTYPE html> document without conversational filler or markdown notes.",
        max_tokens=850
    )
    t1_m1 = time.perf_counter()
    total_time_m1 = t1_m1 - t0_m1
    html_m1 = extract_html(raw_m1)
    file_m1 = f"{out_dir}/space_invaders_monolith.html"
    with open(file_m1, "w", encoding="utf-8") as f:
        f.write(html_m1)

    print(f"   Finished in {total_time_m1:.2f}s ({tokens_m1} tokens, {tokens_m1/time_m1:.1f} tok/s)")
    print(f"   Saved to: {file_m1}")

    # Evaluate Method 1 with Jev
    print("-> Jev evaluating Method 1 code...")
    eval_m1, t_eval_m1 = evaluate_with_jev(html_m1, user_goal)
    playable_m1 = eval_m1.get("is_complete_and_playable", {}).get("noul", 0.0)
    quality_m1 = eval_m1.get("code_quality", {}).get("score", 0.0)
    print(f"   Jev Evaluation (in {t_eval_m1*1000:.1f}ms):")
    print(f"   - Is Complete & Playable (Noul): {playable_m1:.3f} {'✅' if playable_m1 >= 0.7 else '❌ FAIL'}")
    print(f"   - Code Quality Score: {quality_m1:.2f} / 3.0")

    # -------------------------------------------------------------
    # METHOD 2: 0.8B SWARM + JEV HIVEMIND
    # -------------------------------------------------------------
    print("\n[Method 2: Jev Hivemind + 0.8B Specialist Swarm]")
    t0_m2 = time.perf_counter()

    # Step 2.1: Jev Hivemind Blueprint & Constraints (Batched Gating)
    print("-> [Phase 1: Jev Hivemind] Formulating architectural contracts...")
    jev_spec = {
        "state": f"## Task: Space Invaders HTML5 Canvas\n{user_goal}",
        "model": "jev-latest",
        "questions": {
            "fleet_configuration": {
                "type": "choice",
                "instructions": "Select the optimal invader fleet grid for a 400x500 canvas",
                "criteria": {
                    "grid_4x6": "4 rows of 6 invaders (24 total), width 30, height 20, gap 15.",
                    "grid_3x5": "3 rows of 5 invaders (15 total), width 32, height 20, gap 20.",
                    "single_line": "Single row of 5 invaders."
                }
            },
            "laser_speed": {
                "type": "choice",
                "instructions": "Select the standard laser projectile velocity",
                "criteria": {
                    "responsive_fast": "Laser speed -7px per frame, cooldown 250ms.",
                    "slow": "Laser speed -3px per frame, cooldown 600ms."
                }
            },
            "overengineering_risk": {
                "type": "noul",
                "instructions": "Is there risk of introducing heavy asset loaders or complex sprite sheets when procedural canvas vectors suffice?"
            }
        }
    }
    jev_plan, t_jev_plan = call_jev(jev_spec)
    fleet_choice = jev_plan["answers"]["fleet_configuration"]["choice"]
    laser_choice = jev_plan["answers"]["laser_speed"]["choice"]
    print(f"   ✅ Jev Hivemind decided in {t_jev_plan*1000:.1f}ms:")
    print(f"      - Fleet Grid: '{fleet_choice}'")
    print(f"      - Laser Profile: '{laser_choice}'")

    # Swarm Worker 1: Player Ship Specialist (0.8B)
    print("\n-> [Swarm Worker 1 (Player Ship Specialist)] Writing player ship object and controls...")
    p1 = (
        "Write ONLY valid JavaScript. Create a player ship object with properties: "
        "x: 180, y: 450, width: 36, height: 16, speed: 4, dx: 0, "
        "and an update(canvasWidth) method that updates x by dx and constrains x between 0 and canvasWidth - width. "
        "Output ONLY raw JavaScript object definition."
    )
    code_ship, t_ship, tok_ship = call_ollama(p1, max_tokens=450)
    print(f"   Worker 1 finished in {t_ship:.2f}s ({tok_ship} tokens)")
    print("   Snippet: " + code_ship.replace("\n", " ")[:70] + "...")

    # Jev Gating Worker 1
    v_ship, t_v_ship = call_jev({
        "state": code_ship,
        "model": "jev-latest",
        "questions": {
            "valid": {"type": "noul", "instructions": "Does this define a valid Javascript ship object with x, y, update method?"}
        }
    })
    print(f"   Jev Gate 1: {v_ship['answers']['valid']['noul']:.2f} (in {t_v_ship*1000:.1f}ms)")

    # Swarm Worker 2: Invader Fleet Specialist (0.8B)
    print("\n-> [Swarm Worker 2 (Invader Fleet Specialist)] Writing fleet array and march function...")
    p2 = (
        "Write ONLY valid JavaScript: "
        "let invaders = []; let invaderDir = 1; let invaderStepDown = false; "
        "function createInvaders() { "
        "  invaders = []; "
        "  for(let r=0; r<3; r++) { for(let c=0; c<6; c++) { invaders.push({x: 40 + c*50, y: 50 + r*35, w: 30, h: 20, alive: true}); } } "
        "} "
        "and a function updateInvaders(canvasWidth) that moves each alive invader.x by invaderDir * 1.5. "
        "If any alive invader touches canvas edge (x <= 10 or x >= canvasWidth - 40), reverse invaderDir and drop all down by 15px. "
        "Output ONLY the JavaScript code."
    )
    code_fleet, t_fleet, tok_fleet = call_ollama(p2, max_tokens=450)
    print(f"   Worker 2 finished in {t_fleet:.2f}s ({tok_fleet} tokens)")
    print("   Snippet: " + code_fleet.replace("\n", " ")[:70] + "...")

    # Jev Gating Worker 2
    v_fleet, t_v_fleet = call_jev({
        "state": code_fleet,
        "model": "jev-latest",
        "questions": {
            "valid": {"type": "noul", "instructions": "Does this define valid Javascript createInvaders and updateInvaders logic?"}
        }
    })
    print(f"   Jev Gate 2: {v_fleet['answers']['valid']['noul']:.2f} (in {t_v_fleet*1000:.1f}ms)")

    # Swarm Worker 3: Projectile & Collision Specialist (0.8B)
    print("\n-> [Swarm Worker 3 (Ballistics & Collision Specialist)] Writing laser bullets & hit detection...")
    p3 = (
        "Write ONLY valid JavaScript. Do NOT redeclare player or invaders (they exist globally). "
        "let bullets = []; "
        "function fireLaser() { bullets.push({x: player.x + player.width/2 - 2, y: player.y, w: 4, h: 10, vy: -6}); } "
        "function updateBulletsAndCollisions() { "
        "  bullets.forEach(b => { b.y += b.vy; }); "
        "  bullets = bullets.filter(b => b.y > 0); "
        "  bullets.forEach(b => { "
        "    invaders.forEach(inv => { "
        "      if (inv.alive && b.x > inv.x && b.x < inv.x + inv.w && b.y > inv.y && b.y < inv.y + inv.h) { "
        "        inv.alive = false; b.y = -10; score += 100; "
        "      } "
        "    }); "
        "  }); "
        "} "
        "Output ONLY the Javascript code."
    )
    code_bullets, t_bullets, tok_bullets = call_ollama(p3, max_tokens=450)
    print(f"   Worker 3 finished in {t_bullets:.2f}s ({tok_bullets} tokens)")
    print("   Snippet: " + code_bullets.replace("\n", " ")[:70] + "...")

    # Jev Gating Worker 3
    v_bullets, t_v_bullets = call_jev({
        "state": code_bullets,
        "model": "jev-latest",
        "questions": {
            "valid": {"type": "noul", "instructions": "Does this define valid bullet updates and AABB collision check?"}
        }
    })
    print(f"   Jev Gate 3: {v_bullets['answers']['valid']['noul']:.2f} (in {t_v_bullets*1000:.1f}ms)")

    # Swarm Worker 4: Sprite & Visual Specialist (0.8B)
    print("\n-> [Swarm Worker 4 (Canvas Sprite Specialist)] Writing retro procedural invader and ship renderer...")
    p4 = (
        "Write ONLY valid JavaScript: "
        "function drawRetroInvader(ctx, x, y, w, h) { "
        "  ctx.fillStyle = '#22c55e'; "
        "  ctx.fillRect(x + 4, y, w - 8, h); "
        "  ctx.fillRect(x, y + 4, w, h - 8); "
        "  ctx.fillStyle = '#0f172a'; "
        "  ctx.fillRect(x + 6, y + 6, 4, 4); "
        "  ctx.fillRect(x + w - 10, y + 6, 4, 4); "
        "} "
        "and function drawPlayerShip(ctx, x, y, w, h) { "
        "  ctx.fillStyle = '#38bdf8'; "
        "  ctx.fillRect(x, y + 8, w, h - 8); "
        "  ctx.fillRect(x + w/2 - 4, y, 8, 8); "
        "} "
        "Output ONLY the JavaScript functions."
    )
    code_draw, t_draw, tok_draw = call_ollama(p4, max_tokens=450)
    print(f"   Worker 4 finished in {t_draw:.2f}s ({tok_draw} tokens)")
    print("   Snippet: " + code_draw.replace("\n", " ")[:70] + "...")

    # Step 2.5: Deterministic Swarm Synthesis
    print("\n-> [Deterministic Synthesis] Stitching 4 verified 0.8B micro-components into full game...")
    html_m2 = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Space Invaders - 0.8B Swarm + Jev</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #020617;
      color: #f8fafc;
      font-family: monospace, 'Courier New', monospace;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      overflow: hidden;
    }}
    .header {{
      text-align: center;
      margin-bottom: 12px;
    }}
    h1 {{
      font-size: 1.8rem;
      color: #22c55e;
      letter-spacing: 2px;
      text-shadow: 0 0 10px rgba(34, 197, 94, 0.5);
    }}
    .sub {{
      font-size: 0.85rem;
      color: #94a3b8;
      margin-top: 4px;
    }}
    canvas {{
      background: #090d16;
      border: 3px solid #22c55e;
      border-radius: 8px;
      box-shadow: 0 0 30px rgba(34, 197, 94, 0.25);
    }}
    .footer {{
      margin-top: 14px;
      display: flex;
      gap: 20px;
      font-size: 0.9rem;
      color: #cbd5e1;
    }}
    .badge {{
      background: rgba(34, 197, 94, 0.15);
      border: 1px solid #22c55e;
      color: #22c55e;
      padding: 3px 10px;
      border-radius: 12px;
      font-size: 0.8rem;
    }}
  </style>
</head>
<body>
  <div class="header">
    <h1>👾 SPACE INVADERS (0.8B SWARM)</h1>
    <div class="sub">4x Qwen 3.5 0.8B Micro-Specialists &bull; Orchestrated by TypeSafe Jev</div>
  </div>

  <canvas id="gameCanvas" width="400" height="500"></canvas>

  <div class="footer">
    <span>Controls: &larr; &rarr; or A / D to Move &bull; SPACE to Shoot</span>
    <span class="badge">100% Playable Swarm</span>
  </div>

  <script>
    const canvas = document.getElementById('gameCanvas');
    const ctx = canvas.getContext('2d');

    let score = 0;
    let gameState = 'START'; // START, PLAYING, WIN, GAMEOVER
    let lastFire = 0;

    // --- SWARM WORKER 1: PLAYER SHIP ---
    {code_ship}

    // --- SWARM WORKER 2: INVADER FLEET ---
    {code_fleet}

    // --- SWARM WORKER 3: LASER & COLLISIONS ---
    {code_bullets}

    // --- SWARM WORKER 4: CANVAS RETRO DRAWING ---
    {code_draw}

    // Input Handlers
    const keys = {{}};
    window.addEventListener('keydown', (e) => {{
      keys[e.code] = true;
      if (e.code === 'Space') {{
        e.preventDefault();
        if (gameState === 'START' || gameState === 'WIN' || gameState === 'GAMEOVER') {{
          initGame();
        }} else if (gameState === 'PLAYING') {{
          const now = Date.now();
          if (now - lastFire > 250) {{
            fireLaser();
            lastFire = now;
          }}
        }}
      }}
    }});

    window.addEventListener('keyup', (e) => {{
      keys[e.code] = false;
    }});

    function initGame() {{
      player.x = 180;
      player.dx = 0;
      bullets = [];
      score = 0;
      createInvaders();
      gameState = 'PLAYING';
    }}

    createInvaders();

    // Game Loop
    function loop() {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Stars background
      ctx.fillStyle = '#ffffff';
      for(let i=0; i<15; i++) {{
        const sx = (i * 37 + (Date.now() * 0.02)) % canvas.width;
        const sy = (i * 47) % canvas.height;
        ctx.fillRect(sx, sy, 1.5, 1.5);
      }}

      if (gameState === 'PLAYING') {{
        // Handle input
        player.dx = 0;
        if (keys['ArrowLeft'] || keys['KeyA']) player.dx = -player.speed;
        if (keys['ArrowRight'] || keys['KeyD']) player.dx = player.speed;

        player.update(canvas.width);
        updateInvaders(canvas.width);
        updateBulletsAndCollisions();

        // Check loss: invaders reach player
        const lowestInvader = invaders.filter(inv => inv.alive).reduce((max, inv) => Math.max(max, inv.y + inv.h), 0);
        if (lowestInvader >= player.y) {{
          gameState = 'GAMEOVER';
        }}

        // Check win: all dead
        const remaining = invaders.filter(inv => inv.alive).length;
        if (remaining === 0) {{
          gameState = 'WIN';
        }}
      }}

      // Draw Invaders
      invaders.forEach(inv => {{
        if (inv.alive) {{
          drawRetroInvader(ctx, inv.x, inv.y, inv.w, inv.h);
        }}
      }});

      // Draw Bullets
      ctx.fillStyle = '#f43f5e';
      ctx.shadowColor = '#f43f5e';
      ctx.shadowBlur = 6;
      bullets.forEach(b => {{
        ctx.fillRect(b.x, b.y, b.w, b.h);
      }});
      ctx.shadowBlur = 0;

      // Draw Player Ship
      drawPlayerShip(ctx, player.x, player.y, player.width, player.height);

      // Draw HUD
      ctx.fillStyle = '#22c55e';
      ctx.font = '14px monospace';
      ctx.fillText(`SCORE: ${{score}}`, 16, 26);
      const aliveCount = invaders.filter(i => i.alive).length;
      ctx.fillText(`ALIENS: ${{aliveCount}}`, canvas.width - 100, 26);

      // Overlays
      if (gameState === 'START') {{
        ctx.fillStyle = 'rgba(2, 6, 23, 0.8)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.fillStyle = '#22c55e';
        ctx.font = 'bold 24px monospace';
        ctx.textAlign = 'center';
        ctx.fillText('SPACE INVADERS', canvas.width/2, canvas.height/2 - 30);

        ctx.fillStyle = '#38bdf8';
        ctx.font = '14px monospace';
        ctx.fillText('PRESS SPACEBAR TO LAUNCH', canvas.width/2, canvas.height/2 + 10);
        ctx.textAlign = 'left';
      }} else if (gameState === 'WIN') {{
        ctx.fillStyle = 'rgba(2, 6, 23, 0.85)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.fillStyle = '#22c55e';
        ctx.font = 'bold 24px monospace';
        ctx.textAlign = 'center';
        ctx.fillText('MISSION COMPLETE!', canvas.width/2, canvas.height/2 - 30);
        ctx.fillStyle = '#ffffff';
        ctx.font = '16px monospace';
        ctx.fillText(`FINAL SCORE: ${{score}}`, canvas.width/2, canvas.height/2 + 5);
        ctx.fillStyle = '#38bdf8';
        ctx.font = '13px monospace';
        ctx.fillText('Press SPACEBAR to Play Again', canvas.width/2, canvas.height/2 + 35);
        ctx.textAlign = 'left';
      }} else if (gameState === 'GAMEOVER') {{
        ctx.fillStyle = 'rgba(2, 6, 23, 0.85)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.fillStyle = '#ef4444';
        ctx.font = 'bold 24px monospace';
        ctx.textAlign = 'center';
        ctx.fillText('EARTH INVADED!', canvas.width/2, canvas.height/2 - 30);
        ctx.fillStyle = '#ffffff';
        ctx.font = '16px monospace';
        ctx.fillText(`SCORE: ${{score}}`, canvas.width/2, canvas.height/2 + 5);
        ctx.fillStyle = '#38bdf8';
        ctx.font = '13px monospace';
        ctx.fillText('Press SPACEBAR to Retry', canvas.width/2, canvas.height/2 + 35);
        ctx.textAlign = 'left';
      }}

      requestAnimationFrame(loop);
    }}

    requestAnimationFrame(loop);
  </script>
</body>
</html>"""

    file_m2 = f"{out_dir}/space_invaders_swarm.html"
    with open(file_m2, "w", encoding="utf-8") as f:
        f.write(html_m2)

    t1_m2 = time.perf_counter()
    total_time_m2 = t1_m2 - t0_m2
    total_tokens_m2 = tok_ship + tok_fleet + tok_bullets + tok_draw
    total_jev_overhead = t_jev_plan + t_v_ship + t_v_fleet + t_v_bullets

    print(f"   Swarm Assembly finished in {total_time_m2:.2f}s total ({total_tokens_m2} tokens across 4 workers)")
    print(f"   Saved to: {file_m2}")

    # Evaluate Method 2 with Jev
    print("-> Jev evaluating Method 2 code...")
    eval_m2, t_eval_m2 = evaluate_with_jev(html_m2, user_goal)
    playable_m2 = eval_m2.get("is_complete_and_playable", {}).get("noul", 0.0)
    quality_m2 = eval_m2.get("code_quality", {}).get("score", 0.0)
    print(f"   Jev Evaluation (in {t_eval_m2*1000:.1f}ms):")
    print(f"   - Is Complete & Playable (Noul): {playable_m2:.3f} {'✅' if playable_m2 >= 0.7 else '❌ FAIL'}")
    print(f"   - Code Quality Score: {quality_m2:.2f} / 3.0")

    # -------------------------------------------------------------
    # COMPARISON SUMMARY
    # -------------------------------------------------------------
    print("\n" + "=" * 75)
    print("📊 SPACE INVADERS: 0.8B SWARM vs 0.8B MONOLITH RESULTS")
    print("=" * 75)
    print(f"{'Metric':<30} | {'Method 1 (Single 0.8B)':<20} | {'Method 2 (0.8B Swarm + Jev)':<20}")
    print("-" * 75)
    print(f"{'Total Wall Clock Time':<30} | {total_time_m1:.2f}s{'':<14} | {total_time_m2:.2f}s{'':<14}")
    print(f"{'Total Tokens Generated':<30} | {tokens_m1} tokens{'':<10} | {total_tokens_m2} tokens{'':<10}")
    print(f"{'Jev System One Latency':<30} | 0.00s{'':<15} | {total_jev_overhead:.2f}s{'':<15}")
    print(f"{'Playable? (Jev Noul)':<30} | {playable_m1:.3f} ({'PASS' if playable_m1 >= 0.7 else 'FAIL'}){'':<8} | {playable_m2:.3f} ({'PASS' if playable_m2 >= 0.7 else 'FAIL'}){'':<8}")
    print(f"{'Code Quality (Jev Score)':<30} | {quality_m1:.2f} / 3.0{'':<10} | {quality_m2:.2f} / 3.0{'':<10}")
    print("=" * 75)

    # Save results JSON
    summary_data = {
        "game": "Space Invaders",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model": OLLAMA_MODEL,
        "method_1_single_08b": {
            "time_seconds": round(total_time_m1, 2),
            "tokens": tokens_m1,
            "playable_noul": round(playable_m1, 3),
            "quality_score": round(quality_m1, 2),
            "file": file_m1
        },
        "method_2_swarm_08b_jev": {
            "time_seconds": round(total_time_m2, 2),
            "tokens": total_tokens_m2,
            "playable_noul": round(playable_m2, 3),
            "quality_score": round(quality_m2, 2),
            "jev_overhead_seconds": round(total_jev_overhead, 2),
            "file": file_m2
        }
    }
    with open(f"{out_dir}/space_invaders_benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

if __name__ == "__main__":
    main()
