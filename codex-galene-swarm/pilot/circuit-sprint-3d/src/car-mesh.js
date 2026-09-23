import * as THREE from 'three';

export function createCarMesh(color) {
  const group = new THREE.Group();

  const bodyColor = new THREE.Color(color);
  const darkColor = bodyColor.clone().multiplyScalar(0.35);
  const accentColor = bodyColor.clone().lerp(new THREE.Color(0xffffff), 0.6).offsetHSL(0.1, 0.2, -0.1);

  // Body
  const bodyGeo = new THREE.BoxGeometry(1.5, 0.45, 2.5);
  const bodyMat = new THREE.MeshLambertMaterial({ color: bodyColor });
  const body = new THREE.Mesh(bodyGeo, bodyMat);
  body.position.y = 0.3;
  group.add(body);

  // Hood (front section, slightly lower and forward)
  const hoodGeo = new THREE.BoxGeometry(1.4, 0.3, 0.8);
  const hoodMat = new THREE.MeshLambertMaterial({ color: bodyColor });
  const hood = new THREE.Mesh(hoodGeo, hoodMat);
  hood.position.set(0, 0.25, 0.9);
  group.add(hood);

  // Rear section
  const rearGeo = new THREE.BoxGeometry(1.4, 0.35, 0.7);
  const rearMat = new THREE.MeshLambertMaterial({ color: bodyColor });
  const rear = new THREE.Mesh(rearGeo, rearMat);
  rear.position.set(0, 0.28, -0.9);
  group.add(rear);

  // Cockpit / cabin
  const cockpitGeo = new THREE.BoxGeometry(1.1, 0.35, 1.0);
  const cockpitMat = new THREE.MeshLambertMaterial({ color: darkColor });
  const cockpit = new THREE.Mesh(cockpitGeo, cockpitMat);
  cockpit.position.set(0, 0.55, -0.1);
  group.add(cockpit);

  // Windshield (slanted front of cockpit)
  const windshieldGeo = new THREE.BoxGeometry(1.0, 0.25, 0.15);
  const windshieldMat = new THREE.MeshLambertMaterial({ color: 0x88ccff, transparent: true, opacity: 0.7 });
  const windshield = new THREE.Mesh(windshieldGeo, windshieldMat);
  windshield.position.set(0, 0.55, 0.45);
  windshield.rotation.x = -0.4;
  group.add(windshield);

  // Front accent stripe
  const accentGeo = new THREE.BoxGeometry(1.52, 0.12, 0.3);
  const accentMat = new THREE.MeshLambertMaterial({ color: accentColor });
  const accent = new THREE.Mesh(accentGeo, accentMat);
  accent.position.set(0, 0.42, 1.15);
  group.add(accent);

  // Front bumper accent
  const bumperGeo = new THREE.BoxGeometry(1.5, 0.15, 0.1);
  const bumperMat = new THREE.MeshLambertMaterial({ color: accentColor });
  const bumper = new THREE.Mesh(bumperGeo, bumperMat);
  bumper.position.set(0, 0.15, 1.25);
  group.add(bumper);

  // Wheels
  const wheelGeo = new THREE.CylinderGeometry(0.25, 0.25, 0.2, 12);
  const wheelMat = new THREE.MeshLambertMaterial({ color: 0x1a1a1a });

  const wheelPositions = [
    [-0.7, 0.25, 0.8],   // front left
    [0.7, 0.25, 0.8],    // front right
    [-0.7, 0.25, -0.8],  // rear left
    [0.7, 0.25, -0.8]    // rear right
  ];

  for (const pos of wheelPositions) {
    const wheel = new THREE.Mesh(wheelGeo, wheelMat);
    wheel.rotation.z = Math.PI / 2;
    wheel.position.set(pos[0], pos[1], pos[2]);
    group.add(wheel);
  }

  return group;
}
