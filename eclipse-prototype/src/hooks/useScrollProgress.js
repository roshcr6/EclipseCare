import { useEffect, useRef } from 'react';

/** Returns a ref { progress: 0-1, velocity: number } updated on every scroll event. */
export function useScrollProgress() {
  const scroll = useRef({ progress: 0, velocity: 0, y: 0 });

  useEffect(() => {
    let lastY = 0;

    function onScroll() {
      const el = document.documentElement;
      const y  = window.scrollY;
      const max = el.scrollHeight - window.innerHeight;
      const progress = max > 0 ? y / max : 0;
      const velocity = y - lastY;
      scroll.current = { progress, velocity, y };
      lastY = y;
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return scroll;
}
