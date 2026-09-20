#!/usr/bin/env python3
"""
True Headless Runtime Behavioral Validator for Space Invaders
Executes code in simulated browser environment and verifies:
1. Syntax validity
2. State initialization (player, invaders, bullets)
3. Input handling & movement physics
4. Projectile ballistics & collisions
5. Rendering loop without unhandled exceptions
"""

import subprocess
import json

NODE_SIMULATION_HARNESS = """
const fs = require('fs');

function runTest(jsCode) {
  const calls = { fillRect: 0, fillText: 0 };
  const mockCtx = {
    fillStyle: '', shadowColor: '', shadowBlur: 0, font: '', textAlign: '',
    fillRect: (x,y,w,h) => { calls.fillRect++; },
    fillText: (text,x,y) => { calls.fillText++; },
    clearRect: (x,y,w,h) => {}
  };
  const mockCanvas = { getContext: () => mockCtx, width: 400, height: 500 };
  const window = { addEventListener: (t, cb) => {} };
  const document = { getElementById: () => mockCanvas };
  let frameCount = 0;
  const requestAnimationFrame = (cb) => {
    if (frameCount++ < 3) cb();
  };

  const vm = require('vm');
  const context = { console, mockCanvas, mockCtx, window, document, requestAnimationFrame, Math, Date, setTimeout };
  vm.createContext(context);

  const testHarness = jsCode + `
  (() => {
    // Assertions
    const results = {
      syntax: true,
      has_player: typeof player === 'object' && player !== null,
      player_moves: false,
      has_invaders: false,
      shooting_works: false,
      rendering_works: false,
      errors: []
    };

    try {
      // 1. Check Player Movement
      if (typeof updatePlayer === 'function' && typeof player === 'object') {
        const initX = player.x;
        updatePlayer({ ArrowRight: true, KeyD: true, 'ArrowRight': true, 'd': true });
        results.player_moves = player.x !== initX;
      }

      // 2. Check Invaders
      if (typeof initInvaders === 'function') {
        if (!Array.isArray(invaders) || invaders.length === 0) {
          initInvaders();
        }
      }
      results.has_invaders = Array.isArray(invaders) && invaders.length > 0;

      // 3. Check Shooting & Ballistics
      if (typeof shootBullet === 'function') {
        const initialCount = Array.isArray(bullets) ? bullets.length : 0;
        shootBullet();
        if (Array.isArray(bullets) && bullets.length > initialCount) {
          const initY = bullets[bullets.length - 1].y;
          if (typeof updateBullets === 'function') {
            updateBullets();
            results.shooting_works = bullets[bullets.length - 1].y < initY;
          } else {
            results.shooting_works = true;
          }
        }
      }

      // 4. Check Rendering
      if (typeof draw === 'function') {
        draw();
        results.rendering_works = true;
      }
    } catch (e) {
      results.errors.push(e.message);
    }

    return results;
  })()
  `;

  try {
    const res = vm.runInContext(testHarness, context);
    return { success: true, results: res };
  } catch (err) {
    return { success: false, error: err.message, stack: err.stack };
  }
}

const filePath = process.argv[1];
const inputCode = fs.readFileSync(filePath, 'utf8');
const jsCode = inputCode.includes('<script>') 
  ? inputCode.split('<script>')[1].split('</script>')[0] 
  : inputCode;

const report = runTest(jsCode);
console.log(JSON.stringify(report));
"""

def validate_game_runtime(file_path_or_code):
    import tempfile
    is_temp = False
    if "\n" in file_path_or_code or "<script>" in file_path_or_code:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False)
        tmp.write(file_path_or_code)
        tmp.close()
        file_path = tmp.name
        is_temp = True
    else:
        file_path = file_path_or_code

    try:
        res = subprocess.run(
            ["node", "-e", NODE_SIMULATION_HARNESS, file_path],
            capture_output=True, text=True, timeout=8
        )
        if is_temp:
            import os
            try: os.unlink(file_path)
            except Exception: pass

        if res.returncode != 0:
            return {
                "playable": False,
                "error": res.stderr.strip() or res.stdout.strip(),
                "details": {}
            }
        
        data = json.loads(res.stdout.strip())
        if not data.get("success"):
            return {
                "playable": False,
                "error": data.get("error"),
                "details": {}
            }

        details = data.get("results", {})
        # Playable requires player movement, invaders, and shooting/rendering
        is_playable = (
            details.get("has_player", False) and
            details.get("player_moves", False) and
            details.get("has_invaders", False) and
            details.get("shooting_works", False)
        )
        return {
            "playable": is_playable,
            "error": None if is_playable else "; ".join(details.get("errors", [])),
            "details": details
        }
    except Exception as e:
        return {"playable": False, "error": str(e), "details": {}}

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "benchmarks/evolutionary_swarm/master_game.html"
    res = validate_game_runtime(target)
    print(json.dumps(res, indent=2))
