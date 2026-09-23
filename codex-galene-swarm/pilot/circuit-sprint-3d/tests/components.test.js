import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';

import { makeTrackSamples, nearestTrackPoint } from '../src/track-math.js';
import { createCarMesh } from '../src/car-mesh.js';
import { createControls } from '../src/controls.js';

test('track samples make a closed, queryable circuit', () => {
  const samples = makeTrackSamples();
  assert.equal(samples.length, 240);
  for (const point of samples) {
    assert.ok(Number.isFinite(point.x) && Number.isFinite(point.z));
    const nearest = nearestTrackPoint(samples, point.x, point.z);
    assert.ok(nearest.distance < 0.001);
    assert.ok(Math.abs(Math.hypot(nearest.tangentX, nearest.tangentZ) - 1) < 0.001);
    assert.ok(nearest.progress >= 0 && nearest.progress < 1);
  }
  const center = nearestTrackPoint(samples, 0, 0);
  assert.ok(Number.isFinite(center.distance));
});

test('car mesh has procedural geometry and a clear front', () => {
  const car = createCarMesh(0x20b8f2);
  assert.ok(car instanceof THREE.Group);
  assert.ok(car.children.length >= 8);
  assert.ok(car.children.some((part) => part.position.z > 1));
  assert.ok(car.children.every((part) => part.geometry instanceof THREE.BufferGeometry));
});

test('controls support both players, blur, and disposal', () => {
  const listeners = new Map();
  const target = {
    addEventListener(type, fn) { listeners.set(type, fn); },
    removeEventListener(type, fn) { if (listeners.get(type) === fn) listeners.delete(type); },
  };
  const controls = createControls(target);
  let prevented = false;
  listeners.get('keydown')({ code: 'ArrowUp', preventDefault() { prevented = true; } });
  listeners.get('keydown')({ code: 'KeyJ', preventDefault() {} });
  assert.equal(prevented, true);
  assert.deepEqual(controls.read(1), { throttle: 1, brake: 0, steer: 0 });
  assert.deepEqual(controls.read(2), { throttle: 0, brake: 0, steer: -1 });
  listeners.get('blur')();
  assert.deepEqual(controls.read(1), { throttle: 0, brake: 0, steer: 0 });
  controls.dispose();
  controls.dispose();
  assert.equal(listeners.size, 0);
});
