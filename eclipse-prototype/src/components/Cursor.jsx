import { useEffect, useRef } from 'react';
import { animate } from 'animejs';

export default function Cursor() {
  const dotRef  = useRef(null);
  const ringRef = useRef(null);
  let cursorX = 0, cursorY = 0;
  let ringX   = 0, ringY   = 0;
  let raf;

  useEffect(() => {
    const dot  = dotRef.current;
    const ring = ringRef.current;

    function onMove(e) {
      cursorX = e.clientX;
      cursorY = e.clientY;
      dot.style.transform = `translate(${cursorX}px, ${cursorY}px) translate(-50%,-50%)`;
    }

    function loop() {
      ringX += (cursorX - ringX) * 0.12;
      ringY += (cursorY - ringY) * 0.12;
      ring.style.transform = `translate(${ringX}px, ${ringY}px) translate(-50%,-50%)`;
      raf = requestAnimationFrame(loop);
    }

    function onEnter() {
      animate(ring, { width: 64, height: 64, opacity: 0.6, duration: 300, ease: 'spring(1,80,10,0)' });
      animate(dot,  { scale: 0.3, opacity: 0.5, duration: 200, ease: 'outQuad' });
    }
    function onLeave() {
      animate(ring, { width: 40, height: 40, opacity: 1, duration: 300, ease: 'spring(1,80,10,0)' });
      animate(dot,  { scale: 1,   opacity: 1, duration: 200, ease: 'outQuad' });
    }

    window.addEventListener('mousemove', onMove, { passive: true });
    document.querySelectorAll('a,button,[data-cursor]').forEach(el => {
      el.addEventListener('mouseenter', onEnter);
      el.addEventListener('mouseleave', onLeave);
    });

    raf = requestAnimationFrame(loop);
    return () => {
      window.removeEventListener('mousemove', onMove);
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <>
      <div ref={dotRef} style={{
        position:'fixed', top:0, left:0,
        width:10, height:10, background:'#E07A5F', borderRadius:'50%',
        pointerEvents:'none', zIndex:9999, willChange:'transform', mixBlendMode:'difference',
      }} />
      <div ref={ringRef} style={{
        position:'fixed', top:0, left:0,
        width:40, height:40, border:'1px solid rgba(224,122,95,0.6)', borderRadius:'50%',
        pointerEvents:'none', zIndex:9998, willChange:'transform',
      }} />
    </>
  );
}
