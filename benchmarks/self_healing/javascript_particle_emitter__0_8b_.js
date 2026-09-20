class ParticleEmitter {
  constructor() {
    this.particles = [];
  }

  // Create particles with random velocities
  emit(x, y, count, color) {
    for (let i = 0; i < count; i++) {
      // Random velocity components
      const velocityX = (Math.random() - 0.5) * 10;
      const velocityY = (Math.random() - 0.5) * 10;
      const speed = Math.sqrt(velocityX * velocityX + velocityY * velocityY);
      
      // Random direction (angle)
      const angle = Math.random() * Math.PI * 2;
      
      // Random color
      const color = `hsl(${Math.random() * 360}, 70%, 60%)`;
      
      // Create particle
      this.particles.push({
        x,
        y,
        velocityX: velocityX,
        velocityY: velocityY,
        speed: speed,
        angle: angle,
        color: color,
        life: 1.0,
        alpha: 1.0,
        size: 10 + Math.random() * 10,
        rotation: 0
      });
    }
  }

  // Update positions, alpha, and draw circles
  update(ctx) {
    // Update positions
    for (let i =