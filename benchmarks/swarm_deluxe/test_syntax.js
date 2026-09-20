
    const canvas = document.getElementById('c');
    const ctx = canvas.getContext('2d');
    let gameState = 'START'; // START, PLAYING, WIN, GAMEOVER
    let lastPlayerLaser = 0;

    // --- WORKER 1: PLAYER CANNON ---
    let player = {
    x: 200,
    y: 460,
    width: 36,
    height: 18,
    vx: 0,
    speed: 5,
    friction: 0.85,
    update: function(canvasWidth) {
        this.x += this.vx;
        this.vx *= this.friction;
        this.x = Math.max(10, Math.min(canvasWidth - this.width - 10, this.x));
    }
};

    // --- WORKER 2: INVADER FLEET ---
    let invaders = [];
let invaderDir = 1;
let invaderSpeed = 1.2;

function createInvaders() {
    invaders = [];
    for(let r = 0; r < 4; r++) {
        for(let c = 0; c < 6; c++) {
            invaders.push({ x: 40 + c * 50, y: 60 + r * 32, w: 26, h: 18, alive: true, scoreVal: (4 - r) * 10 });
        }
    }
}

function updateInvaders(canvasWidth) {
    let edge = false;
    invaders.forEach(i => {
        if (i.alive) {
            i.x += invaderDir * invaderSpeed;
            if (i.x <= 10 || i.x >= canvasWidth - 36) edge = true;
        }
    });
    if (edge) {
        invaderDir *= -1;
        invaders.forEach(i => {
            i.y += 14;
        });
        invaderSpeed = Math.min(3.5, invaderSpeed * 1.05);

    // --- WORKER 3: BALLISTICS (LASERS & BOMBS) ---
    let lasers = [];
let bombs = [];

function fireLaser() {
    lasers.push({ x: player.x + player.width / 2 - 2, y: player.y, w: 4, h: 10, vy: -7 });
}

function maybeAlienBomb() {
    let aliveOnes = invaders.filter(i => i.alive);
    if (aliveOnes.length > 0 && Math.random() < 0.03) {
        let shooter = aliveOnes[Math.floor(Math.random() * aliveOnes.length)];
        bombs.push({ x: shooter.x + shooter.w / 2, y: shooter.y + shooter.h, w: 3, h: 8, vy: 3.5 });
    }
}

function updateBallistics() {
    lasers.forEach(l => l.y += l.vy);
    bombs.forEach(b => b.y += b.vy);
    lasers = lasers.filter(l => l.y > 0);
    bombs = bombs.filter(b => b.y < 520);
}

    // --- WORKER 4: PARTICLE EXPLOSION ENGINE ---
    let particles = [];
function spawnExplosion(x, y, color) {
    for(let i = 0; i < 12; i++) {
        const angle = Math.random() * Math.PI * 2;
        const speed = Math.random() * 3 + 1;
        particles.push({ x: x, y: y, vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed, alpha: 1.0, color: color || '#22c55e', size: Math.random() * 3 + 2 });
    }
}

function updateAndDrawParticles(ctx) {
    particles.forEach(p => {
        p.x += p.vx;
        p.y += p.vy;
        p.alpha -= 0.03;
        ctx.save();
        ctx.globalAlpha = Math.max(0, p.alpha);
        ctx.fillStyle = p.color;
        ctx.fillRect(p.x, p.y, p.size, p.size);
        ctx.restore();
    });
    particles = particles.filter(p => p.alpha > 0);
}

    // --- WORKER 5: 8-BIT CHIPTUNE SYNTHESIZER ---
    let audioCtx = null;

function initAudio() {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
}

function playTone(freq, duration, type) {
    if (!audioCtx) return;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = type || 'square';
    osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
    gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + duration);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + duration);
}

function sfxLaser() {
    playTone(880, 0.1, 'sawtooth');
}

function sfxExplosion() {
    playTone(120, 0.25, 'triangle');
}

    // --- WORKER 6: MYSTERY FLYING UFO ---
    let ufo = { x: -60, y: 35, w: 40, h: 14, speed: 2, active: false, scoreVal: 200 };

function maybeSpawnUFO() {
    if (!ufo.active && Math.random() < 0.003) {
        ufo.active = true;
        ufo.x = -50;
    }
}

function updateUFO(canvasWidth) {
    if (ufo.active) {
        ufo.x += ufo.speed;
        if (ufo.x > canvasWidth + 50) ufo.active = false;
    }
}

function drawUFO(ctx) {
    if (!ufo.active) return;
    ctx.fillStyle = '#ef4444';
    ctx.fillRect(ufo.x, ufo.y + 4, ufo.w, ufo.h - 4);
    ctx.fillRect(ufo.x + 8, ufo.y, ufo.w - 16, 6);
}

    // --- WORKER 7: DESTRUCTIBLE BUNKERS ---
    let bunkers = [];
function createBunkers() {
    bunkers = [];
    for(let b = 0; b < 4; b++) {
        const bx = 50 + b * 95;
        for(let r = 0; r < 3; r++) {
            for(let c = 0; c < 4; c++) {
                bunkers.push({x: bx + c*8, y: 400 + r*8, w: 8, h: 8, hp: 1});
            }
        }
    }
}

function drawBunkers(ctx) {
    ctx.fillStyle = '#22c55e';
    bunkers.forEach(b => {
        if(b.hp > 0) ctx.fillRect(b.x, b.y, b.w, b.h);
    });
}

    // --- WORKER 8: SCORE & HUD ---
    let score = 0;
let lives = 3;
let highScore = parseInt(localStorage.getItem('si_highscore') || '0');

function addScore(pts) {
    score += pts;
    if (score > highScore) {
        highScore = score;
        localStorage.setItem('si_highscore', highScore);
    }
}

function drawHUD(ctx, width) {
    ctx.fillStyle = '#22c55e';
    ctx.font = '14px monospace';
    ctx.fillText('SCORE: ' + score, 16, 24);
    ctx.fillText('LIVES: ' + '❤️'.repeat(lives), width / 2 - 40, 24);
    ctx.fillText('BEST: ' + highScore, width - 110, 24);
}

    // Controls
    const keys = {};
    window.addEventListener('keydown', (e) => {
      keys[e.code] = true;
      if (e.code === 'Space') {
        e.preventDefault();
        initAudio();
        if (gameState !== 'PLAYING') {
          initGame();
        } else {
          const now = Date.now();
          if (now - lastPlayerLaser > 220) {
            fireLaser();
            sfxLaser();
            lastPlayerLaser = now;
          }
        }
      }
    });
    window.addEventListener('keyup', (e) => { keys[e.code] = false; });

    function initGame() {
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
    }

    createInvaders();
    createBunkers();

    // Custom Sprite Renderers
    function drawRetroInvader(x, y, w, h, scoreVal) {
      const colors = { 40: '#f43f5e', 30: '#a855f7', 20: '#38bdf8', 10: '#22c55e' };
      ctx.fillStyle = colors[scoreVal] || '#22c55e';
      ctx.fillRect(x + 4, y, w - 8, h);
      ctx.fillRect(x, y + 4, w, h - 8);
      ctx.fillStyle = '#080c14';
      ctx.fillRect(x + 5, y + 5, 4, 4);
      ctx.fillRect(x + w - 9, y + 5, 4, 4);
    }

    function drawPlayerCannon(x, y, w, h) {
      ctx.fillStyle = '#38bdf8';
      ctx.fillRect(x, y + 8, w, h - 8);
      ctx.fillRect(x + w/2 - 4, y, 8, 8);
      ctx.fillStyle = '#bae6fd';
      ctx.fillRect(x + 4, y + 10, w - 8, 3);
    }

    // Master Collision Checker
    function checkInteractions() {
      // Laser hits Invaders
      lasers.forEach(l => {
        invaders.forEach(inv => {
          if (inv.alive && l.x > inv.x && l.x < inv.x + inv.w && l.y > inv.y && l.y < inv.y + inv.h) {
            inv.alive = false;
            l.y = -20;
            addScore(inv.scoreVal);
            spawnExplosion(inv.x + inv.w/2, inv.y + inv.h/2, '#22c55e');
            sfxExplosion();
          }
        });
        // Laser hits UFO
        if (ufo.active && l.x > ufo.x && l.x < ufo.x + ufo.w && l.y > ufo.y && l.y < ufo.y + ufo.h) {
          ufo.active = false;
          l.y = -20;
          addScore(ufo.scoreVal);
          spawnExplosion(ufo.x + ufo.w/2, ufo.y + ufo.h/2, '#ef4444');
          sfxExplosion();
        }
        // Laser hits Bunkers
        bunkers.forEach(b => {
          if (b.hp > 0 && l.x > b.x && l.x < b.x + b.w && l.y > b.y && l.y < b.y + b.h) {
            b.hp = 0;
            l.y = -20;
            spawnExplosion(b.x, b.y, '#22c55e');
          }
        });
      });

      // Bombs hit Player
      bombs.forEach(b => {
        if (b.x > player.x && b.x < player.x + player.width && b.y > player.y && b.y < player.y + player.height) {
          b.y = 999;
          lives--;
          spawnExplosion(player.x + player.width/2, player.y + player.height/2, '#38bdf8');
          sfxExplosion();
          if (lives <= 0) gameState = 'GAMEOVER';
        }
        // Bombs hit Bunkers
        bunkers.forEach(bk => {
          if (bk.hp > 0 && b.x > bk.x && b.x < bk.x + bk.w && b.y > bk.y && b.y < bk.y + bk.h) {
            bk.hp = 0;
            b.y = 999;
          }
        });
      });
    }

    // Master Game Loop
    function loop() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (gameState === 'PLAYING') {
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
      }

      // RENDER SCENE
      drawBunkers(ctx);
      drawUFO(ctx);

      // Draw Invaders
      invaders.forEach(i => {
        if (i.alive) drawRetroInvader(i.x, i.y, i.w, i.h, i.scoreVal);
      });

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
      if (gameState === 'START') {
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
      } else if (gameState === 'WIN') {
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
      } else if (gameState === 'GAMEOVER') {
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
      }

      requestAnimationFrame(loop);
    }

    requestAnimationFrame(loop);
  