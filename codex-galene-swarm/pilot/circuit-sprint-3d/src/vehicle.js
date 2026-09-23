import { createCarMesh } from './car-mesh.js';

const clamp = (value, low, high) => Math.max(low, Math.min(high, value));

export function createVehicle(scene, { id, color, x, z, yaw }) {
  const group = createCarMesh(color);
  group.position.set(x, 0.04, z);
  group.rotation.y = yaw;
  group.traverse((part) => {
    if (part.isMesh) part.castShadow = true;
  });
  scene.add(group);
  return { id, color, group, x, z, yaw, speed: 0, spinTimer: 0, spinDirection: 1, oilCooldown: 0, upgrade: 0 };
}

export function stepVehicle(car, input, dt, track) {
  const step = clamp(dt, 0, 0.05);
  const road = track.nearest(car.x, car.z);
  const offRoad = road.distance > track.halfWidth - 0.3;
  const throttle = clamp(input.throttle || 0, 0, 1);
  const brake = clamp(input.brake || 0, 0, 1);
  let steer = clamp(input.steer || 0, -1, 1);

  car.oilCooldown = Math.max(0, car.oilCooldown - step);
  if (car.spinTimer > 0) {
    car.spinTimer = Math.max(0, car.spinTimer - step);
    car.yaw += car.spinDirection * step * 6.3;
    steer *= 0.15;
  }

  const acceleration = (offRoad ? 7.5 : 13.5) + car.upgrade * 1.1;
  const maxSpeed = (offRoad ? 9.5 : 18.5) + car.upgrade * 0.8;
  car.speed += (throttle * acceleration - brake * 19.5) * step;
  car.speed -= car.speed * (throttle || brake ? 0.35 : 1.65) * step;
  car.speed = clamp(car.speed, -5, maxSpeed);

  const steerFactor = 0.42 + car.upgrade * 0.025;
  car.yaw += steer * steerFactor * car.speed * step * 0.48;
  car.x += Math.sin(car.yaw) * car.speed * step;
  car.z += Math.cos(car.yaw) * car.speed * step;

  const next = track.nearest(car.x, car.z);
  const wall = track.halfWidth + 0.52;
  if (next.distance > wall) {
    const dx = car.x - next.x;
    const dz = car.z - next.z;
    const scale = wall / next.distance;
    car.x = next.x + dx * scale;
    car.z = next.z + dz * scale;
    car.speed *= -0.28;
  }

  car.group.position.set(car.x, 0.04, car.z);
  car.group.rotation.y = car.yaw;
}
