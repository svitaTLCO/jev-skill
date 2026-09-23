import * as THREE from 'three';
import { stepVehicle } from './vehicle.js';

const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
const turnDifference = (target, current) => Math.atan2(Math.sin(target - current), Math.cos(target - current));

export function createRace(scene, track, entrants, lapsToWin = 3) {
  const state = { mode: 'ready', elapsed: 0, winner: null, lapsToWin, standings: [] };
  const records = new Map();
  const props = new THREE.Group();
  scene.add(props);

  const oilMaterial = new THREE.MeshBasicMaterial({ color: 0x17212a, transparent: true, opacity: 0.8, side: THREE.DoubleSide });
  const oilRim = new THREE.MeshBasicMaterial({ color: 0x546c72, transparent: true, opacity: 0.75, side: THREE.DoubleSide });
  const oils = [0.32, 0.68].map((fraction, index) => {
    const point = track.samples[Math.floor(fraction * track.samples.length)];
    const group = new THREE.Group();
    const ring = new THREE.Mesh(new THREE.RingGeometry(1.05, 1.27, 24), oilRim);
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = 0.09;
    group.add(ring);
    const slick = new THREE.Mesh(new THREE.CircleGeometry(1.08, 24), oilMaterial);
    slick.rotation.x = -Math.PI / 2;
    slick.position.y = 0.095;
    group.add(slick);
    group.position.set(point.x, 0, point.z);
    props.add(group);
    return { id: index, x: point.x, z: point.z, radius: 1.36, group };
  });

  const gold = new THREE.MeshStandardMaterial({ color: 0xffcf68, metalness: 0.45, roughness: 0.27 });
  const pickups = [0.18, 0.52, 0.84].map((fraction) => {
    const point = track.samples[Math.floor(fraction * track.samples.length)];
    const group = new THREE.Group();
    const handle = new THREE.Mesh(new THREE.BoxGeometry(0.17, 0.14, 0.9), gold);
    group.add(handle);
    for (const side of [-1, 1]) {
      const prong = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.14, 0.34), gold);
      prong.position.set(side * 0.2, 0, 0.54);
      group.add(prong);
    }
    const hub = new THREE.Mesh(new THREE.TorusGeometry(0.19, 0.07, 6, 12), gold);
    hub.rotation.x = Math.PI / 2;
    hub.position.z = -0.48;
    group.add(hub);
    group.position.set(point.x, 0.78, point.z);
    props.add(group);
    return { x: point.x, z: point.z, group, available: true, respawn: 0 };
  });

  function updateStandings() {
    state.standings = entrants.map(({ id, car }) => {
      const record = records.get(id);
      return {
        id,
        color: car.color,
        lap: Math.min(lapsToWin, record.laps + 1),
        completedLaps: record.laps,
        progress: record.lastProgress,
        wrenches: record.wrenches,
        place: 0,
      };
    });
    state.standings.sort((a, b) =>
      b.completedLaps - a.completedLaps || b.progress - a.progress,
    );
    state.standings.forEach((entry, index) => { entry.place = index + 1; });
  }

  function reset() {
    state.mode = 'ready';
    state.elapsed = 0;
    state.winner = null;
    records.clear();
    entrants.forEach(({ id, car }, index) => {
      const sampleIndex = (track.samples.length - 8 - index * 5 + track.samples.length) % track.samples.length;
      const point = track.samples[sampleIndex];
      const nearby = track.nearest(point.x, point.z);
      const lane = (index % 2 ? 1 : -1) * 1.12;
      car.x = point.x + nearby.tangentZ * lane;
      car.z = point.z - nearby.tangentX * lane;
      car.yaw = Math.atan2(nearby.tangentX, nearby.tangentZ);
      car.speed = 0;
      car.spinTimer = 0;
      car.oilCooldown = 0;
      car.upgrade = 0;
      car.group.position.set(car.x, 0.04, car.z);
      car.group.rotation.y = car.yaw;
      const progress = track.nearest(car.x, car.z).progress;
      records.set(id, { laps: 0, nextQuarter: 1, lastProgress: progress, wrenches: 0 });
    });
    pickups.forEach((pickup) => {
      pickup.available = true;
      pickup.respawn = 0;
      pickup.group.visible = true;
    });
    updateStandings();
  }

  function begin() {
    if (state.mode === 'ready') state.mode = 'running';
  }

  function aiInput(car) {
    const near = track.nearest(car.x, car.z);
    const lookAhead = 7 + Math.round(Math.abs(car.speed) * 0.16);
    const point = track.samples[(near.index + lookAhead) % track.samples.length];
    const desiredYaw = Math.atan2(point.x - car.x, point.z - car.z);
    const error = turnDifference(desiredYaw, car.yaw);
    const steer = clamp(error * 1.75, -1, 1);
    const slowing = Math.abs(error) > 0.62 && car.speed > 11;
    return { throttle: slowing ? 0.35 : 0.91, brake: slowing ? 0.42 : 0, steer };
  }

  function update(dt, inputById = {}) {
    if (state.mode !== 'running') return;
    const step = clamp(dt, 0, 0.05);
    state.elapsed += step;
    pickups.forEach((pickup, index) => {
      if (!pickup.available) {
        pickup.respawn -= step;
        if (pickup.respawn <= 0) {
          pickup.available = true;
          pickup.group.visible = true;
        }
      } else {
        pickup.group.rotation.y += step * 2.2;
        pickup.group.position.y = 0.78 + Math.sin(state.elapsed * 3 + index) * 0.13;
      }
    });

    for (const entrant of entrants) {
      const { id, kind, car } = entrant;
      const input = kind === 'human' ? inputById[id] || { throttle: 0, brake: 0, steer: 0 } : aiInput(car);
      stepVehicle(car, input, step, track);
      const record = records.get(id);
      const progress = track.nearest(car.x, car.z).progress;
      if (record.nextQuarter <= 3 && progress >= record.nextQuarter / 4 && progress < record.nextQuarter / 4 + 0.2) {
        record.nextQuarter += 1;
      }
      if (record.lastProgress > 0.87 && progress < 0.13) {
        if (record.nextQuarter === 4) {
          record.laps += 1;
          record.nextQuarter = 1;
          if (record.laps >= lapsToWin && state.winner === null) {
            state.winner = id;
            state.mode = 'finished';
          }
        }
      }
      record.lastProgress = progress;

      for (const oil of oils) {
        if (car.oilCooldown > 0) break;
        if (Math.hypot(car.x - oil.x, car.z - oil.z) < oil.radius) {
          car.spinTimer = 0.62;
          car.spinDirection = oil.id % 2 ? 1 : -1;
          car.oilCooldown = 2.7;
        }
      }
      for (const pickup of pickups) {
        if (!pickup.available) continue;
        if (Math.hypot(car.x - pickup.x, car.z - pickup.z) < 1.24) {
          pickup.available = false;
          pickup.respawn = 12;
          pickup.group.visible = false;
          car.upgrade = Math.min(3, car.upgrade + 1);
          record.wrenches += 1;
        }
      }
    }
    updateStandings();
  }

  function dispose() {
    scene.remove(props);
    props.traverse((part) => {
      if (!part.isMesh) return;
      part.geometry.dispose();
      if (part.material !== gold && part.material !== oilMaterial && part.material !== oilRim) part.material.dispose();
    });
    gold.dispose();
    oilMaterial.dispose();
    oilRim.dispose();
  }

  reset();
  return { state, begin, update, reset, dispose };
}
