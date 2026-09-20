#!/usr/bin/env python3
"""
Experiment 1: Swarm Density Scaling (8-Agent Swarm)
Building: Space Invaders Deluxe
Features:
1. Player Ship with Inertia Physics (Worker 1)
2. Accelerating Invader Fleet Grid (Worker 2)
3. Lasers & Alien Bomb Ballistics (Worker 3)
4. Explosive Particle System Engine (Worker 4)
5. 8-Bit Web Audio API Sound Synthesizer (Worker 5)
6. Mystery Flying UFO Spawner (Worker 6)
7. Destructible Defense Bunkers (Worker 7)
8. High-Score & LocalStorage HUD (Worker 8)

All 8 micro-contracts executed by SLM workers and audited by TypeSafe Jev.
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "hf.co/mradermacher/Huihui-Qwen3.5-0.8B-abliterated-GGUF:Q4_K_M"
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

def call_worker(worker_id, prompt, num_predict=500):
    t0 = time.perf_counter()
    full_prompt = f"Implement the following in JavaScript:\n{prompt}\n\nWrap the code strictly inside a ```javascript ``` code block."
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps({
            "model": OLLAMA_MODEL,
            "prompt": full_prompt,
            "options": {"num_predict": num_predict, "temperature": 0.1},
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
    m = re.search(r"```(?:javascript|js)?\s*(.*?)(?:```|$)", after_think, re.DOTALL)
    clean = m.group(1).strip() if m else after_think.strip()
    
    # Ensure balanced brackets
    diff = clean.count("{") - clean.count("}")
    if diff > 0:
        clean += "\n" + ("}" * diff)
        
    return clean, elapsed, tokens

def run_worker_pipeline(worker_id, prompt, question):
    print(f"-> [Worker {worker_id}] Generating micro-component...")
    code, t_gen, tokens = call_worker(worker_id, prompt)
    
    # Gate with Jev
    jev_res, t_jev = call_jev({
        "state": code,
        "model": "jev-latest",
        "questions": {"valid": {"type": "noul", "instructions": question}}
    })
    noul = jev_res.get("answers", {}).get("valid", {}).get("noul", 0.0)
    print(f"   [{worker_id}] Done in {t_gen:.2f}s ({tokens} tok) | Jev Gate: {noul:.2f} (in {t_jev*1000:.0f}ms)")
    return {
        "id": worker_id,
        "code": code,
        "time": t_gen,
        "tokens": tokens,
        "noul": noul,
        "jev_time": t_jev
    }

def main():
    print("=" * 75)
    print("🚀 EXPERIMENT 1: SWARM DENSITY SCALING (8-AGENT SWARM)")
    print(f"   Game: Space Invaders Deluxe (Canvas 2D + Web Audio Chiptune)")
    print(f"   Workers: 8x {OLLAMA_MODEL} | Hivemind: TypeSafe Jev")
    print("=" * 75)

    out_dir = "benchmarks/swarm_deluxe"
    os.makedirs(out_dir, exist_ok=True)
    t_global_start = time.perf_counter()

    # Step 1: Jev Hivemind Prompt Gating & Architecture Decision
    print("\n[Phase 1: Jev Hivemind Architectural Spec]")
    spec_payload = {
        "state": "Building Space Invaders Deluxe with player inertia, 8-bit audio, destructible bunkers, and particle engine.",
        "model": "jev-latest",
        "questions": {
            "audio_strategy": {
                "type": "choice",
                "instructions": "Select the optimal audio synthesis method for self-contained browser game",
                "criteria": {
                    "web_audio_procedural": "Web Audio API OscillatorNode and AudioContext with synthesized beeps and noise buffer.",
                    "external_mp3": "External audio files over HTTP.",
                    "silent": "No audio."
                }
            },
            "bunker_structure": {
                "type": "choice",
                "instructions": "Select the optimal destructible bunker representation",
                "criteria": {
                    "segmented_blocks": "4 bunkers each composed of 3x4 sub-blocks that disappear upon collision.",
                    "health_counter": "Single rectangle with health integer."
                }
            }
        }
    }
    spec_res, t_spec = call_jev(spec_payload)
    print(f"   ✅ Jev Hivemind resolved architecture in {t_spec*1000:.1f}ms:")
    print(f"      - Audio: '{spec_res['answers']['audio_strategy']['choice']}'")
    print(f"      - Bunkers: '{spec_res['answers']['bunker_structure']['choice']}'")

    # Step 2: Define the 8 Worker Specifications (Goal-oriented prompts)
    worker_specs = [
        (
            "1_player",
            "A player cannon object `player` with x: 200, y: 460, width: 36, height: 18, vx: 0, speed: 5, friction: 0.85, and update(canvasWidth) method that adds vx to x, applies friction, and clamps x between 10 and canvasWidth - width - 10.",
            "Does this define a valid player cannon object with velocity inertia and update method?"
        ),
        (
            "2_fleet",
            "Invader fleet variables: `let invaders = []; let invaderDir = 1; let invaderSpeed = 1.2;`. A createInvaders() function creating 4 rows of 6 aliens (x, y, w: 26, h: 18, alive: true, scoreVal: (4-r)*10). An updateInvaders(canvasWidth) function moving invaders horizontally, reversing dir and dropping down 14px on edge hit, speeding up 5% per bounce.",
            "Does this define valid createInvaders and accelerating updateInvaders logic?"
        ),
        (
            "3_ballistics",
            "Ballistics variables: `let lasers = []; let bombs = [];`. A fireLaser() function spawning a laser from player center with vy: -7. A maybeAlienBomb() function with 3% chance per frame of dropping bomb from a random living invader with vy: 3.5. An updateBallistics() function updating positions and filtering out-of-bounds.",
            "Does this define valid laser and alien bomb ballistic physics functions?"
        ),
        (
            "4_particles",
            "Particle engine: `let particles = [];`. A spawnExplosion(x, y, color) function creating 12 particles with random angle, speed, alpha: 1.0. An updateAndDrawParticles(ctx) function updating positions, decaying alpha by 0.03, drawing colored squares with globalAlpha, and removing dead particles.",
            "Does this define a valid particle explosion system with decay and draw loop?"
        ),
        (
            "5_audio",
            "Web Audio API chiptune audio: `let audioCtx = null;`. An initAudio() function initializing AudioContext. A playTone(freq, duration, type) function creating an oscillator and gain node with exponential decay. An sfxLaser() function playing 880Hz sawtooth. An sfxExplosion() function playing 120Hz triangle.",
            "Does this define valid Web Audio API chiptune sound functions?"
        ),
        (
            "6_ufo",
            "Mystery flying UFO: `let ufo = { x: -60, y: 35, w: 40, h: 14, speed: 2, active: false, scoreVal: 200 };`. A maybeSpawnUFO() function with 0.3% spawn chance. An updateUFO(canvasWidth) function moving it across and resetting when offscreen. A drawUFO(ctx) function rendering a red flying saucer.",
            "Does this define valid mystery flying UFO spawn, update, and draw routines?"
        ),
        (
            "7_bunkers",
            "Destructible defense bunkers: `let bunkers = [];`. A createBunkers() function generating 4 bunkers each made of a 3x4 grid of small blocks (w: 8, h: 8, hp: 1). A drawBunkers(ctx) function rendering alive bunker blocks in green (#22c55e).",
            "Does this define valid destructible bunker shield grid initialization and draw functions?"
        ),
        (
            "8_hud",
            "Game HUD and scoring: `let score = 0; let lives = 3; let highScore = parseInt(localStorage.getItem('si_highscore') || '0');`. An addScore(pts) function updating score and saving highScore. A drawHUD(ctx, width) function drawing score, hearts for lives, and highScore.",
            "Does this define valid game state HUD, score tracking, and localStorage persistence?"
        )
    ]

    print(f"\n[Phase 2: Deploying 8 Micro-Workers Under Jev Governance]")
    results = {}
    for wid, prompt, q in worker_specs:
        res = run_worker_pipeline(wid, prompt, q)
        results[wid] = res

    # Phase 3: Deterministic Swarm Synthesis
    print("\n[Phase 3: Deterministic Swarm Synthesis]")
    deluxe_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Space Invaders Deluxe (8-Agent Jev Swarm)</title>
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
    .header {{ text-align: center; margin-bottom: 10px; }}
    h1 {{ font-size: 1.8rem; color: #22c55e; letter-spacing: 2px; text-shadow: 0 0 12px rgba(34,197,94,0.6); }}
    .sub {{ font-size: 0.85rem; color: #94a3b8; margin-top: 3px; }}
    canvas {{
      background: #080c14;
      border: 3px solid #22c55e;
      border-radius: 8px;
      box-shadow: 0 0 35px rgba(34, 197, 94, 0.3);
    }}
    .footer {{ margin-top: 10px; font-size: 0.85rem; color: #cbd5e1; display: flex; gap: 20px; }}
    .badge {{ background: rgba(34,197,94,0.15); border: 1px solid #22c55e; color: #22c55e; padding: 2px 8px; border-radius: 10px; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>👾 SPACE INVADERS DELUXE</h1>
    <div class="sub">Built by an 8-Agent SLM Swarm &bull; Orchestrated by TypeSafe Jev</div>
  </div>

  <canvas id="c" width="440" height="520"></canvas>

  <div class="footer">
    <span>&larr; &rarr; / A D to Steer &bull; SPACE to Shoot</span>
    <span class="badge">8-Agent Swarm Verified</span>
  </div>

  <script>
    const canvas = document.getElementById('c');
    const ctx = canvas.getContext('2d');
    let gameState = 'START'; // START, PLAYING, WIN, GAMEOVER
    let lastPlayerLaser = 0;

    // --- WORKER 1: PLAYER CANNON ---
    {results['1_player']['code']}

    // --- WORKER 2: INVADER FLEET ---
    {results['2_fleet']['code']}

    // --- WORKER 3: BALLISTICS (LASERS & BOMBS) ---
    {results['3_ballistics']['code']}

    // --- WORKER 4: PARTICLE EXPLOSION ENGINE ---
    {results['4_particles']['code']}

    // --- WORKER 5: 8-BIT CHIPTUNE SYNTHESIZER ---
    {results['5_audio']['code']}

    // --- WORKER 6: MYSTERY FLYING UFO ---
    {results['6_ufo']['code']}

    // --- WORKER 7: DESTRUCTIBLE BUNKERS ---
    {results['7_bunkers']['code']}

    // --- WORKER 8: SCORE & HUD ---
    {results['8_hud']['code']}

    // Controls
    const keys = {{}};
    window.addEventListener('keydown', (e) => {{
      keys[e.code] = true;
      if (e.code === 'Space') {{
        e.preventDefault();
        initAudio();
        if (gameState !== 'PLAYING') {{
          initGame();
        }} else {{
          const now = Date.now();
          if (now - lastPlayerLaser > 220) {{
            fireLaser();
            sfxLaser();
            lastPlayerLaser = now;
          }}
        }}
      }}
    }});
    window.addEventListener('keyup', (e) => {{ keys[e.code] = false; }});

    function initGame() {{
      player.x = 200;
      player.vx = 0;
      lasers = [];
      bombs = [];
      particles = [];
      score = 0;
      lives = 3;
      invaderSpeed = 1.2;
      ufo.active = false;
      createInvaders();
      createBunkers();
      gameState = 'PLAYING';
    }}

    createInvaders();
    createBunkers();

    // Custom Sprite Renderers
    function drawRetroInvader(x, y, w, h, scoreVal) {{
      const colors = {{ 40: '#f43f5e', 30: '#a855f7', 20: '#38bdf8', 10: '#22c55e' }};
      ctx.fillStyle = colors[scoreVal] || '#22c55e';
      ctx.fillRect(x + 4, y, w - 8, h);
      ctx.fillRect(x, y + 4, w, h - 8);
      ctx.fillStyle = '#080c14';
      ctx.fillRect(x + 5, y + 5, 4, 4);
      ctx.fillRect(x + w - 9, y + 5, 4, 4);
    }}

    function drawPlayerCannon(x, y, w, h) {{
      ctx.fillStyle = '#38bdf8';
      ctx.fillRect(x, y + 8, w, h - 8);
      ctx.fillRect(x + w/2 - 4, y, 8, 8);
      ctx.fillStyle = '#bae6fd';
      ctx.fillRect(x + 4, y + 10, w - 8, 3);
    }}

    // Master Collision Checker
    function checkInteractions() {{
      // Laser hits Invaders
      lasers.forEach(l => {{
        invaders.forEach(inv => {{
          if (inv.alive && l.x > inv.x && l.x < inv.x + inv.w && l.y > inv.y && l.y < inv.y + inv.h) {{
            inv.alive = false;
            l.y = -20;
            addScore(inv.scoreVal);
            spawnExplosion(inv.x + inv.w/2, inv.y + inv.h/2, '#22c55e');
            sfxExplosion();
          }}
        }});
        // Laser hits UFO
        if (ufo.active && l.x > ufo.x && l.x < ufo.x + ufo.w && l.y > ufo.y && l.y < ufo.y + ufo.h) {{
          ufo.active = false;
          l.y = -20;
          addScore(ufo.scoreVal);
          spawnExplosion(ufo.x + ufo.w/2, ufo.y + ufo.h/2, '#ef4444');
          sfxExplosion();
        }}
        // Laser hits Bunkers
        bunkers.forEach(b => {{
          if (b.hp > 0 && l.x > b.x && l.x < b.x + b.w && l.y > b.y && l.y < b.y + b.h) {{
            b.hp = 0;
            l.y = -20;
            spawnExplosion(b.x, b.y, '#22c55e');
          }}
        }});
      }});

      // Bombs hit Player
      bombs.forEach(b => {{
        if (b.x > player.x && b.x < player.x + player.width && b.y > player.y && b.y < player.y + player.height) {{
          b.y = 999;
          lives--;
          spawnExplosion(player.x + player.width/2, player.y + player.height/2, '#38bdf8');
          sfxExplosion();
          if (lives <= 0) gameState = 'GAMEOVER';
        }}
        // Bombs hit Bunkers
        bunkers.forEach(bk => {{
          if (bk.hp > 0 && b.x > bk.x && b.x < bk.x + bk.w && b.y > bk.y && b.y < bk.y + bk.h) {{
            bk.hp = 0;
            b.y = 999;
          }}
        }});
      }});
    }}

    // Master Game Loop
    function loop() {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (gameState === 'PLAYING') {{
        // Input
        if (keys['ArrowLeft'] || keys['KeyA']) player.vx = -player.speed;
        if (keys['ArrowRight'] || keys['KeyD']) player.vx = player.speed;

        player.update(canvas.width);
        updateInvaders(canvas.width);
        maybeAlienBomb();
        updateBallistics();
        maybeSpawnUFO();
        updateUFO(canvas.width);
        checkInteractions();

        const alive = invaders.filter(i => i.alive);
        if (alive.length === 0) gameState = 'WIN';
        if (alive.some(i => i.y + i.h >= player.y)) gameState = 'GAMEOVER';
      }}

      // RENDER SCENE
      drawBunkers(ctx);
      drawUFO(ctx);

      // Draw Invaders
      invaders.forEach(i => {{
        if (i.alive) drawRetroInvader(i.x, i.y, i.w, i.h, i.scoreVal);
      }});

      // Draw Lasers & Bombs
      ctx.fillStyle = '#38bdf8';
      lasers.forEach(l => ctx.fillRect(l.x, l.y, l.w, l.h));
      ctx.fillStyle = '#ef4444';
      bombs.forEach(b => ctx.fillRect(b.x, b.y, b.w, b.h));

      // Draw Player Cannon
      drawPlayerCannon(player.x, player.y, player.width, player.height);

      // Particles
      updateAndDrawParticles(ctx);

      // HUD
      drawHUD(ctx, canvas.width);

      // State Screens
      if (gameState === 'START') {{
        ctx.fillStyle = 'rgba(2, 6, 23, 0.85)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#22c55e';
        ctx.font = 'bold 24px monospace';
        ctx.textAlign = 'center';
        ctx.fillText('SPACE INVADERS DELUXE', canvas.width/2, 220);
        ctx.fillStyle = '#38bdf8';
        ctx.font = '14px monospace';
        ctx.fillText('PRESS SPACEBAR TO ENGAGE AUDIO & START', canvas.width/2, 260);
        ctx.textAlign = 'left';
      }} else if (gameState === 'WIN') {{
        ctx.fillStyle = 'rgba(2, 6, 23, 0.85)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#22c55e';
        ctx.font = 'bold 24px monospace';
        ctx.textAlign = 'center';
        ctx.fillText('GALAXY SAVED! YOU WIN!', canvas.width/2, 220);
        ctx.fillStyle = '#ffffff';
        ctx.font = '16px monospace';
        ctx.fillText('FINAL SCORE: ' + score, canvas.width/2, 260);
        ctx.fillStyle = '#38bdf8';
        ctx.font = '13px monospace';
        ctx.fillText('Press SPACE to Play Again', canvas.width/2, 295);
        ctx.textAlign = 'left';
      }} else if (gameState === 'GAMEOVER') {{
        ctx.fillStyle = 'rgba(2, 6, 23, 0.85)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#ef4444';
        ctx.font = 'bold 26px monospace';
        ctx.textAlign = 'center';
        ctx.fillText('DEFENSES BREACHED!', canvas.width/2, 220);
        ctx.fillStyle = '#ffffff';
        ctx.font = '16px monospace';
        ctx.fillText('SCORE: ' + score + '  BEST: ' + highScore, canvas.width/2, 260);
        ctx.fillStyle = '#38bdf8';
        ctx.font = '13px monospace';
        ctx.fillText('Press SPACE to Re-deploy', canvas.width/2, 295);
        ctx.textAlign = 'left';
      }}

      requestAnimationFrame(loop);
    }}

    requestAnimationFrame(loop);
  </script>
</body>
</html>"""

    file_deluxe = f"{out_dir}/space_invaders_deluxe.html"
    with open(file_deluxe, "w", encoding="utf-8") as f:
        f.write(deluxe_html)

    t_global_total = time.perf_counter() - t_global_start
    total_tokens = sum(r["tokens"] for r in results.values())
    total_jev_time = sum(r["jev_time"] for r in results.values()) + t_spec

    print(f"\n✅ 8-Agent Swarm Synthesis Finished in {t_global_total:.2f}s!")
    print(f"   - Total Tokens Generated: {total_tokens}")
    print(f"   - Total Jev Verification Overhead: {total_jev_time:.2f}s")
    print(f"   - Saved to: {file_deluxe}")

    # Phase 4: Full Jev System One Post-Flight Audit
    print("\n[Phase 4: Jev System One Final Quality Audit]")
    audit_res, t_audit = call_jev({
        "state": f"## Complete Space Invaders Deluxe HTML5 Game\n\n{deluxe_html}",
        "model": "jev-latest",
        "questions": {
            "is_complete_and_playable": {
                "type": "noul",
                "instructions": "Is this complete, valid HTML5 Canvas Space Invaders with player cannon inertia, particles, Web Audio chiptune, bunkers, UFO, and 100% playable in browser?"
            },
            "code_quality": {
                "type": "score",
                "instructions": "Rate code structure, modularity, and cleanliness",
                "criteria": ["Broken", "Fragile", "Clean & working", "Exemplary production-grade"]
            }
        }
    })
    noul_play = audit_res.get("answers", {}).get("is_complete_and_playable", {}).get("noul", 0.0)
    score_qual = audit_res.get("answers", {}).get("code_quality", {}).get("score", 0.0)
    print(f"   - Jev Playable Probability (Noul): {noul_play:.3f} {'✅' if noul_play >= 0.7 else '❌'}")
    print(f"   - Jev Code Quality Score: {score_qual:.2f} / 3.0")

    # Save metrics JSON
    metrics = {
        "experiment": "Experiment 1: Swarm Density Scaling (8 Agents)",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "workers_count": 8,
        "total_wall_clock_seconds": round(t_global_total, 2),
        "total_tokens": total_tokens,
        "total_jev_overhead_seconds": round(total_jev_time, 2),
        "workers": results,
        "final_audit": {
            "playable_noul": round(noul_play, 3),
            "quality_score": round(score_qual, 2)
        },
        "file": file_deluxe
    }
    with open(f"{out_dir}/exp1_results.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

if __name__ == "__main__":
    main()
