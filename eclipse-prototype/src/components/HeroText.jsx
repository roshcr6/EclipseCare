import { useEffect, useRef } from 'react';
import { animate, stagger, Timeline } from 'animejs';

export default function HeroText({ visible }) {
  const eyebrowRef = useRef();
  const h1Ref      = useRef();
  const subRef     = useRef();

  useEffect(() => {
    if (!visible) {
      animate([eyebrowRef.current, h1Ref.current, subRef.current], {
        opacity: 0, translateY: -20, duration: 400, ease: 'outCubic',
      });
      return;
    }
    const tl = new Timeline({ defaults: { ease: 'outExpo' } });
    tl.add(eyebrowRef.current, { opacity: [0,1], translateY: [15,0], duration: 600 })
      .add(h1Ref.current,      { opacity: [0,1], translateY: [30,0], duration: 800 }, '-=300')
      .add(subRef.current,     { opacity: [0,1], translateY: [20,0], duration: 600 }, '-=400');
  }, [visible]);

  return (
    <div style={{
      position:'fixed', inset:0,
      display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center',
      textAlign:'center', pointerEvents:'none', zIndex:20, padding:'0 2rem',
    }}>
      <p ref={eyebrowRef} style={{
        fontFamily:"'Space Mono',monospace",
        fontSize:'0.62rem', letterSpacing:'0.45em',
        textTransform:'uppercase', color:'#E07A5F',
        marginBottom:'1.5rem', opacity:0,
      }}>Eclipse Wearable System · Clinical AI · 2026</p>

      <h1 ref={h1Ref} style={{
        fontSize:'clamp(3.5rem,10vw,10rem)',
        fontWeight:800, letterSpacing:'-0.04em',
        lineHeight:0.88, marginBottom:'1.8rem', opacity:0,
        background:'linear-gradient(135deg,#fff 0%,rgba(255,255,255,0.35) 100%)',
        WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent',
      }}>
        ECLIPSE.
      </h1>

      <p ref={subRef} style={{
        fontSize:'clamp(0.8rem,1.2vw,1rem)',
        fontWeight:300, color:'#64748B', lineHeight:1.85,
        maxWidth:380, opacity:0,
      }}>
        Invisible monitoring.<br/>Absolute dignity.
      </p>

      <div style={{ marginTop:'3rem', opacity: visible ? 1 : 0, transition:'opacity 1s 1.5s' }}>
        <ScrollHint />
      </div>
    </div>
  );
}

function ScrollHint() {
  const lineRef = useRef();

  useEffect(() => {
    animate(lineRef.current, {
      translateY: [0, 20],
      opacity: [1, 0],
      duration: 1200,
      loop: true,
      ease: 'inQuad',
    });
  }, []);

  return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:'0.7rem' }}>
      <span style={{ fontFamily:"'Space Mono',monospace", fontSize:'0.5rem', letterSpacing:'0.3em', color:'#334155', textTransform:'uppercase' }}>
        scroll
      </span>
      <div ref={lineRef} style={{ width:1, height:48, background:'linear-gradient(to bottom, #64748B, transparent)' }} />
    </div>
  );
}
