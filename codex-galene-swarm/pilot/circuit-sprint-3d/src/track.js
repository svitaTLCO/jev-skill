import * as THREE from 'three';
import { makeTrackSamples, nearestTrackPoint } from './track-math.js';

const asphalt = new THREE.MeshStandardMaterial({ color: 0x292c35, roughness: 0.92, side: THREE.DoubleSide });
const paleCurb = new THREE.MeshStandardMaterial({ color: 0xf2e7d5, roughness: 0.8 });
const coralCurb = new THREE.MeshStandardMaterial({ color: 0xf56f60, roughness: 0.8 });
const lineMaterial = new THREE.MeshBasicMaterial({ color: 0xf7e7bd });

export function createTrack(scene) {
  const samples = makeTrackSamples(240);
  const halfWidth = 3.05;
  const nearest = (x, z) => nearestTrackPoint(samples, x, z);
  const onRoad = (x, z) => nearest(x, z).distance <= halfWidth;
  const first = nearest(samples[0].x, samples[0].z);
  const start = { x: first.x, z: first.z, yaw: Math.atan2(first.tangentX, first.tangentZ) };

  const grass = new THREE.Mesh(
    new THREE.PlaneGeometry(110, 90),
    new THREE.MeshStandardMaterial({ color: 0x789c6e, roughness: 1, side: THREE.DoubleSide }),
  );
  grass.rotation.x = -Math.PI / 2;
  grass.position.y = -0.1;
  grass.receiveShadow = true;
  scene.add(grass);

  const ribbon = [];
  const triangles = [];
  for (let i = 0; i <= samples.length; i += 1) {
    const p = samples[i % samples.length];
    const q = nearest(p.x, p.z);
    const nx = q.tangentZ;
    const nz = -q.tangentX;
    ribbon.push(p.x - nx * halfWidth, 0.025, p.z - nz * halfWidth);
    ribbon.push(p.x + nx * halfWidth, 0.025, p.z + nz * halfWidth);
    if (i < samples.length) {
      const a = 2 * i;
      triangles.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
    }
  }
  const roadGeometry = new THREE.BufferGeometry();
  roadGeometry.setAttribute('position', new THREE.Float32BufferAttribute(ribbon, 3));
  roadGeometry.setIndex(triangles);
  roadGeometry.computeVertexNormals();
  const road = new THREE.Mesh(roadGeometry, asphalt);
  road.receiveShadow = true;
  scene.add(road);

  const curbGeometry = new THREE.BoxGeometry(0.36, 0.15, 1);
  const edgeGeometry = new THREE.BoxGeometry(0.08, 0.025, 1);
  for (let i = 0; i < samples.length; i += 4) {
    const a = samples[i];
    const b = samples[(i + 4) % samples.length];
    const segment = Math.hypot(b.x - a.x, b.z - a.z);
    const mid = nearest((a.x + b.x) / 2, (a.z + b.z) / 2);
    const angle = Math.atan2(mid.tangentX, mid.tangentZ);
    for (const side of [-1, 1]) {
      const nx = mid.tangentZ * side;
      const nz = -mid.tangentX * side;
      const curb = new THREE.Mesh(curbGeometry, (i / 4) % 2 ? coralCurb : paleCurb);
      curb.position.set(mid.x + nx * (halfWidth + 0.12), 0.10, mid.z + nz * (halfWidth + 0.12));
      curb.rotation.y = angle;
      curb.scale.z = segment + 0.15;
      curb.castShadow = true;
      scene.add(curb);

      if (i % 8 === 0) {
        const edge = new THREE.Mesh(edgeGeometry, lineMaterial);
        edge.position.set(mid.x + nx * (halfWidth - 0.43), 0.055, mid.z + nz * (halfWidth - 0.43));
        edge.rotation.y = angle;
        edge.scale.z = segment + 0.1;
        scene.add(edge);
      }
    }
  }

  for (let i = 6; i < samples.length; i += 11) {
    const p = samples[i];
    const q = nearest(p.x, p.z);
    const dash = new THREE.Mesh(new THREE.BoxGeometry(0.075, 0.018, 0.65), lineMaterial);
    dash.position.set(p.x, 0.056, p.z);
    dash.rotation.y = Math.atan2(q.tangentX, q.tangentZ);
    scene.add(dash);
  }

  const startGroup = new THREE.Group();
  startGroup.position.set(start.x, 0.06, start.z);
  startGroup.rotation.y = start.yaw;
  const tileWidth = (halfWidth * 2) / 10;
  for (let row = 0; row < 2; row += 1) {
    for (let column = 0; column < 10; column += 1) {
      const tile = new THREE.Mesh(
        new THREE.BoxGeometry(tileWidth, 0.017, 0.37),
        new THREE.MeshBasicMaterial({ color: (row + column) % 2 ? 0x17232a : 0xfff6dc }),
      );
      tile.position.set(-halfWidth + tileWidth * (column + 0.5), 0, (row - 0.5) * 0.37);
      startGroup.add(tile);
    }
  }
  scene.add(startGroup);

  const trunkGeometry = new THREE.CylinderGeometry(0.22, 0.28, 1.1, 6);
  const crownGeometry = new THREE.ConeGeometry(1.1, 2.5, 7);
  const trunkMaterial = new THREE.MeshStandardMaterial({ color: 0x6b4c3c, roughness: 1 });
  const crownMaterial = new THREE.MeshStandardMaterial({ color: 0x315d49, roughness: 1 });
  for (let i = 0; i < 36; i += 1) {
    const angle = i * 2.39996;
    const radius = 16 + (i % 5) * 2.3;
    const x = Math.cos(angle) * radius;
    const z = Math.sin(angle) * radius * 0.72;
    if (onRoad(x, z) || nearest(x, z).distance < halfWidth + 2.2) continue;
    const trunk = new THREE.Mesh(trunkGeometry, trunkMaterial);
    trunk.position.set(x, 0.5, z);
    trunk.castShadow = true;
    scene.add(trunk);
    const crown = new THREE.Mesh(crownGeometry, crownMaterial);
    crown.position.set(x, 2.1, z);
    crown.castShadow = true;
    scene.add(crown);
  }

  return { samples, halfWidth, start, nearest, onRoad };
}
