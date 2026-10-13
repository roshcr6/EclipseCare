// ── ECLIPSE Motion Config ────────────────────────────────────
// Central animation tokens — change here, affects everywhere

export const motion = {
  duration: {
    instant:  80,
    fast:     240,
    medium:   500,
    slow:     900,
    cinematic:1600,
  },
  ease: {
    standard:  'easeOutCubic',
    emphasized:'easeOutExpo',
    spring:    'spring(1, 80, 10, 0)',
    springSnap:'spring(1, 120, 10, 0)',
    reveal:    'cubicBezier(.16,1,.3,1)',
    cinematic: 'cubicBezier(.76,0,.24,1)',
    linear:    'linear',
  },
  stagger: {
    tight:  25,
    normal: 60,
    loose:  120,
    airy:   200,
  },
  distance: {
    xs:  8,
    sm:  20,
    md:  50,
    lg:  100,
    xl:  200,
  },
  // Scroll section breakpoints (0-1)
  scroll: {
    heroFade:   [0, 0.12],
    explodeIn:  [0.15, 0.50],
    gateway:    [0.52, 0.72],
    haptic:     [0.74, 1.0],
  },
};

export const theme = {
  colors: {
    ink:    '#030712',
    slate:  '#0F172A',
    mid:    '#1E293B',
    muted:  '#334155',
    dim:    '#64748B',
    light:  '#CBD5E1',
    coral:  '#E07A5F',
    coral2: '#F4956F',
    cyan:   '#22D3EE',
    violet: '#818CF8',
    mint:   '#4ADE80',
    amber:  '#FBBF24',
    neon:   '#39FF14',
  },
  layer: {
    shell:   { color: '#334155', stroke: '#64748B', accent: '#94A3B8' },
    logic:   { color: '#0c1628', stroke: '#22D3EE', accent: '#7DD3FC' },
    battery: { color: '#1c0f10', stroke: '#E07A5F', accent: '#FCA5A5' },
    sensors: { color: '#0c2015', stroke: '#4ADE80', accent: '#DCFCE7' },
    strap:   { color: '#0F172A', stroke: '#475569', accent: '#CBD5E1' },
  },
};
