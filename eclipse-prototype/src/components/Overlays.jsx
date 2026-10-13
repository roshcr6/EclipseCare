import { useEffect, useRef } from 'react';
import { animate, stagger, Timeline } from 'animejs';

// ── Section label that fades in/out ─────────────────────────
export function SectionLabel({ visible, tag, headline, sub, align = 'left' }) {
  const ref = useRef();

  useEffect(() => {
    if (!ref.current) return;
    if (visible) {
      const tl = new Timeline({ defaults: { ease: 'outExpo' } });
      tl.add(ref.current.querySelector('.sl-tag'), { opacity:[0,1], translateY:[8,0], duration:400 })
        .add(ref.current.querySelector('.sl-h2'),  { opacity:[0,1], translateY:[25,0], duration:700 }, '-=200')
        .add(ref.current.querySelector('.sl-p'),   { opacity:[0,1], translateY:[15,0], duration:500 }, '-=400');
      animate(ref.current, { opacity:[0,1], duration: 100 });
    } else {
      animate(ref.current, { opacity: 0, translateY: -10, duration:300, ease:'inCubic' });
    }
  }, [visible]);

  return (
    <div ref={ref} style={{
      position:'fixed', bottom:'5rem', padding:'0 4rem',
      left: align === 'left'  ? 0 : 'auto',
      right: align === 'right' ? 0 : 'auto',
      zIndex:25, maxWidth:480, opacity:0, pointerEvents:'none',
    }}>
      <p className="sl-tag" style={{
        fontFamily:"'Space Mono',monospace",
        fontSize:'0.55rem', letterSpacing:'0.35em', color:'#E07A5F',
        textTransform:'uppercase', marginBottom:'0.6rem', opacity:0,
      }}>{tag}</p>
      <h2 className="sl-h2" style={{
        fontSize:'clamp(2rem,4vw,4.5rem)', fontWeight:800, letterSpacing:'-0.04em',
        lineHeight:0.95, marginBottom:'0.8rem', opacity:0, whiteSpace:'pre-line',
        background:'linear-gradient(135deg,white,rgba(255,255,255,0.4))',
        WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent',
      }}>{headline}</h2>
      <p className="sl-p" style={{
        fontSize:'0.85rem', color:'#64748B', lineHeight:1.7, fontWeight:300, opacity:0,
      }}>{sub}</p>
    </div>
  );
}

// ── SVG signal pulse rings ───────────────────────────────────
export function SignalRings({ visible }) {
  const svgRef = useRef();
  const animRef = useRef(null);

  useEffect(() => {
    if (!svgRef.current) return;
    const rings = svgRef.current.querySelectorAll('.signal-r');
    if (visible) {
      animRef.current = animate(rings, {
        r:       { from: 60, to: 280 },
        opacity: [{ to: 0.8 }, { to: 0 }],
        strokeWidth: { from: 2, to: 0.3 },
        delay:   stagger(220),
        duration:1800,
        loop:    true,
        ease:    'outCirc',
      });
    } else {
      animRef.current?.pause();
    }
    return () => animRef.current?.pause();
  }, [visible]);

  if (!visible) return null;

  return (
    <svg ref={svgRef} style={{ position:'fixed', inset:0, width:'100%', height:'100%',
      pointerEvents:'none', zIndex:8 }}>
      <g transform={`translate(${window.innerWidth/2},${window.innerHeight/2})`}>
        {[0,1,2,3].map(i => (
          <circle key={i} className="signal-r" cx={0} cy={0} r={60}
            fill="none" stroke="#22D3EE" strokeWidth={2} opacity={0} />
        ))}
        <line x1={0} y1={0} x2={220} y2={-130} stroke="#22D3EE" strokeWidth={0.6} strokeDasharray="5,7" opacity={0.3}/>
        <line x1={0} y1={0} x2={220} y2={130}  stroke="#22D3EE" strokeWidth={0.6} strokeDasharray="5,7" opacity={0.3}/>
        <line x1={0} y1={0} x2={-200} y2={-60} stroke="#E07A5F" strokeWidth={0.5} strokeDasharray="5,7" opacity={0.25}/>
      </g>
    </svg>
  );
}

// ── Dashboard metric cards ───────────────────────────────────
const CARDS = [
  { tag:'RTLS Accuracy', val:'0.8m', color:'#22D3EE' },
  { tag:'Fall Risk',     val:'LOW',  color:'#FBBF24' },
  { tag:'Battery Fleet', val:'94%',  color:'#4ADE80' },
];

export function DashCards({ visible }) {
  const cardsRef = useRef([]);

  useEffect(() => {
    const nodes = cardsRef.current.filter(Boolean);
    if (!nodes.length) return;
    if (visible) {
      animate(nodes, {
        opacity: [0,1], translateY: [60,0],
        delay: stagger(120, { start: 200 }),
        duration: 700, ease: 'spring(1,80,10,0)',
      });
    } else {
      animate(nodes, { opacity: 0, translateY: 30, duration: 300 });
    }
  }, [visible]);

  return (
    <div style={{
      position:'fixed', top:'50%', right:'2.5rem',
      transform:'translateY(-50%)', zIndex:30,
      display:'flex', flexDirection:'column', gap:'0.8rem',
      pointerEvents: visible ? 'all' : 'none',
    }}>
      {CARDS.map((c, i) => (
        <div key={i} ref={el => cardsRef.current[i] = el}
          style={{
            background:'rgba(255,255,255,0.04)', backdropFilter:'blur(20px)',
            border:'1px solid rgba(255,255,255,0.07)', borderRadius:12,
            padding:'1rem 1.3rem', opacity:0,
            borderLeft:`2px solid ${c.color}`,
          }}
          onMouseEnter={e => animate(e.currentTarget, { scale:1.04, duration:200, ease:'outQuad' })}
          onMouseLeave={e => animate(e.currentTarget, { scale:1,    duration:200, ease:'outQuad' })}
        >
          <p style={{ fontFamily:"'Space Mono',monospace", fontSize:'0.48rem', letterSpacing:'0.2em', color:c.color, marginBottom:3 }}>{c.tag}</p>
          <p style={{ fontSize:'1.6rem', fontWeight:800, letterSpacing:'-0.03em', color:'white', lineHeight:1 }}>{c.val}</p>
        </div>
      ))}
    </div>
  );
}
