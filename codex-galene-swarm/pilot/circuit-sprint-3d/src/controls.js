// src/controls.js

export function createControls(target = window) {
  const keyState = new Set();

  // Track which keys are currently pressed by code
  function handleKeyDown(event) {
    // Prevent default for arrow keys and space to avoid scrolling
    if (event.code === 'ArrowUp' || event.code === 'ArrowDown' ||
        event.code === 'ArrowLeft' || event.code === 'ArrowRight' ||
        event.code === 'Space') {
      event.preventDefault();
    }

    // Add to set; Set handles duplicates naturally
    keyState.add(event.code);
  }

  function handleKeyUp(event) {
    keyState.delete(event.code);
  }

  function handleBlur() {
    // Clear all keys on window blur
    keyState.clear();
  }

  target.addEventListener('keydown', handleKeyDown);
  target.addEventListener('keyup', handleKeyUp);
  target.addEventListener('blur', handleBlur);

  function read(playerNumber) {
    let throttle = 0;
    let brake = 0;
    let steer = 0;

    if (playerNumber === 1) {
      // Throttle: W or ArrowUp
      if (keyState.has('KeyW') || keyState.has('ArrowUp')) {
        throttle = 1;
      }

      // Brake: S or ArrowDown
      if (keyState.has('KeyS') || keyState.has('ArrowDown')) {
        brake = 1;
      }

      // Steer left: A or ArrowLeft
      if (keyState.has('KeyA') || keyState.has('ArrowLeft')) {
        steer = -1;
      }

      // Steer right: D or ArrowRight
      if (keyState.has('KeyD') || keyState.has('ArrowRight')) {
        steer = 1;
      }
    } else if (playerNumber === 2) {
      // Throttle: I
      if (keyState.has('KeyI')) {
        throttle = 1;
      }

      // Brake: K
      if (keyState.has('KeyK')) {
        brake = 1;
      }

      // Steer left: J
      if (keyState.has('KeyJ')) {
        steer = -1;
      }

      // Steer right: L
      if (keyState.has('KeyL')) {
        steer = 1;
      }
    }

    return { throttle, brake, steer };
  }

  let disposed = false;

  function dispose() {
    if (disposed) return;
    disposed = true;

    target.removeEventListener('keydown', handleKeyDown);
    target.removeEventListener('keyup', handleKeyUp);
    target.removeEventListener('blur', handleBlur);

    keyState.clear();
  }

  return { read, dispose };
}
