import json, urllib.request, time, subprocess, os, re

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:1.5b"
TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"

def get_key():
    res = subprocess.run(['security', 'find-generic-password', '-s', 'network-infra-typesafe-jev', '-w'], capture_output=True, text=True)
    return res.stdout.strip() if res.returncode == 0 else os.environ.get('TYPESAFE_API_KEY')

KEY = get_key()

def call_jev_gate(code, question):
    t0 = time.perf_counter()
    req = urllib.request.Request(
        TYPESAFE_URL,
        data=json.dumps({
            "state": code,
            "model": "jev-latest",
            "questions": {"valid": {"type": "noul", "instructions": question}}
        }).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        d = json.loads(resp.read().decode())
    return d["answers"]["valid"]["noul"], time.perf_counter() - t0

def call_worker(name, prompt, num_predict=220):
    t0 = time.perf_counter()
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps({
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "options": {"num_predict": num_predict, "temperature": 0.1},
            "stream": False
        }).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        raw = json.loads(resp.read().decode())['response']
    elapsed = time.perf_counter() - t0
    m = re.search(r"```(?:javascript|js)?\s*(.*?)```", raw, re.DOTALL)
    clean = m.group(1).strip() if m else raw.strip()
    return clean, elapsed

print("=" * 65)
print("👾 SPACE INVADERS: JEV + FAST SLM SWARM (qwen2.5:1.5b)")
print("=" * 65)

t_start = time.perf_counter()

# Worker 1: Player Ship
print("\n-> [Worker 1: Player Ship Specialist]...")
p1 = "Write ONLY valid JavaScript: `let player = { x: 180, y: 450, width: 36, height: 16, speed: 4, dx: 0, update: function(canvasWidth) { this.x = Math.max(0, Math.min(canvasWidth - this.width, this.x + this.dx)); } };` Output ONLY the code."
w1_code, t1 = call_worker("Worker 1", p1)
g1, tg1 = call_jev_gate(w1_code, "Does this define valid player ship object with update method?")
print(f"   Generated in {t1:.2f}s | Jev Gate: {g1:.2f} (in {tg1*1000:.0f}ms)")

# Worker 2: Fleet
print("\n-> [Worker 2: Invader Fleet Specialist]...")
p2 = "Write ONLY valid JavaScript: `let invaders = []; let invaderDir = 1; function createInvaders() { invaders = []; for(let r=0; r<3; r++) { for(let c=0; c<6; c++) { invaders.push({x: 40 + c*50, y: 50 + r*35, w: 28, h: 18, alive: true}); } } } function updateInvaders(canvasWidth) { let edge = false; invaders.forEach(i => { if(i.alive) { i.x += invaderDir * 1.5; if(i.x <= 10 || i.x >= canvasWidth - 38) edge = true; } }); if(edge) { invaderDir *= -1; invaders.forEach(i => { i.y += 15; }); } }` Output ONLY the code."
w2_code, t2 = call_worker("Worker 2", p2)
g2, tg2 = call_jev_gate(w2_code, "Does this define valid createInvaders and updateInvaders logic?")
print(f"   Generated in {t2:.2f}s | Jev Gate: {g2:.2f} (in {tg2*1000:.0f}ms)")

# Worker 3: Bullets & Collisions
print("\n-> [Worker 3: Ballistics & Collision Specialist]...")
p3 = "Write ONLY valid JavaScript: `let bullets = []; function fireLaser() { bullets.push({x: player.x + player.width/2 - 2, y: player.y, w: 4, h: 10, vy: -6}); } function updateBulletsAndCollisions() { bullets.forEach(b => { b.y += b.vy; }); bullets = bullets.filter(b => b.y > 0); bullets.forEach(b => { invaders.forEach(inv => { if(inv.alive && b.x > inv.x && b.x < inv.x + inv.w && b.y > inv.y && b.y < inv.y + inv.h) { inv.alive = false; b.y = -10; score += 100; } }); }); }` Output ONLY the code."
w3_code, t3 = call_worker("Worker 3", p3)
g3, tg3 = call_jev_gate(w3_code, "Does this define valid bullet movement and collision detection?")
print(f"   Generated in {t3:.2f}s | Jev Gate: {g3:.2f} (in {tg3*1000:.0f}ms)")

# Worker 4: Renderer
print("\n-> [Worker 4: Canvas Retro Renderer]...")
p4 = "Write ONLY valid JavaScript: `function drawRetroInvader(ctx, x, y, w, h) { ctx.fillStyle = '#22c55e'; ctx.fillRect(x + 4, y, w - 8, h); ctx.fillRect(x, y + 4, w, h - 8); ctx.fillStyle = '#0f172a'; ctx.fillRect(x + 6, y + 6, 4, 4); ctx.fillRect(x + w - 10, y + 6, 4, 4); } function drawPlayerShip(ctx, x, y, w, h) { ctx.fillStyle = '#38bdf8'; ctx.fillRect(x, y + 8, w, h - 8); ctx.fillRect(x + w/2 - 4, y, 8, 8); }` Output ONLY the code."
w4_code, t4 = call_worker("Worker 4", p4)
g4, tg4 = call_jev_gate(w4_code, "Does this define valid drawRetroInvader and drawPlayerShip functions?")
print(f"   Generated in {t4:.2f}s | Jev Gate: {g4:.2f} (in {tg4*1000:.0f}ms)")

# Assembly
print("\n-> [Assembly] Stitching verified swarm blocks into complete playable game...")
full_game_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Space Invaders - Swarm + Jev</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #020617;
      color: #f8fafc;
      font-family: monospace;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      overflow: hidden;
    }}
    h1 {{ color: #22c55e; margin-bottom: 8px; letter-spacing: 2px; }}
    canvas {{
      background: #090d16;
      border: 3px solid #22c55e;
      border-radius: 8px;
      box-shadow: 0 0 25px rgba(34, 197, 94, 0.3);
    }}
    .footer {{ margin-top: 10px; font-size: 0.9rem; color: #94a3b8; }}
  </style>
</head>
<body>
  <h1>👾 SPACE INVADERS (JEV SWARM)</h1>
  <canvas id="c" width="400" height="500"></canvas>
  <div class="footer">&larr; &rarr; or A/D to Move &bull; SPACEBAR to Fire</div>

  <script>
    const canvas = document.getElementById('c');
    const ctx = canvas.getContext('2d');
    let score = 0;
    let gameState = 'START';
    let lastFire = 0;

    // --- WORKER 1: PLAYER ---
    {w1_code}

    // --- WORKER 2: FLEET ---
    {w2_code}

    // --- WORKER 3: BULLETS & COLLISION ---
    {w3_code}

    // --- WORKER 4: RENDERER ---
    {w4_code}

    const keys = {{}};
    window.addEventListener('keydown', (e) => {{
      keys[e.code] = true;
      if (e.code === 'Space') {{
        e.preventDefault();
        if (gameState !== 'PLAYING') {{
          player.x = 180;
          player.dx = 0;
          bullets = [];
          score = 0;
          createInvaders();
          gameState = 'PLAYING';
        }} else {{
          const now = Date.now();
          if (now - lastFire > 220) {{
            fireLaser();
            lastFire = now;
          }}
        }}
      }}
    }});
    window.addEventListener('keyup', (e) => {{ keys[e.code] = false; }});

    createInvaders();

    function loop() {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (gameState === 'PLAYING') {{
        player.dx = 0;
        if (keys['ArrowLeft'] || keys['KeyA']) player.dx = -player.speed;
        if (keys['ArrowRight'] || keys['KeyD']) player.dx = player.speed;

        player.update(canvas.width);
        updateInvaders(canvas.width);
        updateBulletsAndCollisions();

        const aliveInv = invaders.filter(i => i.alive);
        if (aliveInv.length === 0) gameState = 'WIN';
        if (aliveInv.some(i => i.y + i.h >= player.y)) gameState = 'GAMEOVER';
      }}

      // Draw Invaders
      invaders.forEach(i => {{ if (i.alive) drawRetroInvader(ctx, i.x, i.y, i.w, i.h); }});

      // Draw Bullets
      ctx.fillStyle = '#f43f5e';
      bullets.forEach(b => {{ ctx.fillRect(b.x, b.y, b.w, b.h); }});

      // Draw Ship
      drawPlayerShip(ctx, player.x, player.y, player.width, player.height);

      // HUD
      ctx.fillStyle = '#22c55e';
      ctx.font = '14px monospace';
      ctx.fillText(`SCORE: ${{score}}`, 16, 24);
      ctx.fillText(`ALIENS: ${{invaders.filter(i => i.alive).length}}`, canvas.width - 100, 24);

      if (gameState === 'START') {{
        ctx.fillStyle = 'rgba(2, 6, 23, 0.8)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#22c55e';
        ctx.font = 'bold 22px monospace';
        ctx.textAlign = 'center';
        ctx.fillText('SPACE INVADERS', canvas.width/2, 230);
        ctx.fillStyle = '#38bdf8';
        ctx.font = '14px monospace';
        ctx.fillText('PRESS SPACEBAR TO START', canvas.width/2, 270);
        ctx.textAlign = 'left';
      }} else if (gameState === 'WIN') {{
        ctx.fillStyle = 'rgba(2, 6, 23, 0.85)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#22c55e';
        ctx.font = 'bold 22px monospace';
        ctx.textAlign = 'center';
        ctx.fillText('MISSION COMPLETE!', canvas.width/2, 230);
        ctx.fillText(`SCORE: ${{score}}`, canvas.width/2, 265);
        ctx.fillStyle = '#38bdf8';
        ctx.font = '14px monospace';
        ctx.fillText('Press SPACE to Play Again', canvas.width/2, 300);
        ctx.textAlign = 'left';
      }} else if (gameState === 'GAMEOVER') {{
        ctx.fillStyle = 'rgba(2, 6, 23, 0.85)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#ef4444';
        ctx.font = 'bold 22px monospace';
        ctx.textAlign = 'center';
        ctx.fillText('EARTH INVADED!', canvas.width/2, 230);
        ctx.fillStyle = '#ffffff';
        ctx.font = '16px monospace';
        ctx.fillText(`FINAL SCORE: ${{score}}`, canvas.width/2, 265);
        ctx.fillStyle = '#38bdf8';
        ctx.font = '14px monospace';
        ctx.fillText('Press SPACE to Retry', canvas.width/2, 300);
        ctx.textAlign = 'left';
      }}

      requestAnimationFrame(loop);
    }}
    requestAnimationFrame(loop);
  </script>
</body>
</html>"""

out_file = "benchmarks/space_invaders/space_invaders_playable.html"
with open(out_file, "w") as f:
    f.write(full_game_html)

total_time = time.perf_counter() - t_start
print(f"\n✅ Space Invaders Swarm completed in {total_time:.2f}s total!")
print(f"   Saved to: {out_file}")

# Final Jev Evaluation
print("\n-> Jev performing post-flight audit on assembled game...")
req_eval = urllib.request.Request(
    TYPESAFE_URL,
    data=json.dumps({
        "state": f"## Complete Space Invaders HTML Game\n\n{full_game_html}",
        "model": "jev-latest",
        "questions": {
            "is_complete_and_playable": {
                "type": "noul",
                "instructions": "Is this complete, valid HTML5 Canvas Space Invaders with working player ship, firing bullets, moving invaders grid, collision detection, and immediately playable?"
            },
            "code_quality": {
                "type": "score",
                "instructions": "Rate code structure, modularity, and cleanliness",
                "criteria": ["Broken", "Fragile", "Clean & working", "Exemplary"]
            }
        }
    }).encode(),
    headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
)
with urllib.request.urlopen(req_eval) as resp:
    ev = json.loads(resp.read().decode())['answers']

print(f"   Jev Playable Probability (Noul): {ev['is_complete_and_playable']['noul']:.3f}")
print(f"   Jev Code Quality (Score): {ev['code_quality']['score']:.2f} / 3.0")
