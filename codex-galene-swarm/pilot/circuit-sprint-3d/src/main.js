import * as THREE from 'three';
import './style.css';
import { createTrack } from './track.js';
import { createVehicle } from './vehicle.js';
import { createRace } from './race.js';
import { createControls } from './controls.js';

const app = document.querySelector('#app');
app.innerHTML = `
  <div class="game-shell">
    <div class="viewport" id="viewport" aria-label="3D racing circuit"></div>
    <div class="vignette" aria-hidden="true"></div>
    <header class="topbar">
      <div class="brand"><span class="brand-mark">CS<span>3</span></span><div><strong>CIRCUIT SPRINT</strong><small>THREE DIMENSIONS. ONE FINISH LINE.</small></div></div>
      <div class="race-meta"><span class="eyebrow">ARCADE GRAND PRIX</span><strong id="timer">00:00.0</strong></div>
      <button class="top-button" id="pause-button" type="button" disabled>PAUSE</button>
    </header>
    <aside class="score-panel" aria-live="polite">
      <div class="panel-title"><span>LIVE STANDINGS</span><span id="lap-counter">3 LAPS</span></div>
      <div id="standings"></div>
      <div class="panel-footer"><span class="signal"></span><span id="race-status">READY TO RACE</span></div>
    </aside>
    <div class="track-label">DUST VALLEY <span>·</span> CIRCUIT 01</div>
    <section class="overlay intro" id="intro">
      <div class="intro-card">
        <p class="kicker">THE LIGHTS ARE YOURS</p>
        <h1>CIRCUIT<br><em>SPRINT</em><b>3D</b></h1>
        <p class="intro-copy">An overhead racing classic reimagined as a miniature 3D grand prix. Chase the line, dodge slicks, and collect upgrades across three laps.</p>
        <div class="mode-buttons">
          <button class="primary-button" data-players="1" type="button">SOLO RACE <span>→</span></button>
          <button class="secondary-button" data-players="2" type="button">TWO PLAYER <span>→</span></button>
        </div>
        <div class="control-guide"><span><b>P1</b> WASD / ARROWS</span><span><b>P2</b> I J K L</span><span><b>ESC</b> PAUSE</span></div>
      </div>
    </section>
    <section class="overlay result" id="result" hidden>
      <div class="result-card">
        <p class="kicker">RACE COMPLETE</p>
        <h2 id="result-title">CHECKERED FLAG</h2>
        <p id="result-copy"></p>
        <div class="mode-buttons"><button class="primary-button" id="race-again" type="button">RACE AGAIN <span>→</span></button><button class="secondary-button" id="change-mode" type="button">CHANGE MODE</button></div>
      </div>
    </section>
    <footer class="footer"><span>WRENCHES BOOST YOUR CAR</span><span>OIL SLICKS WILL SPIN YOU OUT</span><span>ORIGINAL PROCEDURAL 3D</span></footer>
  </div>
`;

const viewport = document.querySelector('#viewport');
const timer = document.querySelector('#timer');
const standings = document.querySelector('#standings');
const status = document.querySelector('#race-status');
const intro = document.querySelector('#intro');
const result = document.querySelector('#result');
const pauseButton = document.querySelector('#pause-button');
const lapCounter = document.querySelector('#lap-counter');

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x8cae8d);
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.45;
viewport.append(renderer.domElement);

const camera = new THREE.OrthographicCamera(-30, 30, 20, -20, 0.1, 200);
camera.position.set(0, 45, 28);
camera.lookAt(0, 0, 0);
scene.add(new THREE.HemisphereLight(0xe7f7ff, 0x566e57, 2.2));
const sun = new THREE.DirectionalLight(0xffedcd, 2.7);
sun.position.set(-18, 32, 18);
sun.castShadow = true;
sun.shadow.mapSize.set(1024, 1024);
sun.shadow.camera.left = -45;
sun.shadow.camera.right = 45;
sun.shadow.camera.top = 45;
sun.shadow.camera.bottom = -45;
sun.shadow.normalBias = 0.02;
scene.add(sun);

const track = createTrack(scene);
const controls = createControls();
const palette = [0x28c7e7, 0xfb6f64, 0xf9c85c, 0xa793ea];
const names = ['YOU', 'P2', 'COMET', 'VECTOR'];
let race = null;
let entrants = [];
let players = 1;
let resultShown = false;
let lastFrame = performance.now();
let hudTimer = 0;

function formatTime(seconds) {
  const minutes = Math.floor(seconds / 60).toString().padStart(2, '0');
  const rest = (seconds % 60).toFixed(1).padStart(4, '0');
  return `${minutes}:${rest}`;
}

function resize() {
  const width = Math.max(1, viewport.clientWidth);
  const height = Math.max(1, viewport.clientHeight);
  const aspect = width / height;
  const halfHeight = Math.max(18.5, 25 / aspect);
  camera.left = -halfHeight * aspect;
  camera.right = halfHeight * aspect;
  camera.top = halfHeight;
  camera.bottom = -halfHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);
}
window.addEventListener('resize', resize);
resize();

function buildRace(playerCount) {
  if (race) race.dispose();
  entrants.forEach(({ car }) => {
    scene.remove(car.group);
    car.group.traverse((part) => {
      if (!part.isMesh) return;
      part.geometry.dispose();
      part.material.dispose();
    });
  });
  players = playerCount;
  entrants = palette.map((color, index) => {
    const id = index === 1 && players === 1 ? 'RIVAL' : names[index];
    const car = createVehicle(scene, { id, color, x: track.start.x, z: track.start.z, yaw: track.start.yaw });
    return { id, kind: index < players ? 'human' : 'ai', car };
  });
  race = createRace(scene, track, entrants, 3);
  resultShown = false;
  updateHud();
}

function startGame(playerCount = players) {
  buildRace(playerCount);
  race.begin();
  intro.hidden = true;
  result.hidden = true;
  pauseButton.disabled = false;
  pauseButton.textContent = 'PAUSE';
  status.textContent = 'RACE IN PROGRESS';
}

function showResult() {
  if (resultShown) return;
  resultShown = true;
  const winner = race.state.winner;
  const humanWon = entrants.some(({ id, kind }) => id === winner && kind === 'human');
  document.querySelector('#result-title').textContent = humanWon ? 'VICTORY LAP' : 'CHECKERED FLAG';
  document.querySelector('#result-copy').textContent = `${winner} crossed the line first in ${formatTime(race.state.elapsed)}. ${humanWon ? 'The trophy is yours.' : 'The grid is ready for a rematch.'}`;
  result.hidden = false;
  pauseButton.disabled = true;
  status.textContent = `${winner} WINS`;
}

function updateHud() {
  if (!race) return;
  timer.textContent = formatTime(race.state.elapsed);
  const firstHuman = race.state.standings.find((entry) => entry.id === 'YOU');
  lapCounter.textContent = firstHuman ? `LAP ${firstHuman.lap} / ${race.state.lapsToWin}` : '3 LAPS';
  standings.innerHTML = race.state.standings.map((entry) => `
    <div class="standing ${entry.id === 'YOU' || (players === 2 && entry.id === 'P2') ? 'player' : ''}">
      <span class="place">${String(entry.place).padStart(2, '0')}</span>
      <span class="swatch" style="background:#${entry.color.toString(16).padStart(6, '0')}"></span>
      <span class="driver">${entry.id}</span>
      <span class="standing-lap">${entry.lap}/${race.state.lapsToWin}</span>
      <span class="standing-wrench" title="Collected upgrades">◆ ${entry.wrenches}</span>
    </div>
  `).join('');
}

function frame(now) {
  const dt = Math.min((now - lastFrame) / 1000, 0.05);
  lastFrame = now;
  if (race?.state.mode === 'running') {
    race.update(dt, { YOU: controls.read(1), P2: controls.read(2) });
    hudTimer += dt;
    if (hudTimer > 0.09 || race.state.mode === 'finished') {
      updateHud();
      hudTimer = 0;
    }
    if (race.state.mode === 'finished') showResult();
  }
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

intro.querySelectorAll('[data-players]').forEach((button) => {
  button.addEventListener('click', () => startGame(Number(button.dataset.players)));
});
document.querySelector('#race-again').addEventListener('click', () => startGame(players));
document.querySelector('#change-mode').addEventListener('click', () => {
  result.hidden = true;
  intro.hidden = false;
  status.textContent = 'READY TO RACE';
});
pauseButton.addEventListener('click', () => {
  if (!race || race.state.mode === 'finished') return;
  race.state.mode = race.state.mode === 'running' ? 'paused' : 'running';
  pauseButton.textContent = race.state.mode === 'paused' ? 'RESUME' : 'PAUSE';
  status.textContent = race.state.mode === 'paused' ? 'RACE PAUSED' : 'RACE IN PROGRESS';
});
window.addEventListener('keydown', (event) => {
  if (event.code === 'Escape' && !pauseButton.disabled) pauseButton.click();
});

buildRace(1);
