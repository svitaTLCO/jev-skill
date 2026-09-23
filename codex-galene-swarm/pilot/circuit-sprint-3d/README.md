# Circuit Sprint 3D

A playable browser-based 3D overhead racer built as a real-work pilot for Codex
Galene Swarm. The 1989 NES Super Sprint inspired its circuit racing, oil
hazards, collectible upgrades, and local competition. The track, cars, UI,
names, and geometry are original; no game assets or code were copied.

This first slice has one circuit, four cars, one or two local keyboard players,
AI opponents, three-lap races, oil slicks, wrench upgrades, standings, pause,
and a result screen. Player 1 uses WASD or arrow keys; player 2 uses I/J/K/L.
Escape pauses or resumes. A browser with WebGL is required.

## Run and verify in Docker

From this directory:

```bash
rtk docker run --rm --user "$(rtk id -u):$(rtk id -g)" -v "$PWD:/app" -w /app node:22-alpine npm ci
rtk docker run --rm --user "$(rtk id -u):$(rtk id -g)" -v "$PWD:/app" -w /app node:22-alpine npm test
rtk docker run --rm --user "$(rtk id -u):$(rtk id -g)" -v "$PWD:/app" -w /app node:22-alpine npm run build
rtk docker run --rm --user "$(rtk id -u):$(rtk id -g)" --ipc=host -v "$PWD:/app" -w /app mcr.microsoft.com/playwright:v1.63.0-noble npm run test:e2e
```

To play locally, serve the Vite preview from Docker and open
`http://localhost:4173`:

```bash
rtk docker run --rm --user "$(rtk id -u):$(rtk id -g)" -p 4173:4173 -v "$PWD:/app" -w /app node:22-alpine npm run preview -- --port 4173
```

The first build is checked by five Node tests and two Chromium browser tests.
See [PILOT_EVIDENCE.md](PILOT_EVIDENCE.md) for what the swarm generated, Jev's
decisions, and the validation limits. A [race screenshot](screenshots/racing.png)
is committed for review after a fresh clone. The browser tests render with software
WebGL inside the official Playwright container, so they can run slowly.

Reference mechanics: the [NES game archive](https://www.gamesdatabase.org/game/nintendo-nes/super-sprint)
describes overhead circuits, hazards, wrenches, and upgrades.
