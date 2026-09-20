#!/usr/bin/env python3
"""
Experiment 2: Heterogeneous Swarm Tiering
Tier 1 Workers (qwen2.5:1.5b): High-speed micro-components (player thrust, particles, audio, HUD)
Tier 2 Brain (qwen2.5:3b): Complex procedural vector math & AI (irregular polygon asteroid splitting, hunter drone AI)
Supreme Hivemind (TypeSafe Jev System One): Interface contract gating & post-flight audit

Deliverable: Neon Vector Asteroids Deluxe
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_TIER1 = "hf.co/mradermacher/Huihui-Qwen3.5-0.8B-abliterated-GGUF:Q4_K_M"
MODEL_TIER2 = "hf.co/mradermacher/Huihui-Qwen3.5-2B-abliterated-GGUF:Q4_K_M"
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

def call_model(model_name, prompt, num_predict=600, temperature=0.1):
    t0 = time.perf_counter()
    chatml = f"""<|im_start|>system
You are an expert JavaScript developer. Generate ONLY valid JavaScript code enclosed in ```javascript ... ``` code fences. Never add extra functions or redeclare globals.<|im_end|>
<|im_start|>user
{prompt}
<|im_end|>
<|im_start|>assistant
<think>
"""
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps({
            "model": model_name,
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
    m = re.findall(r"```(?:javascript|js)?\s*(.*?)(?:```|$)", after_think, re.DOTALL)
    clean = m[0].strip() if m else after_think.strip()

    # Strip any redeclarations of global variables
    clean = re.sub(r"^\s*(?:let|const|var)\s+(?:canvas|ctx|keys|score|lives|gameState|lastShot)\s*=.*?;", "", clean, flags=re.MULTILINE)

    # Balance brackets if truncated
    diff = clean.count("{") - clean.count("}")
    if diff > 0:
        clean += "\n" + ("}" * diff)

    return clean, elapsed, tokens

def run_worker(tier_name, model_name, wid, prompt, question):
    print(f"-> [{tier_name}: {wid}] Prompting {model_name}...")
    code, t_gen, tokens = call_model(model_name, prompt)
    
    # Jev Contract Verification
    v_res, t_jev = call_jev({
        "state": code,
        "model": "jev-latest",
        "questions": {"valid": {"type": "noul", "instructions": question}}
    })
    noul = v_res.get("answers", {}).get("valid", {}).get("noul", 0.0)
    print(f"   ✅ [{wid}] Done in {t_gen:.2f}s ({tokens} tok) | Jev Gate: {noul:.2f} (in {t_jev*1000:.0f}ms)")
    return {
        "tier": tier_name,
        "model": model_name,
        "code": code,
        "time": t_gen,
        "tokens": tokens,
        "noul": noul,
        "jev_time": t_jev
    }

def main():
    print("=" * 75)
    print("⚡ EXPERIMENT 2: HETEROGENEOUS SWARM TIERING")
    print(f"   Game: Neon Vector Asteroids Deluxe")
    print(f"   Tier 1 (Agile SLM): {MODEL_TIER1} (Fast Physics, Audio, FX)")
    print(f"   Tier 2 (Deep Brain): {MODEL_TIER2} (Vector Math, Asteroid Splitting, Hunter AI)")
    print(f"   Supreme Hivemind: TypeSafe Jev System One")
    print("=" * 75)

    out_dir = "benchmarks/heterogeneous_swarm"
    os.makedirs(out_dir, exist_ok=True)
    t_global_start = time.perf_counter()

    # Phase 1: Jev Blueprint
    print("\n[Phase 1: Jev Blueprint Gating]")
    plan_res, t_plan = call_jev({
        "state": "Neon Vector Asteroids: 360-degree rotation physics, procedural polygon asteroid fracturing, hunter drone AI, and chiptune sound.",
        "model": "jev-latest",
        "questions": {
            "rotation_model": {
                "type": "choice",
                "instructions": "Select the optimal 2D ship rotation coordinate system",
                "criteria": {
                    "polar_radians": "Angle in radians with vx += Math.cos(angle)*thrust, vy += Math.sin(angle)*thrust, wrap edges.",
                    "four_way_grid": "Cardinal 4-direction movement."
                }
            },
            "interface_stability": {
                "type": "noul",
                "instructions": "Is there risk of signature mismatch between Tier 1 ship coordinates and Tier 2 AI vector calculations?"
            }
        }
    })
    print(f"   ✅ Jev resolved in {t_plan*1000:.1f}ms:")
    print(f"      - Rotation: '{plan_res['answers']['rotation_model']['choice']}'")
    print(f"      - Interface Risk (Noul): {plan_res['answers']['interface_stability']['noul']:.2f}")

    results = {}

    # Tier 1 - Worker 1: Ship Physics (Qwen 3.5 0.8B)
    p_ship = (
        "Implement in JavaScript a spaceship object: "
        "`let ship = { x: 250, y: 250, angle: -Math.PI/2, vx: 0, vy: 0, r: 12, rotSpeed: 0.08, thrust: 0.15, friction: 0.985, "
        "update: function(w, h) { this.x += this.vx; this.y += this.vy; this.vx *= this.friction; this.vy *= this.friction; "
        "if(this.x < 0) this.x += w; if(this.x > w) this.x -= w; if(this.y < 0) this.y += h; if(this.y > h) this.y -= h; } };` "
        "Output ONLY the JavaScript code inside a ```javascript block."
    )
    results["ship"] = run_worker("Tier 1", MODEL_TIER1, "ship", p_ship, "Does this define valid 2D spaceship with thrust and screen wrap?")

    # Tier 1 - Worker 2: Lasers & Particles (Qwen 3.5 0.8B)
    p_fx = (
        "Implement in JavaScript: a laser ballistics and particle system with: "
        "`let lasers = []; let particles = [];` "
        "function fireLaser() to push a laser traveling forward from ship position, "
        "function spawnDust(x, y, color) to spawn particle debris, and "
        "function updateLasersAndFX(w, h) to move lasers and age particles. "
        "Output ONLY the JavaScript code inside a ```javascript block."
    )
    results["lasers_fx"] = run_worker("Tier 1", MODEL_TIER1, "lasers_fx", p_fx, "Does this define valid laser ballistics and particle dust system?")

    # Tier 1 - Worker 3: Web Audio (Qwen 3.5 0.8B)
    p_audio = (
        "Implement in JavaScript: Web Audio API chiptune audio functions: "
        "let audioCtx = null; "
        "function initAudio() { if(!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)(); } "
        "function beep(freq, duration, type) { if(!audioCtx) return; const o = audioCtx.createOscillator(); const g = audioCtx.createGain(); o.type = type||'sawtooth'; o.frequency.setValueAtTime(freq, audioCtx.currentTime); g.gain.setValueAtTime(0.12, audioCtx.currentTime); g.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration); o.connect(g); g.connect(audioCtx.destination); o.start(); o.stop(audioCtx.currentTime + duration); } "
        "function sndThrust() { beep(80, 0.05, 'triangle'); } function sndLaser() { beep(950, 0.08, 'square'); } function sndBoom() { beep(120, 0.3, 'sawtooth'); } "
        "Output ONLY the JavaScript code inside a ```javascript block."
    )
    results["audio"] = run_worker("Tier 1", MODEL_TIER1, "audio", p_audio, "Does this define valid Web Audio laser, thrust, and explosion beeps?")

    # -------------------------------------------------------------
    # TIER 2 BRAIN: Complex Procedural Asteroids & Hunter AI (Qwen 3.5 2B)
    # -------------------------------------------------------------
    print("\n[Phase 2: Tier 2 High-Cognition Brain (Qwen 3.5 2B)]")
    
    # Tier 2 - Worker 4: Procedural Asteroids (Qwen 3.5 2B)
    p_asteroids = (
        "Implement in JavaScript: a procedural asteroid engine with: "
        "`let asteroids = [];` "
        "function spawnAsteroid(x, y, radius, level) that creates an asteroid with randomized polygon vertex offsets and angular velocity, "
        "function splitAsteroid(ast) that fractures hit asteroids into 2 smaller child asteroids, and "
        "function updateAsteroids(w, h) that moves and wraps asteroids across canvas borders. "
        "Output ONLY the JavaScript code inside a ```javascript block."
    )
    results["asteroids"] = run_worker("Tier 2", MODEL_TIER2, "asteroids_brain", p_asteroids, "Does this implement procedural irregular asteroid spawning, splitting, and motion math?")

    # Tier 2 - Worker 5: Hunter Drone Vector AI (Qwen 3.5 2B)
    p_drone = (
        "Implement in JavaScript: vector hunter drone tracking AI: "
        "`let hunterDrone = { x: -50, y: -50, vx: 0, vy: 0, r: 10, active: false };` "
        "function maybeSpawnDrone(w, h) that randomly activates the drone at the screen edge, and "
        "function updateHunterAI(targetX, targetY) that calculates vector distance (dx, dy) to target, accelerates toward it, and caps max velocity. "
        "Output ONLY the JavaScript code inside a ```javascript block."
    )
    results["drone_ai"] = run_worker("Tier 2", MODEL_TIER2, "drone_ai_brain", p_drone, "Does this implement vector tracking hunter drone AI pursuing target coordinates?")

    # Phase 3: Assembly
    print("\n[Phase 3: Assembly & Interface Verification]")
    game_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Neon Vector Asteroids (Heterogeneous Swarm)</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #030712;
      color: #f3f4f6;
      font-family: system-ui, -apple-system, sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      overflow: hidden;
    }}
    h1 {{ color: #38bdf8; font-size: 1.7rem; letter-spacing: 2px; text-shadow: 0 0 15px rgba(56,189,248,0.5); margin-bottom: 6px; }}
    .sub {{ color: #94a3b8; font-size: 0.85rem; margin-bottom: 10px; }}
    canvas {{
      background: #020617;
      border: 3px solid #38bdf8;
      border-radius: 12px;
      box-shadow: 0 0 40px rgba(56,189,248,0.25);
    }}
    .footer {{ margin-top: 10px; font-size: 0.85rem; color: #cbd5e1; display: flex; gap: 15px; }}
    .badge {{ background: rgba(56,189,248,0.15); border: 1px solid #38bdf8; color: #38bdf8; padding: 2px 8px; border-radius: 10px; }}
  </style>
</head>
<body>
  <h1>⚡ NEON VECTOR ASTEROIDS</h1>
  <div class="sub">Heterogeneous Swarm: Huihui-Qwen3.5-0.8B + Huihui-Qwen3.5-2B (Abliterated) &bull; Governed by TypeSafe Jev</div>

  <canvas id="c" width="500" height="500"></canvas>

  <div class="footer">
    <span>&larr; &rarr; / A D Rotate &bull; &uarr; / W Thrust &bull; SPACE Shoot</span>
    <span class="badge">Multi-Tier Swarm</span>
  </div>

  <script>
    const canvas = document.getElementById('c');
    const ctx = canvas.getContext('2d');
    let score = 0;
    let lives = 3;
    let gameState = 'START';
    let lastShot = 0;

    // --- TIER 1: SHIP PHYSICS ---
    {results['ship']['code']}

    // --- TIER 1: LASERS & PARTICLES ---
    {results['lasers_fx']['code']}

    // --- TIER 1: CHIPTUNE AUDIO ---
    {results['audio']['code']}

    // --- TIER 2 BRAIN: PROCEDURAL ASTEROID ENGINE ---
    {results['asteroids']['code']}

    // --- TIER 2 BRAIN: HUNTER DRONE VECTOR AI ---
    {results['drone_ai']['code']}

    const keys = {{}};
    window.addEventListener('keydown', (e) => {{
      keys[e.code] = true;
      initAudio();
      if (e.code === 'Space') {{
        e.preventDefault();
        if (gameState !== 'PLAYING') {{
          initGame();
        }} else {{
          const now = Date.now();
          if (now - lastShot > 180) {{
            fireLaser();
            sndLaser();
            lastShot = now;
          }}
        }}
      }}
    }});
    window.addEventListener('keyup', (e) => {{ keys[e.code] = false; }});

    function initGame() {{
      ship.x = canvas.width/2;
      ship.y = canvas.height/2;
      ship.vx = 0;
      ship.vy = 0;
      ship.angle = -Math.PI/2;
      lasers = [];
      particles = [];
      asteroids = [];
      hunterDrone.active = false;
      score = 0;
      lives = 3;
      for(let i=0; i<4; i++) {{
        const ax = Math.random() < 0.5 ? 40 : canvas.width - 40;
        const ay = Math.random() * canvas.height;
        spawnAsteroid(ax, ay, 32, 1);
      }}
      gameState = 'PLAYING';
    }}

    // Master Interactions
    function checkCollisions() {{
      // Lasers hit Asteroids
      lasers.forEach(l => {{
        asteroids.forEach(a => {{
          if (Math.hypot(l.x - a.x, l.y - a.y) < a.r) {{
            l.life = 0;
            score += (4 - a.level) * 50;
            spawnDust(a.x, a.y, '#f59e0b');
            sndBoom();
            splitAsteroid(a);
            a.dead = true;
          }}
        }});
        // Lasers hit Hunter Drone
        if (hunterDrone.active && Math.hypot(l.x - hunterDrone.x, l.y - hunterDrone.y) < hunterDrone.r + 4) {{
          l.life = 0;
          hunterDrone.active = false;
          score += 300;
          spawnDust(hunterDrone.x, hunterDrone.y, '#ef4444');
          sndBoom();
        }}
      }});
      asteroids = asteroids.filter(a => !a.dead);

      // Ship hits Asteroids
      asteroids.forEach(a => {{
        if (Math.hypot(ship.x - a.x, ship.y - a.y) < ship.r + a.r) {{
          lives--;
          spawnDust(ship.x, ship.y, '#38bdf8');
          sndBoom();
          ship.x = canvas.width/2;
          ship.y = canvas.height/2;
          ship.vx = 0; ship.vy = 0;
          if (lives <= 0) gameState = 'GAMEOVER';
        }}
      }});

      // Ship hits Hunter Drone
      if (hunterDrone.active && Math.hypot(ship.x - hunterDrone.x, ship.y - hunterDrone.y) < ship.r + hunterDrone.r) {{
        lives--;
        hunterDrone.active = false;
        spawnDust(ship.x, ship.y, '#ef4444');
        sndBoom();
        if (lives <= 0) gameState = 'GAMEOVER';
      }}

      if (asteroids.length === 0 && !hunterDrone.active) {{
        gameState = 'WIN';
      }}
    }}

    // Render Procedural Asteroid
    function drawAsteroid(ctx, a) {{
      ctx.save();
      ctx.translate(a.x, a.y);
      ctx.rotate(a.rot);
      ctx.strokeStyle = '#f59e0b';
      ctx.lineWidth = 2;
      ctx.shadowColor = '#f59e0b';
      ctx.shadowBlur = 8;
      ctx.beginPath();
      const n = a.offsets.length;
      for(let i=0; i<n; i++) {{
        const ang = (i / n) * Math.PI * 2;
        const rad = a.r * a.offsets[i];
        const px = Math.cos(ang) * rad;
        const py = Math.sin(ang) * rad;
        if(i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }}
      ctx.closePath();
      ctx.stroke();
      ctx.restore();
    }}

    // Render Ship
    function drawShip(ctx, s) {{
      ctx.save();
      ctx.translate(s.x, s.y);
      ctx.rotate(s.angle);
      ctx.strokeStyle = '#38bdf8';
      ctx.lineWidth = 2.5;
      ctx.shadowColor = '#38bdf8';
      ctx.shadowBlur = 10;
      ctx.beginPath();
      ctx.moveTo(s.r + 4, 0);
      ctx.lineTo(-s.r, -s.r + 3);
      ctx.lineTo(-s.r * 0.6, 0);
      ctx.lineTo(-s.r, s.r - 3);
      ctx.closePath();
      ctx.stroke();
      ctx.restore();
    }}

    // Render Hunter Drone
    function drawDrone(ctx, d) {{
      if(!d.active) return;
      ctx.save();
      ctx.translate(d.x, d.y);
      ctx.fillStyle = '#ef4444';
      ctx.strokeStyle = '#ff6b6b';
      ctx.lineWidth = 2;
      ctx.shadowColor = '#ef4444';
      ctx.shadowBlur = 10;
      ctx.beginPath();
      ctx.arc(0, 0, d.r, 0, Math.PI*2);
      ctx.fill();
      ctx.stroke();
      ctx.restore();
    }}

    function loop() {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (gameState === 'PLAYING') {{
        if (keys['ArrowLeft'] || keys['KeyA']) ship.angle -= ship.rotSpeed;
        if (keys['ArrowRight'] || keys['KeyD']) ship.angle += ship.rotSpeed;
        if (keys['ArrowUp'] || keys['KeyW']) {{
          ship.vx += Math.cos(ship.angle) * ship.thrust;
          ship.vy += Math.sin(ship.angle) * ship.thrust;
          sndThrust();
          spawnDust(ship.x - Math.cos(ship.angle)*12, ship.y - Math.sin(ship.angle)*12, '#38bdf8');
        }}

        ship.update(canvas.width, canvas.height);
        updateLasersAndFX(canvas.width, canvas.height);
        updateAsteroids(canvas.width, canvas.height);
        maybeSpawnDrone(canvas.width, canvas.height);
        updateHunterAI(ship.x, ship.y);
        checkCollisions();
      }}

      // RENDER
      asteroids.forEach(a => drawAsteroid(ctx, a));
      drawDrone(ctx, hunterDrone);

      // Lasers
      ctx.fillStyle = '#f43f5e';
      lasers.forEach(l => ctx.fillRect(l.x - 2, l.y - 2, 4, 4));

      // Particles
      particles.forEach(p => {{
        ctx.fillStyle = p.color;
        ctx.globalAlpha = Math.max(0, p.life / p.maxLife);
        ctx.fillRect(p.x, p.y, 2, 2);
      }});
      ctx.globalAlpha = 1.0;

      // Ship
      drawShip(ctx, ship);

      // HUD
      ctx.fillStyle = '#38bdf8';
      ctx.font = '14px system-ui';
      ctx.fillText(`SCORE: ${{score}}`, 16, 26);
      ctx.fillText(`LIVES: ${{lives > 0 ? '🔺'.repeat(lives) : '💀'}}`, canvas.width - 100, 26);

      // Overlays
      if (gameState === 'START') {{
        ctx.fillStyle = 'rgba(2, 6, 23, 0.85)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#38bdf8';
        ctx.font = 'bold 24px system-ui';
        ctx.textAlign = 'center';
        ctx.fillText('NEON VECTOR ASTEROIDS', canvas.width/2, 220);
        ctx.fillStyle = '#94a3b8';
        ctx.font = '14px system-ui';
        ctx.fillText('Press SPACEBAR to Engage Audio & Fly', canvas.width/2, 260);
        ctx.textAlign = 'left';
      }} else if (gameState === 'WIN') {{
        ctx.fillStyle = 'rgba(2, 6, 23, 0.85)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#22c55e';
        ctx.font = 'bold 24px system-ui';
        ctx.textAlign = 'center';
        ctx.fillText('SECTOR CLEARED! YOU WIN!', canvas.width/2, 220);
        ctx.fillStyle = '#ffffff';
        ctx.font = '16px system-ui';
        ctx.fillText(`FINAL SCORE: ${{score}}`, canvas.width/2, 260);
        ctx.textAlign = 'left';
      }} else if (gameState === 'GAMEOVER') {{
        ctx.fillStyle = 'rgba(2, 6, 23, 0.85)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#ef4444';
        ctx.font = 'bold 24px system-ui';
        ctx.textAlign = 'center';
        ctx.fillText('SHIP DESTROYED!', canvas.width/2, 220);
        ctx.fillStyle = '#ffffff';
        ctx.font = '16px system-ui';
        ctx.fillText(`SCORE: ${{score}}`, canvas.width/2, 260);
        ctx.textAlign = 'left';
      }}

      requestAnimationFrame(loop);
    }}
    requestAnimationFrame(loop);
  </script>
</body>
</html>"""

    file_game = f"{out_dir}/neon_asteroids.html"
    with open(file_game, "w", encoding="utf-8") as f:
        f.write(game_html)

    t_global = time.perf_counter() - t_global_start
    total_tokens = sum(r["tokens"] for r in results.values())
    total_jev = sum(r["jev_time"] for r in results.values()) + t_plan

    print(f"\n✅ Heterogeneous Swarm Synthesis Finished in {t_global:.2f}s!")
    print(f"   - Total Tokens Generated: {total_tokens}")
    print(f"   - Total Jev Verification Overhead: {total_jev:.2f}s")
    print(f"   - Saved to: {file_game}")

    # Phase 4: Jev Audit
    print("\n[Phase 4: Jev Final Quality Audit]")
    audit, t_aud = call_jev({
        "state": f"## Complete Heterogeneous Neon Asteroids HTML5 Game\n\n{game_html}",
        "model": "jev-latest",
        "questions": {
            "is_complete_and_playable": {
                "type": "noul",
                "instructions": "Is this complete, valid HTML5 Canvas Asteroids game with rotation physics, procedural asteroid fracturing, hunter drone AI, and immediately playable?"
            },
            "code_quality": {
                "type": "score",
                "instructions": "Rate code structure, modularity, and cleanliness",
                "range": [0, 3],
                "criteria": ["Broken", "Fragile", "Clean & working", "Exemplary production-grade"]
            }
        }
    })
    
    # Node.js Syntax Verification
    script_match = re.search(r"<script>(.*?)</script>", game_html, re.DOTALL)
    if script_match:
        with open("/tmp/verify_asteroids.js", "w") as vf:
            vf.write(script_match.group(1))
        node_res = subprocess.run(["node", "-c", "/tmp/verify_asteroids.js"], capture_output=True, text=True)
        print(f"\nNode.js Syntax Verification: Returncode {node_res.returncode}")
        if node_res.returncode != 0:
            print("Syntax error:\n", node_res.stderr)
    noul_play = audit.get("answers", {}).get("is_complete_and_playable", {}).get("noul", 0.0)
    score_qual = audit.get("answers", {}).get("code_quality", {}).get("score", 0.0)
    print(f"   - Jev Playable Probability (Noul): {noul_play:.3f} {'✅' if noul_play >= 0.7 else '❌'}")
    print(f"   - Jev Code Quality Score: {score_qual:.2f} / 3.0")

    metrics = {
        "experiment": "Experiment 2: Heterogeneous Swarm Tiering (1.5B + 3B)",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_wall_clock_seconds": round(t_global, 2),
        "total_tokens": total_tokens,
        "total_jev_overhead_seconds": round(total_jev, 2),
        "workers": results,
        "final_audit": {
            "playable_noul": round(noul_play, 3),
            "quality_score": round(score_qual, 2)
        },
        "file": file_game
    }
    with open(f"{out_dir}/exp2_results.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

if __name__ == "__main__":
    main()
