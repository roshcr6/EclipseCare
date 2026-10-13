import { useEffect, useRef, useCallback } from 'react';
import { animate, stagger, Timeline } from 'animejs';

const HAPTICS = [
  {
    id: 'med',
    label: 'Medication',
    pattern: 'Soft double-vibration',
    color: '#E07A5F',
    anim: (icon) => animate(icon, {
      translateX: [
        { to: -6 }, { to: 6 }, { to: -4 }, { to: 4 }, { to: 0 }
      ],
      duration: 350, ease:'linear',
    }),
  },
  {
    id: 'hyd',
    label: 'Hydration',
    pattern: 'Gentle pulse',
    color: '#22D3EE',
    anim: (icon) => animate(icon, {
      scale: [{ to: 1.18 }, { to: 0.95 }, { to: 1 }],
      duration: 600, ease:'inOutSine',
    }),
  },
  {
    id: 'rtn',
    label: 'Routine',
    pattern: 'Rhythmic wave',
    color: '#4ADE80',
    anim: (icon) => animate(icon, {
      rotate: [
        { to: -10 }, { to: 10 }, { to: -5 }, { to: 5 }, { to: 0 }
      ],
      duration: 450, ease:'linear',
    }),
  },
];

function HapticCard({ data }) {
  const cardRef = useRef();
  const iconRef = useRef();

  const handleHover = useCallback(() => {
    animate(cardRef.current, { scale:1.04, duration:300, ease:'spring(1,80,10,0)' });
    data.anim(iconRef.current);
  }, [data]);

  const handleLeave = useCallback(() => {
    animate(cardRef.current, { scale:1, duration:300, ease:'spring(1,80,10,0)' });
  }, []);

  return (
    <div ref={cardRef}
      onMouseEnter={handleHover}
      onMouseLeave={handleLeave}
      style={{
        width:210, padding:'2rem 1.6rem',
        background:'rgba(255,255,255,0.04)',
        backdropFilter:'blur(20px)',
        border:`1px solid rgba(255,255,255,0.07)`,
        borderTop:`2px solid ${data.color}`,
        borderRadius:20, textAlign:'center',
        cursor:'pointer', willChange:'transform',
        position:'relative', overflow:'hidden',
      }}>
      <div style={{
        position:'absolute', top:0, left:'50%', transform:'translateX(-50%)',
        width:80, height:40, borderRadius:'0 0 50% 50%',
        background:`radial-gradient(ellipse, ${data.color}22, transparent)`,
        pointerEvents:'none',
      }} />
      <div ref={iconRef} style={{
        width:60, height:60, margin:'0 auto 1.2rem',
        background:`${data.color}14`,
        border:`1px solid ${data.color}40`,
        borderRadius:'50%', display:'flex', alignItems:'center', justifyContent:'center',
        willChange:'transform',
      }}>
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
          {data.id === 'med' && (
            <>
              <circle cx="14" cy="14" r="12" stroke={data.color} strokeWidth="1.2" opacity="0.4"/>
              <path d="M10 14h8M14 10v8" stroke={data.color} strokeWidth="1.8" strokeLinecap="round"/>
            </>
          )}
          {data.id === 'hyd' && (
            <path d="M14 4c0 0-7 9-7 14a7 7 0 0 0 14 0c0-5-7-14-7-14z"
              stroke={data.color} strokeWidth="1.4" fill="none" strokeLinejoin="round"/>
          )}
          {data.id === 'rtn' && (
            <>
              <circle cx="14" cy="14" r="10" stroke={data.color} strokeWidth="1.2" opacity="0.4"/>
              <path d="M9 14a5 5 0 0 1 10 0" stroke={data.color} strokeWidth="1.6" strokeLinecap="round" fill="none"/>
              <circle cx="14" cy="14" r="2" fill={data.color}/>
            </>
          )}
        </svg>
      </div>
      <h3 style={{ fontSize:'0.82rem', fontWeight:700, letterSpacing:'0.04em', color:'white', marginBottom:'0.4rem' }}>
        {data.label}
      </h3>
      <span style={{
        display:'inline-block', marginTop:'0.8rem',
        fontFamily:"'Space Mono',monospace",
        fontSize:'0.48rem', letterSpacing:'0.2em', textTransform:'uppercase',
        color:data.color, border:`1px solid ${data.color}30`, borderRadius:4,
        padding:'0.2rem 0.6rem',
      }}>{data.pattern}</span>
    </div>
  );
}

export default function HapticSection({ visible }) {
  const wrapRef  = useRef();
  const titleRef = useRef();
  const cardsRef = useRef();

  useEffect(() => {
    if (!wrapRef.current) return;
    if (visible) {
      wrapRef.current.style.pointerEvents = 'all';
      const tl = new Timeline({ defaults: { ease:'outExpo' } });
      tl.add(wrapRef.current, { opacity:[0,1], duration:400 })
        .add(titleRef.current, { opacity:[0,1], translateY:[30,0], duration:700 }, '-=200')
        .add([...cardsRef.current.children], {
          opacity:[0,1], translateY:[60,0],
          delay: stagger(120), duration:600, ease:'spring(1,80,10,0)',
        }, '-=400');
    } else {
      wrapRef.current.style.pointerEvents = 'none';
      animate(wrapRef.current, { opacity:0, duration:300 });
    }
  }, [visible]);

  return (
    <div ref={wrapRef} style={{
      position:'fixed', inset:0,
      display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center',
      gap:'3rem', zIndex:30, opacity:0, pointerEvents:'none',
    }}>
      <div ref={titleRef} style={{ textAlign:'center', opacity:0 }}>
        <p style={{ fontFamily:"'Space Mono',monospace", fontSize:'0.55rem', letterSpacing:'0.35em',
          textTransform:'uppercase', color:'#E07A5F', marginBottom:'0.8rem' }}>
          Haptic · Section 04
        </p>
        <h2 style={{
          fontSize:'clamp(2.5rem,5vw,5.5rem)', fontWeight:800, letterSpacing:'-0.04em', lineHeight:0.9,
          background:'linear-gradient(135deg,white,rgba(255,255,255,0.35))',
          WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent',
        }}>
          Dignity First.
        </h2>
      </div>

      <div ref={cardsRef} style={{ display:'flex', gap:'1.2rem' }}>
        {HAPTICS.map(h => <HapticCard key={h.id} data={h} />)}
      </div>
    </div>
  );
}
