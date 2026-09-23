import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';

import { createTrack } from '../src/track.js';
import { createVehicle, stepVehicle } from '../src/vehicle.js';
import { createRace } from '../src/race.js';

test('car physics stays finite and respects the road boundary', () => {
  const scene = new THREE.Scene();
  const track = createTrack(scene);
  const car = createVehicle(scene, { id: 'TEST', color: 0x20b8f2, ...track.start });
  for (let i = 0; i < 300; i += 1) {
    stepVehicle(car, { throttle: 1, brake: 0, steer: i > 80 ? 0.35 : 0 }, 0.05, track);
    assert.ok(Number.isFinite(car.x) && Number.isFinite(car.z) && Number.isFinite(car.yaw));
    assert.ok(track.nearest(car.x, car.z).distance <= track.halfWidth + 0.53);
  }
  assert.ok(Math.hypot(car.x - track.start.x, car.z - track.start.z) > 1);
});

test('AI can complete a valid three-lap race', () => {
  const scene = new THREE.Scene();
  const track = createTrack(scene);
  const entrants = [0, 1, 2, 3].map((index) => ({
    id: `AI${index}`,
    kind: 'ai',
    car: createVehicle(scene, { id: `AI${index}`, color: 0x55bbdd + index, ...track.start }),
  }));
  const race = createRace(scene, track, entrants);
  race.begin();
  for (let i = 0; i < 4800 && race.state.mode === 'running'; i += 1) race.update(0.05);
  assert.equal(race.state.mode, 'finished');
  assert.ok(entrants.some((entry) => entry.id === race.state.winner));
  assert.ok(race.state.standings.some((entry) => entry.completedLaps >= 3));
  race.dispose();
});
