import { useEffect, useRef, useState, useCallback } from 'react';
import { Canvas } from '@react-three/fiber';
import { animate, stagger, Timeline } from 'animejs';
import * as THREE from 'three';
import EclipseScene from './three/EclipseScene.jsx';
import Cursor from './components/Cursor.jsx';
import './index.css';

// ─── Tiny spring interpolation for DOM elements ───────────────
function lerp(a, b, t) { return a + (b - a) * t; }

// ─── Scroll progress (0-1) ───────────────────────────────────
function useScrollRef() {
  const ref = useRef({ progress: 0, velocity: 0 });
  useEffect(() => {
    let lastY = 0;
    const fn = () => {
      const el = document.documentElement;
      const y = window.scrollY;
      const max = el.scrollHeight - window.innerHeight;
      ref.current.progress = max > 0 ? y / max : 0;
      ref.current.velocity = y - lastY;
      lastY = y;
    };
    window.addEventListener('scroll', fn, { passive: true });
    return () => window.removeEventListener('scroll', fn);
  }, []);
  return ref;
}

// ─── Mouse position (−1 to +1) ───────────────────────────────
function useMouseRef() {
  const mx = useRef(0), my = useRef(0);
  useEffect(() => {
    const fn = (e) => {
      mx.current = (e.clientX / window.innerWidth) * 2 - 1;
      my.current = (e.clientY / window.innerHeight) * 2 - 1;
    };
    window.addEventListener('mousemove', fn, { passive: true });
    return () => window.removeEventListener('mousemove', fn);
  }, []);
  return { x: mx, y: my };
}

// ─── Section nav dot ─────────────────────────────────────────
function NavDot({ active }) {
  return (
    <div style={{
      width: 5, height: 5, borderRadius: '50%',
      background: active ? '#E07A5F' : '#334155',
      boxShadow: active ? '0 0 8px #E07A5F' : 'none',
      transform: active ? 'scale(1.9)' : 'scale(1)',
      transition: 'all 0.45s cubic-bezier(.16,1,.3,1)',
    }} />
  );
}

// ─── Topbar NAV ───────────────────────────────────────────────
function TopNav() {
  return (
    <nav style={{
      position: 'fixed', top: 0, left: 0, right: 0,
      padding: '1.1rem 3rem',
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      background: 'rgba(3,7,18,0.72)', backdropFilter: 'blur(18px)',
      borderBottom: '1px solid rgba(255,255,255,0.04)', zIndex: 500,
    }}>
      <span style={{ fontWeight: 800, letterSpacing: '0.22em', fontSize: '0.88rem', textTransform: 'uppercase' }}>
        ECLIPSE<span style={{ color: '#E07A5F' }}>.</span>
      </span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{
          width: 6, height: 6, borderRadius: '50%', background: '#4ADE80', boxShadow: '0 0 8px #4ADE80',
          animation: 'pulse 2s infinite'
        }} />
        <span style={{ fontFamily: "'Space Mono',monospace", fontSize: '0.58rem', letterSpacing: '0.06em', color: '#64748B' }}>
          LIVE
        </span>
      </div>
      <button
        data-cursor
        style={{
          fontFamily: "'Space Mono',monospace", fontSize: '0.6rem', letterSpacing: '0.1em',
          color: '#E07A5F', background: 'transparent', border: '1px solid rgba(224,122,95,0.4)',
          padding: '0.5rem 1.2rem', borderRadius: 4, cursor: 'pointer',
          transition: 'all 0.25s',
        }}
        onMouseEnter={e => { e.target.style.background = '#E07A5F'; e.target.style.color = '#030712'; }}
        onMouseLeave={e => { e.target.style.background = 'transparent'; e.target.style.color = '#E07A5F'; }}
      >
        Request Demo
      </button>
    </nav>
  );
}

// ─── Progress bar ─────────────────────────────────────────────
function ProgressBar({ scrollRef }) {
  const barRef = useRef();
  useEffect(() => {
    let raf;
    const tick = () => {
      if (barRef.current) {
        barRef.current.style.transform = `scaleX(${scrollRef.current.progress})`;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [scrollRef]);

  return (
    <div ref={barRef} style={{
      position: 'fixed', top: 0, left: 0, width: '100%', height: 2,
      background: 'linear-gradient(90deg,#E07A5F,#22D3EE,#818CF8)',
      transformOrigin: 'left', transform: 'scaleX(0)', zIndex: 1000,
      willChange: 'transform',
    }} />
  );
}

// ─── Hero copy (fades out after 15% scroll) ───────────────────
function HeroOverlay({ scrollRef }) {
  const wrapRef = useRef();
  const eyeRef = useRef();
  const h1Ref = useRef();
  const subRef = useRef();
  const scrollLineRef = useRef();
  const mounted = useRef(false);

  useEffect(() => {
    if (mounted.current) return;
    mounted.current = true;
    const tl = new Timeline({ defaults: { ease: 'outExpo' } });
    tl.add(eyeRef.current, { opacity: [0, 1], translateY: [12, 0], duration: 600 }, 400)
      .add(h1Ref.current, { opacity: [0, 1], translateY: [28, 0], duration: 900 }, '-=300')
      .add(subRef.current, { opacity: [0, 1], translateY: [16, 0], duration: 600 }, '-=500')
      .add(scrollLineRef.current, { opacity: [0, 1], duration: 500 }, '-=300');

    // Looping scroll line
    animate(scrollLineRef.current, {
      translateY: [0, 22], opacity: [1, 0],
      duration: 1300, loop: true, ease: 'inQuad', delay: 1200,
    });
  }, []);

  // Hide on scroll
  useEffect(() => {
    let raf;
    const tick = () => {
      if (wrapRef.current) {
        const op = Math.max(0, 1 - scrollRef.current.progress / 0.14);
        wrapRef.current.style.opacity = op;
        wrapRef.current.style.pointerEvents = op < 0.05 ? 'none' : 'all';
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [scrollRef]);

  return (
    <div ref={wrapRef} style={{
      position: 'fixed', inset: 0, zIndex: 20, pointerEvents: 'none',
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'flex-end', paddingBottom: '12vh',
    }}>
      <p ref={eyeRef} style={{
        fontFamily: "'Space Mono',monospace", fontSize: '0.6rem',
        letterSpacing: '0.42em', textTransform: 'uppercase', color: '#E07A5F',
        marginBottom: '1.2rem', opacity: 0,
      }}>
        Wearable Intelligence · 2026
      </p>
      <h1 ref={h1Ref} style={{
        fontSize: 'clamp(4rem,11vw,11rem)',
        fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 0.85,
        marginBottom: '1.4rem', opacity: 0, textAlign: 'center',
        background: 'linear-gradient(160deg,#fff 15%,rgba(255,255,255,0.25) 100%)',
        WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
      }}>
        ECLIPSE<span style={{ WebkitTextFillColor: '#E07A5F' }}>.</span>
      </h1>
      <p ref={subRef} style={{
        fontSize: '0.9rem', color: '#475569', fontWeight: 300,
        letterSpacing: '0.05em', maxWidth: 300, textAlign: 'center',
        lineHeight: 1.8, opacity: 0,
      }}>
        Invisible. Continuous. Dignified care.
      </p>
      <div style={{ marginTop: '2.5rem', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
        <span style={{ fontFamily: "'Space Mono',monospace", fontSize: '0.5rem', letterSpacing: '0.3em', color: '#334155', textTransform: 'uppercase' }}>
          drag · scroll
        </span>
        <div ref={scrollLineRef} style={{ width: 1, height: 44, background: 'linear-gradient(to bottom,#64748B,transparent)', opacity: 0 }} />
      </div>
    </div>
  );
}

// ─── Section labels (EXPLODE / GATEWAY / HAPTIC) ──────────────
const SEC_DEFS = [
  { id: 'explode', range: [0.18, 0.75], tag: 'Hardware Architecture', headline: 'Five Layers.\nOne Shield.', sub: 'Drag to rotate · scroll to inspect.', align: 'left' },
  { id: 'final', range: [0.78, 1.00], tag: 'Eclipse Care · Platform', headline: 'Invisible\nProtection.', sub: 'Real-time vitals. Fall detection. BLE gateway.', align: 'left' },
];

function SectionLabels({ scrollRef }) {
  const refs = useRef({});
  let prevSection = useRef(null);

  useEffect(() => {
    let raf;
    const tick = () => {
      const p = scrollRef.current.progress;
      let activeSec = null;
      SEC_DEFS.forEach(s => { if (p >= s.range[0] && p < s.range[1]) activeSec = s.id; });

      if (activeSec !== prevSection.current) {
        // hide all
        SEC_DEFS.forEach(s => {
          const el = refs.current[s.id];
          if (el) animate(el, { opacity: 0, translateY: -8, duration: 300, ease: 'inCubic' });
        });
        // show active
        if (activeSec) {
          const el = refs.current[activeSec];
          if (el) {
            const tl = new Timeline({ defaults: { ease: 'outExpo' } });
            tl.add(el.querySelector('.sl-tag'), { opacity: [0, 1], translateY: [8, 0], duration: 400 })
              .add(el.querySelector('.sl-h2'), { opacity: [0, 1], translateY: [22, 0], duration: 700 }, '-=200')
              .add(el.querySelector('.sl-p'), { opacity: [0, 1], translateY: [12, 0], duration: 500 }, '-=400');
            animate(el, { opacity: 1, translateY: 0, duration: 100 });
          }
        }
        prevSection.current = activeSec;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [scrollRef]);

  return (
    <>
      {SEC_DEFS.map(s => (
        <div key={s.id} ref={el => refs.current[s.id] = el}
          style={{
            position: 'fixed', bottom: '5.5rem', zIndex: 25,
            left: s.align === 'left' ? '3.5rem' : 'auto',
            right: s.align === 'right' ? '3.5rem' : 'auto',
            maxWidth: 420, opacity: 0, pointerEvents: 'none',
          }}>
          <p className="sl-tag" style={{
            fontFamily: "'Space Mono',monospace", fontSize: '0.54rem',
            letterSpacing: '0.35em', color: '#E07A5F', textTransform: 'uppercase',
            marginBottom: '0.55rem', opacity: 0,
          }}>{s.tag}</p>
          <h2 className="sl-h2" style={{
            fontSize: 'clamp(2rem,4vw,4rem)', fontWeight: 800, letterSpacing: '-0.04em',
            lineHeight: 0.95, marginBottom: '0.7rem', opacity: 0, whiteSpace: 'pre-line',
            background: 'linear-gradient(135deg,#fff,rgba(255,255,255,0.35))',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>{s.headline}</h2>
          <p className="sl-p" style={{
            fontSize: '0.82rem', color: '#64748B', lineHeight: 1.7, fontWeight: 300, opacity: 0,
          }}>{s.sub}</p>
        </div>
      ))}
    </>
  );
}

// ─── Side section nav dots ─────────────────────────────────────
const DOT_SECTIONS = [
  { id: 'hero', range: [0, 0.18] },
  { id: 'explode', range: [0.18, 0.75] },
  { id: 'final', range: [0.75, 1.0] },
];

function SectionDots({ scrollRef }) {
  const [active, setActive] = useState('hero');
  useEffect(() => {
    let raf;
    const tick = () => {
      const p = scrollRef.current.progress;
      const sec = DOT_SECTIONS.find(s => p >= s.range[0] && p < s.range[1]);
      if (sec) setActive(sec.id);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [scrollRef]);

  const scrollTo = useCallback((id) => {
    const targets = { hero: 0, explode: 0.22, final: 0.78 };
    const el = document.documentElement;
    const max = el.scrollHeight - window.innerHeight;
    window.scrollTo({ top: targets[id] * max, behavior: 'smooth' });
  }, []);

  return (
    <div style={{
      position: 'fixed', right: '1.6rem', top: '50%', transform: 'translateY(-50%)',
      display: 'flex', flexDirection: 'column', gap: 14, zIndex: 500
    }}>
      {DOT_SECTIONS.map(s => (
        <button key={s.id} onClick={() => scrollTo(s.id)} aria-label={s.id}
          style={{ border: 'none', background: 'none', padding: 4, cursor: 'pointer' }}>
          <NavDot active={active === s.id} />
        </button>
      ))}
    </div>
  );
}

// ─── ROOT APP ─────────────────────────────────────────────────
export default function App() {
  const scrollRef = useScrollRef();
  const mouse = useMouseRef();

  return (
    <>
      {/* Grid noise */}
      <div style={{
        position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none',
        backgroundImage: `
          linear-gradient(rgba(255,255,255,0.018) 1px,transparent 1px),
          linear-gradient(90deg,rgba(255,255,255,0.018) 1px,transparent 1px)`,
        backgroundSize: '54px 54px',
      }} />

      {/* Ambient blobs */}
      <div style={{ position: 'fixed', inset: 0, zIndex: 1, pointerEvents: 'none', overflow: 'hidden' }}>
        <div style={{
          position: 'absolute', width: 700, height: 700, top: -200, left: -200, borderRadius: '50%',
          background: 'radial-gradient(circle,rgba(224,122,95,0.06),transparent 65%)', filter: 'blur(50px)'
        }} />
        <div style={{
          position: 'absolute', width: 500, height: 500, bottom: -100, right: -100, borderRadius: '50%',
          background: 'radial-gradient(circle,rgba(34,211,238,0.05),transparent 65%)', filter: 'blur(50px)'
        }} />
      </div>

      <Cursor />
      <TopNav />
      <ProgressBar scrollRef={scrollRef} />
      <SectionDots scrollRef={scrollRef} />

      {/* ── 3D CANVAS — full viewport, fixed ──────────────────── */}
      <Canvas
        camera={{ position: [0, 0, 6.5], fov: 40, near: 0.1, far: 150 }}
        dpr={[1, 2]}
        shadows
        style={{ position: 'fixed', inset: 0, zIndex: 10, background: 'transparent' }}
        gl={{ antialias: true, alpha: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.0 }}
      >
        <EclipseScene scrollProgress={scrollRef} />
      </Canvas>

      {/* ── 2D UI overlays ─────────────────────────────────────── */}
      <HeroOverlay scrollRef={scrollRef} />
      <SectionLabels scrollRef={scrollRef} />

      {/* ── SCROLL SPACE ───────────────────────────────────────── */}
      <div style={{ height: '550vh' }} />

      <style>{`
        @keyframes pulse {
          0%,100%{opacity:1;transform:scale(1)}
          50%{opacity:0.4;transform:scale(0.7)}
        }
        * { cursor: none !important; }
        html { scroll-behavior: smooth; overflow-x: hidden; }
        body { 
          margin: 0;
          background: linear-gradient(to bottom, #05070A, #0A0D12);
          min-height: 100vh;
        }
      `}</style>
    </>
  );
}
