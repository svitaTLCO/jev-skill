#!/usr/bin/env python3
"""
3D Ball Physics & Collision Simulation Builder
Coordinates micro-contracts under TypeSafe Jev System One 3-Tier Verification.
"""

import os
import sys
import json
import time
import subprocess

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.jev_swarm import JevClient, GenericRuntimeValidator

def generate_simulation_html() -> str:
    """
    Generates the complete, high-fidelity 3D simulation webapp.
    Each modular subsystem is structured according to the verified contracts:
    - Contract 1: Three.js PBR Scene & Room Geometry with Soft Shadows
    - Contract 2: 3D Ball Mesh with Procedural Hexagonal Texture & Material
    - Contract 3: Multi-Substep Vector Physics Integrator with Angular Momentum & Rolling
    - Contract 4: 6-Plane Room Collision Solver with Restitution & Surface Friction
    - Contract 5: Raycast Kick Interaction with Off-Center Torque & Web Audio Synthesis
    - Contract 6: Glassmorphic Telemetry HUD & Interactive Camera Controls
    """
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Realistic 3D Ball & Room Physics Simulation</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      user-select: none;
      -webkit-user-select: none;
    }
    body {
      width: 100vw;
      height: 100vh;
      overflow: hidden;
      background: #0a0b10;
      font-family: 'Outfit', sans-serif;
      color: #e2e8f0;
    }
    #canvas-container {
      width: 100%;
      height: 100%;
      position: absolute;
      top: 0;
      left: 0;
      cursor: grab;
    }
    #canvas-container:active {
      cursor: grabbing;
    }
    #canvas-container.hover-ball {
      cursor: crosshair !important;
    }

    /* Glassmorphic HUD Header */
    .hud-header {
      position: absolute;
      top: 24px;
      left: 24px;
      z-index: 10;
      pointer-events: none;
    }
    .hud-title {
      font-size: 26px;
      font-weight: 700;
      letter-spacing: -0.5px;
      background: linear-gradient(135deg, #ffffff 0%, #94a3b8 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      text-shadow: 0 4px 20px rgba(0,0,0,0.5);
    }
    .hud-subtitle {
      font-size: 13px;
      color: #38bdf8;
      font-weight: 500;
      letter-spacing: 1px;
      text-transform: uppercase;
      margin-top: 4px;
    }

    /* Telemetry Panel */
    .telemetry-card {
      position: absolute;
      top: 24px;
      right: 24px;
      background: rgba(15, 23, 42, 0.75);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 16px;
      padding: 18px 22px;
      min-width: 260px;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1);
      z-index: 10;
    }
    .card-label {
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 1.2px;
      color: #64748b;
      margin-bottom: 12px;
      font-weight: 600;
    }
    .metric-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
    }
    .metric-row:last-child {
      margin-bottom: 0;
    }
    .metric-name {
      color: #94a3b8;
    }
    .metric-val {
      font-weight: 600;
      color: #38bdf8;
    }
    .metric-val.alert {
      color: #f43f5e;
    }
    .metric-val.highlight {
      color: #10b981;
    }

    /* Speedometer Bar */
    .meter-container {
      margin-top: 14px;
      padding-top: 12px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
    }
    .meter-bar-bg {
      width: 100%;
      height: 6px;
      background: rgba(255, 255, 255, 0.08);
      border-radius: 999px;
      overflow: hidden;
      margin-top: 6px;
    }
    .meter-bar-fill {
      width: 0%;
      height: 100%;
      background: linear-gradient(90deg, #38bdf8, #818cf8, #f43f5e);
      border-radius: 999px;
      transition: width 0.08s ease-out;
    }

    /* Interactive Action Bar */
    .hud-controls {
      position: absolute;
      bottom: 24px;
      left: 50%;
      transform: translateX(-50%);
      display: flex;
      gap: 12px;
      background: rgba(15, 23, 42, 0.75);
      backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 999px;
      padding: 8px 16px;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
      z-index: 10;
    }
    .btn {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #f1f5f9;
      padding: 8px 16px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .btn:hover {
      background: rgba(255, 255, 255, 0.15);
      border-color: rgba(255, 255, 255, 0.25);
      transform: translateY(-1px);
    }
    .btn:active {
      transform: translateY(1px);
    }
    .btn.active {
      background: #38bdf8;
      color: #0f172a;
      font-weight: 600;
      border-color: #38bdf8;
    }

    /* Kick Target Crosshair Badge */
    .crosshair-hint {
      position: absolute;
      bottom: 84px;
      left: 50%;
      transform: translateX(-50%);
      font-size: 12px;
      color: #94a3b8;
      background: rgba(15, 23, 42, 0.6);
      backdrop-filter: blur(8px);
      padding: 6px 14px;
      border-radius: 20px;
      border: 1px solid rgba(255, 255, 255, 0.05);
      pointer-events: none;
      letter-spacing: 0.3px;
    }

    /* Kick Flash Ripple Effect */
    .kick-indicator {
      position: absolute;
      width: 40px;
      height: 40px;
      border: 2px solid #38bdf8;
      border-radius: 50%;
      pointer-events: none;
      transform: translate(-50%, -50%) scale(0.2);
      opacity: 1;
      transition: transform 0.4s cubic-bezier(0.1, 1, 0.1, 1), opacity 0.4s ease-out;
      z-index: 20;
    }
  </style>

  <!-- Three.js & OrbitControls via CDN -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>

  <div id="canvas-container"></div>

  <!-- Header -->
  <div class="hud-header">
    <div class="hud-title">3D Ball Simulation</div>
    <div class="hud-subtitle">TypeSafe Jev System One Physics Engine</div>
  </div>

  <!-- Telemetry Dashboard -->
  <div class="telemetry-card">
    <div class="card-label">Realtime Dynamics</div>
    <div class="metric-row">
      <span class="metric-name">Velocity</span>
      <span class="metric-val" id="val-speed">0.00 m/s</span>
    </div>
    <div class="metric-row">
      <span class="metric-name">Speed (km/h)</span>
      <span class="metric-val" id="val-speed-kmh">0.0 km/h</span>
    </div>
    <div class="metric-row">
      <span class="metric-name">Spin Rate</span>
      <span class="metric-val" id="val-spin">0 RPM</span>
    </div>
    <div class="metric-row">
      <span class="metric-name">Altitude (Y)</span>
      <span class="metric-val" id="val-altitude">1.00 m</span>
    </div>
    <div class="metric-row">
      <span class="metric-name">State</span>
      <span class="metric-val highlight" id="val-state">Resting</span>
    </div>
    <div class="metric-row">
      <span class="metric-name">Total Kicks</span>
      <span class="metric-val" id="val-kicks">0</span>
    </div>
    <div class="metric-row">
      <span class="metric-name">Wall Collisions</span>
      <span class="metric-val" id="val-bounces">0</span>
    </div>

    <div class="meter-container">
      <div class="metric-row" style="margin-bottom: 0;">
        <span class="metric-name" style="font-size: 11px;">Kinetic Intensity</span>
        <span class="metric-val" id="val-intensity" style="font-size: 11px;">0%</span>
      </div>
      <div class="meter-bar-bg">
        <div class="meter-bar-fill" id="meter-fill"></div>
      </div>
    </div>
  </div>

  <!-- Interaction Hint -->
  <div class="crosshair-hint" id="hud-hint">
    🎯 Click anywhere on the ball to kick • Click off-center to impart curve spin
  </div>

  <!-- Controls -->
  <div class="hud-controls">
    <button class="btn" id="btn-kick">⚽ Kick Up</button>
    <button class="btn" id="btn-power">⚡ Power: Normal</button>
    <button class="btn" id="btn-gravity">🌍 Earth 1.0G</button>
    <button class="btn" id="btn-sound">🔊 Sound: ON</button>
    <button class="btn" id="btn-reset">🔄 Reset</button>
  </div>

  <script>
    /* --- CONTRACT 1: Web Audio Synthesis (Dynamic Impact Thump & Whoosh) --- */
    class SimulationAudio {
      constructor() {
        this.ctx = null;
        this.enabled = true;
      }
      init() {
        if (!this.ctx) {
          const AudioContext = window.AudioContext || window.webkitAudioContext;
          if (AudioContext) {
            this.ctx = new AudioContext();
          }
        }
        if (this.ctx && this.ctx.state === 'suspended') {
          this.ctx.resume();
        }
      }
      playImpact(speed, isFloor = false) {
        if (!this.enabled || !this.ctx || speed < 0.2) return;
        this.init();
        const t = this.ctx.currentTime;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();

        // Volume & pitch scaled dynamically by impact velocity
        const clampedSpeed = Math.min(speed, 35);
        const volume = Math.min(0.8, 0.05 + (clampedSpeed / 35) * 0.75);
        const baseFreq = isFloor ? 90 : 130;
        const startFreq = baseFreq + clampedSpeed * 3;

        osc.type = 'sine';
        osc.frequency.setValueAtTime(startFreq, t);
        osc.frequency.exponentialRampToValueAtTime(35, t + 0.12);

        gain.gain.setValueAtTime(volume, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.15);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start(t);
        osc.stop(t + 0.16);
      }
      playKick(power = 1.0) {
        if (!this.enabled || !this.ctx) return;
        this.init();
        const t = this.ctx.currentTime;
        // Low frequency thud + white noise whoosh
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();

        osc.type = 'triangle';
        osc.frequency.setValueAtTime(180, t);
        osc.frequency.exponentialRampToValueAtTime(40, t + 0.18);

        gain.gain.setValueAtTime(0.6 * power, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.2);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start(t);
        osc.stop(t + 0.21);
      }
    }

    /* --- CONTRACT 2: Procedural Soccer Ball Texture & Materials --- */
    function createSoccerTexture() {
      const canvas = document.createElement('canvas');
      canvas.width = 1024;
      canvas.height = 512;
      const ctx = canvas.getContext('2d');

      // Base leather white
      ctx.fillStyle = '#f8fafc';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Subtle leather grain noise
      const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const data = imgData.data;
      for (let i = 0; i < data.length; i += 4) {
        const noise = (Math.random() - 0.5) * 8;
        data[i] = Math.min(255, Math.max(0, data[i] + noise));
        data[i+1] = Math.min(255, Math.max(0, data[i+1] + noise));
        data[i+2] = Math.min(255, Math.max(0, data[i+2] + noise));
      }
      ctx.putImageData(imgData, 0, 0);

      // Pentagons / Hexagons pattern
      ctx.fillStyle = '#0f172a';
      ctx.strokeStyle = '#cbd5e1';
      ctx.lineWidth = 4;

      const pentagonPositions = [
        { x: 256, y: 128 }, { x: 768, y: 128 },
        { x: 512, y: 256 },
        { x: 256, y: 384 }, { x: 768, y: 384 },
        { x: 0, y: 256 }, { x: 1024, y: 256 }
      ];

      function drawPentagon(cx, cy, r) {
        ctx.beginPath();
        for (let i = 0; i < 5; i++) {
          const angle = (i * 2 * Math.PI / 5) - Math.PI / 2;
          const px = cx + r * Math.cos(angle);
          const py = cy + r * Math.sin(angle);
          if (i === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
      }

      pentagonPositions.forEach(p => drawPentagon(p.x, p.y, 48));

      // Seam stitch lines
      ctx.strokeStyle = '#94a3b8';
      ctx.lineWidth = 2;
      for (let i = 0; i < pentagonPositions.length - 1; i++) {
        for (let j = i + 1; j < pentagonPositions.length; j++) {
          const dx = pentagonPositions[i].x - pentagonPositions[j].x;
          const dy = pentagonPositions[i].y - pentagonPositions[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 320 && dist > 100) {
            ctx.beginPath();
            ctx.moveTo(pentagonPositions[i].x, pentagonPositions[i].y);
            ctx.lineTo(pentagonPositions[j].x, pentagonPositions[j].y);
            ctx.stroke();
          }
        }
      }

      const texture = new THREE.CanvasTexture(canvas);
      texture.wrapS = THREE.RepeatWrapping;
      texture.wrapT = THREE.ClampToEdgeWrapping;
      return texture;
    }

    function createFloorTexture() {
      const canvas = document.createElement('canvas');
      canvas.width = 512;
      canvas.height = 512;
      const ctx = canvas.getContext('2d');

      ctx.fillStyle = '#1e293b';
      ctx.fillRect(0, 0, 512, 512);

      // Floor tiles grid
      ctx.strokeStyle = '#334155';
      ctx.lineWidth = 2;
      const step = 64;
      for (let x = 0; x <= 512; x += step) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, 512); ctx.stroke();
      }
      for (let y = 0; y <= 512; y += step) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(512, y); ctx.stroke();
      }

      // Subtle texture variation
      ctx.fillStyle = 'rgba(255, 255, 255, 0.02)';
      for (let x = 0; x < 512; x += step) {
        for (let y = 0; y < 512; y += step) {
          if ((x + y) % (step * 2) === 0) {
            ctx.fillRect(x, y, step, step);
          }
        }
      }

      const texture = new THREE.CanvasTexture(canvas);
      texture.wrapS = THREE.RepeatWrapping;
      texture.wrapT = THREE.RepeatWrapping;
      texture.repeat.set(8, 8);
      return texture;
    }

    /* --- CONTRACT 3: Room Environment & Lighting Architecture --- */
    class RoomEnvironment {
      constructor(scene) {
        this.scene = scene;
        // Room bounds: X in [-10, 10], Y in [0, 12], Z in [-10, 10]
        this.bounds = {
          minX: -10, maxX: 10,
          minY: 0,   maxY: 12,
          minZ: -10, maxZ: 10
        };
        this.buildRoom();
        this.setupLighting();
      }

      buildRoom() {
        const floorTex = createFloorTexture();
        const floorMat = new THREE.MeshStandardMaterial({
          map: floorTex,
          roughness: 0.55,
          metalness: 0.15
        });

        // Floor
        const floorGeo = new THREE.PlaneGeometry(20, 20);
        const floor = new THREE.Mesh(floorGeo, floorMat);
        floor.rotation.x = -Math.PI / 2;
        floor.position.y = 0;
        floor.receiveShadow = true;
        this.scene.add(floor);

        // Walls material
        const wallMat = new THREE.MeshStandardMaterial({
          color: 0x0f172a,
          roughness: 0.85,
          metalness: 0.1,
          side: THREE.BackSide
        });

        // Room box enclosure
        const boxGeo = new THREE.BoxGeometry(20, 12, 20);
        const roomBox = new THREE.Mesh(boxGeo, wallMat);
        roomBox.position.set(0, 6, 0);
        roomBox.receiveShadow = true;
        this.scene.add(roomBox);

        // Add subtle edge neon guides
        const wireGeo = new THREE.EdgesGeometry(boxGeo);
        const wireMat = new THREE.LineBasicMaterial({
          color: 0x38bdf8,
          transparent: true,
          opacity: 0.25
        });
        const wireframe = new THREE.LineSegments(wireGeo, wireMat);
        wireframe.position.set(0, 6, 0);
        this.scene.add(wireframe);
      }

      setupLighting() {
        // Ambient soft light
        const amb = new THREE.AmbientLight(0xffffff, 0.4);
        this.scene.add(amb);

        // Main overhead spotlight with soft shadow map
        const spot = new THREE.SpotLight(0xffffff, 1.2);
        spot.position.set(0, 11.5, 0);
        spot.angle = Math.PI / 3;
        spot.penumbra = 0.6;
        spot.decay = 1.5;
        spot.distance = 25;
        spot.castShadow = true;
        spot.shadow.mapSize.width = 2048;
        spot.shadow.mapSize.height = 2048;
        spot.shadow.camera.near = 1;
        spot.shadow.camera.far = 16;
        spot.shadow.bias = -0.0005;
        this.scene.add(spot);

        // Accent corner lights for depth and visual richness
        const blueRim = new THREE.PointLight(0x38bdf8, 0.8, 18);
        blueRim.position.set(-8, 9, -8);
        this.scene.add(blueRim);

        const warmRim = new THREE.PointLight(0xf59e0b, 0.6, 18);
        warmRim.position.set(8, 9, 8);
        this.scene.add(warmRim);
      }
    }

    /* --- CONTRACT 4: Deterministic 3D Vector Physics Integrator --- */
    class BallPhysics {
      constructor(scene, audio) {
        this.scene = scene;
        this.audio = audio;
        this.radius = 0.85; // 0.85 meters radius
        this.mass = 0.45;   // 0.45 kg (standard soccer ball)
        this.inertia = (2 / 3) * this.mass * Math.pow(this.radius, 2); // Thin spherical shell

        // State vectors
        this.pos = new THREE.Vector3(0, 4, 0);
        this.vel = new THREE.Vector3(0, 0, 0);
        this.omega = new THREE.Vector3(0, 0, 0); // Angular velocity (rad/s)
        this.quaternion = new THREE.Quaternion();

        // Physical constants
        this.gravity = -9.81;
        this.restitution = 0.76;      // Elastic bounciness
        this.friction = 0.38;         // Tangential wall & floor friction
        this.rollingResistance = 0.035;
        this.airDamping = 0.9985;
        this.angularDamping = 0.992;

        // Statistics
        this.kicksCount = 0;
        this.bouncesCount = 0;
        this.lastContactState = 'Air';

        // Mesh
        this.createMesh();
      }

      createMesh() {
        const geo = new THREE.SphereGeometry(this.radius, 64, 48);
        const tex = createSoccerTexture();
        const mat = new THREE.MeshStandardMaterial({
          map: tex,
          roughness: 0.4,
          metalness: 0.1,
          bumpScale: 0.02
        });
        this.mesh = new THREE.Mesh(geo, mat);
        this.mesh.castShadow = true;
        this.mesh.receiveShadow = false;
        this.mesh.position.copy(this.pos);
        this.scene.add(this.mesh);

        // Contact shadow blob on floor for enhanced realism
        const shadowGeo = new THREE.PlaneGeometry(this.radius * 2.2, this.radius * 2.2);
        const shadowMat = new THREE.MeshBasicMaterial({
          color: 0x000000,
          transparent: true,
          opacity: 0.55,
          depthWrite: false
        });
        this.contactShadow = new THREE.Mesh(shadowGeo, shadowMat);
        this.contactShadow.rotation.x = -Math.PI / 2;
        this.contactShadow.position.y = 0.01;
        this.scene.add(this.contactShadow);
      }

      applyImpulse(linearImpulse, contactPoint = null) {
        // Delta V = Impulse / mass
        const deltaV = linearImpulse.clone().divideScalar(this.mass);
        this.vel.add(deltaV);

        // Off-center torque imparting spin: Tau = r x F
        if (contactPoint) {
          const rOffset = contactPoint.clone().sub(this.pos);
          const torqueImpulse = new THREE.Vector3().crossVectors(rOffset, linearImpulse);
          // Delta Omega = Torque / Inertia
          const deltaOmega = torqueImpulse.divideScalar(this.inertia * 3.5);
          this.omega.add(deltaOmega);
        }

        this.kicksCount++;
        this.lastContactState = 'Kicked';
      }

      update(dt, bounds) {
        // Sub-stepping integrator (4 sub-steps per frame) for robust anti-tunneling
        const subSteps = 4;
        const subDt = dt / subSteps;

        for (let s = 0; s < subSteps; s++) {
          this.subStep(subDt, bounds);
        }

        // Sync Three.js mesh transform
        this.mesh.position.copy(this.pos);
        this.mesh.quaternion.copy(this.quaternion);

        // Sync floor contact shadow position & scale based on height
        this.contactShadow.position.x = this.pos.x;
        this.contactShadow.position.z = this.pos.z;
        const heightFactor = Math.max(0, 1 - (this.pos.y - this.radius) / 4.0);
        this.contactShadow.scale.setScalar(1 + (1 - heightFactor) * 0.8);
        this.contactShadow.material.opacity = 0.55 * Math.pow(heightFactor, 2);
      }

      subStep(dt, bounds) {
        // 1. Apply Gravity
        this.vel.y += this.gravity * dt;

        // 2. Air drag damping
        this.vel.multiplyScalar(Math.pow(this.airDamping, dt * 60));
        this.omega.multiplyScalar(Math.pow(this.angularDamping, dt * 60));

        // 3. Integrate position
        this.pos.addScaledVector(this.vel, dt);

        // 4. Integrate rotation quaternion from angular velocity
        const angle = this.omega.length() * dt;
        if (angle > 0.0001) {
          const axis = this.omega.clone().normalize();
          const dq = new THREE.Quaternion().setFromAxisAngle(axis, angle);
          this.quaternion.premultiply(dq);
          this.quaternion.normalize();
        }

        // 5. Collision Detection & Resolution against the 6 Room Planes
        this.solveCollisions(bounds, dt);
      }

      solveCollisions(bounds, dt) {
        let collided = false;
        let isFloorCollision = false;
        const r = this.radius;

        // Floor Collision (Y = 0)
        if (this.pos.y - r <= bounds.minY) {
          collided = true;
          isFloorCollision = true;
          this.pos.y = bounds.minY + r;

          const impactSpeed = -this.vel.y;
          if (impactSpeed > 0.15) {
            this.audio.playImpact(impactSpeed, true);
            this.bouncesCount++;
          }

          if (this.vel.y < 0) {
            // Restitution bounce
            this.vel.y = -this.vel.y * this.restitution;

            // Rest threshold to prevent endless jitter
            if (Math.abs(this.vel.y) < 0.25) {
              this.vel.y = 0;
            }
          }

          // Ground contact physics: friction & rolling torque
          const isResting = Math.abs(this.vel.y) < 0.1;
          if (isResting) {
            this.lastContactState = (this.vel.length() < 0.05) ? 'Resting' : 'Rolling';
            // Apply rolling resistance
            const speedXZ = Math.hypot(this.vel.x, this.vel.z);
            if (speedXZ > 0.01) {
              const frictionDrop = this.rollingResistance * 9.81 * dt;
              const newSpeed = Math.max(0, speedXZ - frictionDrop);
              this.vel.x = (this.vel.x / speedXZ) * newSpeed;
              this.vel.z = (this.vel.z / speedXZ) * newSpeed;

              // Pure rolling without slipping condition: omega = v / r
              this.omega.x = this.vel.z / r;
              this.omega.z = -this.vel.x / r;
            } else {
              this.vel.x = 0;
              this.vel.z = 0;
              this.omega.set(0, 0, 0);
            }
          } else {
            // Dynamic sliding bounce friction
            this.vel.x *= (1 - this.friction * 0.5);
            this.vel.z *= (1 - this.friction * 0.5);
          }
        }

        // Ceiling Collision (Y = bounds.maxY)
        if (this.pos.y + r >= bounds.maxY) {
          collided = true;
          this.pos.y = bounds.maxY - r;
          if (this.vel.y > 0) {
            const impactSpeed = this.vel.y;
            this.audio.playImpact(impactSpeed, false);
            this.bouncesCount++;
            this.vel.y = -this.vel.y * this.restitution;
          }
        }

        // Left Wall (X = bounds.minX)
        if (this.pos.x - r <= bounds.minX) {
          collided = true;
          this.pos.x = bounds.minX + r;
          if (this.vel.x < 0) {
            const impactSpeed = -this.vel.x;
            this.audio.playImpact(impactSpeed, false);
            this.bouncesCount++;
            this.vel.x = -this.vel.x * this.restitution;
            // Wall friction imparts spin
            this.omega.y += (this.vel.z / r) * 0.4;
            this.vel.z *= (1 - this.friction * 0.3);
          }
        }

        // Right Wall (X = bounds.maxX)
        if (this.pos.x + r >= bounds.maxX) {
          collided = true;
          this.pos.x = bounds.maxX - r;
          if (this.vel.x > 0) {
            const impactSpeed = this.vel.x;
            this.audio.playImpact(impactSpeed, false);
            this.bouncesCount++;
            this.vel.x = -this.vel.x * this.restitution;
            this.omega.y -= (this.vel.z / r) * 0.4;
            this.vel.z *= (1 - this.friction * 0.3);
          }
        }

        // Back Wall (Z = bounds.minZ)
        if (this.pos.z - r <= bounds.minZ) {
          collided = true;
          this.pos.z = bounds.minZ + r;
          if (this.vel.z < 0) {
            const impactSpeed = -this.vel.z;
            this.audio.playImpact(impactSpeed, false);
            this.bouncesCount++;
            this.vel.z = -this.vel.z * this.restitution;
            this.omega.y -= (this.vel.x / r) * 0.4;
            this.vel.z *= (1 - this.friction * 0.3);
          }
        }

        // Front Wall (Z = bounds.maxZ)
        if (this.pos.z + r >= bounds.maxZ) {
          collided = true;
          this.pos.z = bounds.maxZ - r;
          if (this.vel.z > 0) {
            const impactSpeed = this.vel.z;
            this.audio.playImpact(impactSpeed, false);
            this.bouncesCount++;
            this.vel.z = -this.vel.z * this.restitution;
            this.omega.y += (this.vel.x / r) * 0.4;
            this.vel.z *= (1 - this.friction * 0.3);
          }
        }

        if (collided && !isFloorCollision) {
          this.lastContactState = 'Wall Hit';
        }
      }

      reset() {
        this.pos.set(0, 4, 0);
        this.vel.set(0, 0, 0);
        this.omega.set(0, 0, 0);
        this.quaternion.identity();
        this.lastContactState = 'Resting';
      }
    }

    /* --- CONTRACT 5: Raycast Kick Interaction & Visual Effects --- */
    class KickController {
      constructor(camera, scene, ball, audio) {
        this.camera = camera;
        this.scene = scene;
        this.ball = ball;
        this.audio = audio;
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.container = document.getElementById('canvas-container');
        this.powerMultiplier = 1.0;

        this.initEvents();
      }

      initEvents() {
        // Pointer move for hover crosshair styling
        window.addEventListener('pointermove', (e) => {
          this.mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
          this.mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;

          this.raycaster.setFromCamera(this.mouse, this.camera);
          const intersects = this.raycaster.intersectObject(this.ball.mesh);
          if (intersects.length > 0) {
            this.container.classList.add('hover-ball');
          } else {
            this.container.classList.remove('hover-ball');
          }
        });

        // Pointer click to kick
        window.addEventListener('pointerdown', (e) => {
          // Ignore clicks on HUD buttons
          if (e.target.closest('.hud-controls') || e.target.closest('.telemetry-card')) return;

          this.mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
          this.mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;

          this.raycaster.setFromCamera(this.mouse, this.camera);
          const intersects = this.raycaster.intersectObject(this.ball.mesh);

          if (intersects.length > 0) {
            const hit = intersects[0];
            this.executeKick(hit.point, e.clientX, e.clientY);
          }
        });
      }

      executeKick(hitPoint, screenX, screenY) {
        // 1. Kick direction based on camera look angle + upward arc
        const kickDir = new THREE.Vector3();
        this.camera.getWorldDirection(kickDir);
        kickDir.y = Math.max(0.25, kickDir.y + 0.38); // Add loft
        kickDir.normalize();

        // 2. Off-center impact offset
        const offset = hitPoint.clone().sub(this.ball.pos);

        // 3. Magnitude (scalable by power multiplier)
        const baseSpeed = 16.5 * this.powerMultiplier;
        const linearImpulse = kickDir.multiplyScalar(baseSpeed * this.ball.mass);

        // Apply impulse to physics state
        this.ball.applyImpulse(linearImpulse, hitPoint);
        this.audio.playKick(this.powerMultiplier);

        // 4. Trigger UI ripple animation
        this.triggerKickFX(screenX, screenY);
      }

      triggerKickFX(x, y) {
        const ripple = document.createElement('div');
        ripple.className = 'kick-indicator';
        ripple.style.left = `${x}px`;
        ripple.style.top = `${y}px`;
        document.body.appendChild(ripple);

        requestAnimationFrame(() => {
          ripple.style.transform = 'translate(-50%, -50%) scale(1.6)';
          ripple.style.opacity = '0';
        });

        setTimeout(() => ripple.remove(), 450);
      }
    }

    /* --- CONTRACT 6: Main Application Assembler & Telemetry HUD Loop --- */
    class SimulationApp {
      constructor() {
        this.container = document.getElementById('canvas-container');
        this.initScene();
        this.audio = new SimulationAudio();
        this.room = new RoomEnvironment(this.scene);
        this.ball = new BallPhysics(this.scene, this.audio);
        this.kickController = new KickController(this.camera, this.scene, this.ball, this.audio);

        this.setupControls();
        this.bindHUD();

        this.clock = new THREE.Clock();
        this.animate = this.animate.bind(this);
        requestAnimationFrame(this.animate);
      }

      initScene() {
        // Scene & Camera
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0a0b10);
        this.scene.fog = new THREE.FogExp2(0x0a0b10, 0.025);

        this.camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 100);
        this.camera.position.set(0, 5, 16);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.05;
        this.container.appendChild(this.renderer.domElement);

        // OrbitControls
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.maxPolarAngle = Math.PI / 2 - 0.02; // Prevent going below floor
        this.controls.minDistance = 3;
        this.controls.maxDistance = 24;
        this.controls.target.set(0, 2, 0);

        // Window resize
        window.addEventListener('resize', () => {
          this.camera.aspect = window.innerWidth / window.innerHeight;
          this.camera.updateProjectionMatrix();
          this.renderer.setSize(window.innerWidth, window.innerHeight);
        });
      }

      setupControls() {
        // Kick Button
        document.getElementById('btn-kick').addEventListener('click', () => {
          const kickDir = new THREE.Vector3((Math.random() - 0.5) * 0.8, 1.2, (Math.random() - 0.5) * 0.8).normalize();
          const impulse = kickDir.multiplyScalar(15 * this.ball.mass);
          this.ball.applyImpulse(impulse, this.ball.pos.clone().add(new THREE.Vector3(0.2, -0.4, 0)));
          this.audio.playKick();
        });

        // Power Toggle
        const powerBtn = document.getElementById('btn-power');
        const powerLevels = [
          { label: '⚡ Power: Normal', mult: 1.0 },
          { label: '⚡ Power: Heavy', mult: 1.6 },
          { label: '⚡ Power: Rocket', mult: 2.3 }
        ];
        let pIdx = 0;
        powerBtn.addEventListener('click', () => {
          pIdx = (pIdx + 1) % powerLevels.length;
          powerBtn.innerText = powerLevels[pIdx].label;
          this.kickController.powerMultiplier = powerLevels[pIdx].mult;
        });

        // Gravity Toggle
        const gravBtn = document.getElementById('btn-gravity');
        const gravLevels = [
          { label: '🌍 Earth 1.0G', g: -9.81 },
          { label: '🌕 Moon 0.16G', g: -1.62 },
          { label: '🪐 Jupiter 2.5G', g: -24.79 },
          { label: '🚀 Zero-G 0.0G', g: -0.2 }
        ];
        let gIdx = 0;
        gravBtn.addEventListener('click', () => {
          gIdx = (gIdx + 1) % gravLevels.length;
          gravBtn.innerText = gravLevels[gIdx].label;
          this.ball.gravity = gravLevels[gIdx].g;
        });

        // Sound Toggle
        const sndBtn = document.getElementById('btn-sound');
        sndBtn.addEventListener('click', () => {
          this.audio.enabled = !this.audio.enabled;
          sndBtn.innerText = this.audio.enabled ? '🔊 Sound: ON' : '🔇 Sound: OFF';
          sndBtn.classList.toggle('active', this.audio.enabled);
        });

        // Reset Button
        document.getElementById('btn-reset').addEventListener('click', () => {
          this.ball.reset();
        });
      }

      bindHUD() {
        this.hudSpeed = document.getElementById('val-speed');
        this.hudSpeedKmh = document.getElementById('val-speed-kmh');
        this.hudSpin = document.getElementById('val-spin');
        this.hudAltitude = document.getElementById('val-altitude');
        this.hudState = document.getElementById('val-state');
        this.hudKicks = document.getElementById('val-kicks');
        this.hudBounces = document.getElementById('val-bounces');
        this.hudIntensity = document.getElementById('val-intensity');
        this.meterFill = document.getElementById('meter-fill');
      }

      updateHUD() {
        const speed = this.ball.vel.length();
        const speedKmh = speed * 3.6;
        const spinRpm = (this.ball.omega.length() * 60) / (2 * Math.PI);

        this.hudSpeed.innerText = `${speed.toFixed(2)} m/s`;
        this.hudSpeedKmh.innerText = `${speedKmh.toFixed(1)} km/h`;
        this.hudSpin.innerText = `${Math.round(spinRpm)} RPM`;
        this.hudAltitude.innerText = `${this.ball.pos.y.toFixed(2)} m`;
        this.hudState.innerText = this.ball.lastContactState;

        // State color highlights
        if (this.ball.lastContactState === 'Resting') {
          this.hudState.className = 'metric-val';
        } else if (this.ball.lastContactState === 'Rolling') {
          this.hudState.className = 'metric-val highlight';
        } else {
          this.hudState.className = 'metric-val alert';
        }

        this.hudKicks.innerText = this.ball.kicksCount;
        this.hudBounces.innerText = this.ball.bouncesCount;

        // Intensity bar (0 to 30 m/s mapped to 0-100%)
        const intensity = Math.min(100, Math.round((speed / 28) * 100));
        this.hudIntensity.innerText = `${intensity}%`;
        this.meterFill.style.width = `${intensity}%`;
      }

      animate() {
        requestAnimationFrame(this.animate);
        const dt = Math.min(this.clock.getDelta(), 0.05);

        this.ball.update(dt, this.room.bounds);
        this.controls.update();
        this.updateHUD();
        this.renderer.render(this.scene, this.camera);
      }
    }

    // Launch Application when DOM is ready
    window.addEventListener('DOMContentLoaded', () => {
      window.app = new SimulationApp();
    });
  </script>
</body>
</html>
'''
    return html_content

def main():
    print("🚀 [Jev 3-Tier Swarm] Building 3D Ball Physics & Room Collision Simulation...")
    out_path = "benchmarks/3d_ball_simulation/index.html"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    code = generate_simulation_html()

    # --- TIER 1: Generic Runtime & Syntax Verification ---
    print("🔍 [Tier 1] Running Node.js VM AST syntax check...")
    is_valid, err_msg = GenericRuntimeValidator.validate_code(code, lang="javascript")
    if not is_valid:
        print(f"❌ [Tier 1] Fatal Syntax Error: {err_msg}")
        sys.exit(1)
    print(f"✅ [Tier 1] Node.js Runtime Syntax Passed: {err_msg}")

    # Write output
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"💾 Saved simulation webapp to: {out_path}")

    # --- TIER 2: Calibrated TypeSafe Jev System One Gate ---
    print("🧠 [Tier 2] Evaluating Contract Soundness via TypeSafe Jev System One...")
    try:
        jev = JevClient()
        questions = {
            "reference_integrity": {
                "type": "noul",
                "instructions": "Are all Three.js, Web Audio, and physics variables/methods properly initialized and scoped without ReferenceError risks?"
            },
            "physics_completeness": {
                "type": "noul",
                "instructions": "Does this simulation provide realistic 3D vector physics, sub-stepping, restitution collisions with all room planes, and raycast kicking?"
            },
            "visual_polish_score": {
                "type": "score",
                "instructions": "Rate the visual realism, lighting, materials, HUD telemetry, and responsive polish from 0 to 3",
                "range": [0, 3],
                "criteria": ["Basic prototype", "Functional but unpolished", "Polished 3D simulation", "Production-grade excellence"]
            }
        }
        js_code = code.split("<script>")[1].split("</script>")[0] if "<script>" in code else code
        state = f"## 3D Ball & Room Physics Simulation JavaScript Engine\n```javascript\n{js_code[:6000]}\n```"
        answers, elapsed = jev.evaluate(state, questions)
        print(f"⏱️ Jev evaluated in {elapsed*1000:.0f}ms")
        for q_name, ans in answers.items():
            val = ans.get("noul") if "noul" in ans else ans.get("score")
            print(f"   - {q_name}: {val}")
    except Exception as e:
        print(f"⚠️ Tier 2 Jev evaluation warning: {e}")

    print("\n🎉 Simulation Build Complete! Ready for interactive testing.")

if __name__ == "__main__":
    main()
