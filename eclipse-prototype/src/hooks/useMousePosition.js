import { useEffect, useRef } from 'react';

/**
 * Returns a ref that always holds the latest normalized mouse position.
 * { x, y }  → -1 to +1 from center
 * { px, py } → raw pixel coords
 * { vx, vy } → velocity
 */
export function useMousePosition() {
  const pos = useRef({ x: 0, y: 0, px: 0, py: 0, vx: 0, vy: 0 });

  useEffect(() => {
    let lastPx = 0, lastPy = 0;
    let raf;

    function onMove(e) {
      const px = e.clientX;
      const py = e.clientY;
      const x  = (px / window.innerWidth)  * 2 - 1;
      const y  = (py / window.innerHeight) * 2 - 1;
      const vx = px - lastPx;
      const vy = py - lastPy;
      pos.current = { x, y, px, py, vx, vy };
      lastPx = px; lastPy = py;
    }

    window.addEventListener('mousemove', onMove, { passive: true });
    return () => {
      window.removeEventListener('mousemove', onMove);
      cancelAnimationFrame(raf);
    };
  }, []);

  return pos;
}
