export function makeTrackSamples(count = 240) {
    const points = [];
    for (let i = 0; i < count; i++) {
        const t = (i / count) * Math.PI * 2;
        // Base oval with harmonic deformation to create bends
        const rX = 15 + 3 * Math.sin(2 * t) + 1.5 * Math.cos(3 * t);
        const rZ = 10 + 2 * Math.cos(2 * t) + 1 * Math.sin(4 * t);

        // Scale and offset to center around origin
        const x = rX * Math.cos(t);
        const z = rZ * Math.sin(t);

        points.push({ x, z });
    }
    return points;
}

export function nearestTrackPoint(samples, x, z) {
    let minDistSq = Infinity;
    let bestIndex = 0;

    for (let i = 0; i < samples.length; i++) {
        const dx = samples[i].x - x;
        const dz = samples[i].z - z;
        const distSq = dx * dx + dz * dz;
        if (distSq < minDistSq) {
            minDistSq = distSq;
            bestIndex = i;
        }
    }

    const n = samples.length;
    const prevIdx = (bestIndex - 1 + n) % n;
    const nextIdx = (bestIndex + 1) % n;

    const pPrev = samples[prevIdx];
    const pCurr = samples[bestIndex];
    const pNext = samples[nextIdx];

    // Calculate tangent using central difference or forward/backward at boundaries
    let tx, tz;
    if (n > 2) {
        tx = pNext.x - pPrev.x;
        tz = pNext.z - pPrev.z;
    } else {
        tx = pNext.x - pCurr.x;
        tz = pNext.z - pCurr.z;
    }

    const len = Math.sqrt(tx * tx + tz * tz);
    if (len > 0) {
        tx /= len;
        tz /= len;
    } else {
        tx = 1;
        tz = 0;
    }

    const distance = Math.sqrt(minDistSq);
    const progress = bestIndex / n;

    return {
        x: pCurr.x,
        z: pCurr.z,
        tangentX: tx,
        tangentZ: tz,
        distance,
        progress,
        index: bestIndex
    };
}
