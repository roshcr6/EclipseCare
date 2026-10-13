import React, { useRef, useEffect, useState } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import * as THREE from 'three';
import { Timeline } from 'animejs';
import { EffectComposer, Bloom, Noise } from '@react-three/postprocessing';
import { HARDWARE_LAYERS } from './EclipseHardware';

// ─── MASTER MOTION GRAPH ────────────────────────────────────
const motionState = {
  explode: 0,
  rotY: 0,
  rotX: 0,
  camZ: 6.5,
  labelsProgress: 0,
};

export default function EclipseScene({ scrollProgress }) {
  const { camera, size } = useThree();
  const rootGroup = useRef();
  const layerRefs = useRef({});
  const tl = useRef(null);

  const dragState = useRef({
    isDragging: false,
    manualX: 0,
    manualY: 0,
    velX: 0,
    velY: 0,
    lastX: 0,
    lastY: 0,
  });

  // ── 1. SETUP ANIME.JS TIMELINE ──
  useEffect(() => {
    tl.current = new Timeline({
      autoplay: false,
      duration: 1000,
      defaults: { ease: 'linear' }
    });

    tl.current.add(motionState, {
      camZ: [6.5, 14.0],
      duration: 600,
      ease: 'inOutSine'
    }, 150);

    tl.current.add(motionState, {
      rotY: [0, Math.PI * 2.5],
      duration: 850,
      ease: 'inOutSine'
    }, 150);

    // Give each component a slight local spin as it explodes! (Kinetic)
    tl.current.add(motionState, {
      explode: [0, 1.0],
      duration: 450,
      ease: 'inOutCubic'
    }, 300);
    
    // Labels progressive reveal
    tl.current.add(motionState, {
      labelsProgress: [0, 1.0],
      duration: 250,
      ease: 'inOutQuad'
    }, 600);
  }, []);

  // ── 2. DRAG INTERACTION ──
  useEffect(() => {
    const canvas = document.querySelector('canvas');
    if (!canvas) return;
    
    const onDown = (e) => {
      dragState.current.isDragging = true;
      dragState.current.lastX = e.clientX;
      dragState.current.lastY = e.clientY;
      dragState.current.velX = 0;
      dragState.current.velY = 0;
    };
    
    const onMove = (e) => {
      if (!dragState.current.isDragging) return;
      const dx = e.clientX - dragState.current.lastX;
      const dy = e.clientY - dragState.current.lastY;
      
      dragState.current.manualY += dx * 0.01;
      dragState.current.manualX += dy * 0.01;
      dragState.current.manualX = THREE.MathUtils.clamp(dragState.current.manualX, -Math.PI * 0.4, Math.PI * 0.4);
      
      dragState.current.velX = dy * 0.01;
      dragState.current.velY = dx * 0.01;
      dragState.current.lastX = e.clientX;
      dragState.current.lastY = e.clientY;
    };
    
    const onUp = () => { dragState.current.isDragging = false; };
    
    canvas.addEventListener('mousedown', onDown);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      canvas.removeEventListener('mousedown', onDown);
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, []);

  // ── 3. RENDER LOOP ──
  useFrame(() => {
    if (!rootGroup.current || !tl.current) return;
    
    const sp = scrollProgress.current.progress;
    tl.current.seek(tl.current.duration * sp);

    const ds = dragState.current;
    
    if (!ds.isDragging) {
      ds.velX *= 0.92;
      ds.velY *= 0.92;
      ds.manualX += ds.velX * 0.02;
      ds.manualY += ds.velY * 0.02;
    }

    const finalRotY = motionState.rotY + ds.manualY;
    const finalRotX = motionState.rotX + ds.manualX;
    
    camera.position.set(0, 0, THREE.MathUtils.lerp(camera.position.z, motionState.camZ, 0.1));
    camera.lookAt(0, 0, 0);
    
    rootGroup.current.rotation.set(
      THREE.MathUtils.lerp(rootGroup.current.rotation.x, finalRotX, 0.1),
      THREE.MathUtils.lerp(rootGroup.current.rotation.y, finalRotY, 0.1),
      0
    );

    // Explode logic with kinetic micro-rotations
    HARDWARE_LAYERS.forEach((layer, idx) => {
      const obj = layerRefs.current[layer.id];
      if (obj) {
        const targetZ = THREE.MathUtils.lerp(0, layer.explodeZ, motionState.explode);
        obj.position.z = THREE.MathUtils.lerp(obj.position.z, targetZ, 0.2);
        
        // Add a very subtle tumbling effect to internal parts when exploded
        if (idx > 0 && idx < HARDWARE_LAYERS.length - 1) {
          obj.rotation.z = motionState.explode * Math.PI * 0.05 * (idx % 2 === 0 ? 1 : -1);
        }
      }
    });

    // ── KINETIC DOM MUTATION ──
    const rootEl = document.getElementById('eclipse-annotations-root');
    if (rootEl) {
      const lp = motionState.labelsProgress;
      const opacity = (lp > 0.01 && !ds.isDragging) ? lp : 0;
      rootEl.style.opacity = opacity;
      rootEl.style.pointerEvents = lp > 0.9 ? 'auto' : 'none';
      
      if (opacity > 0) {
        const newLabels = [];
        const tempVec = new THREE.Vector3();
        
        HARDWARE_LAYERS.forEach((layer, idx) => {
          if (!layer.label) return;
          const obj = layerRefs.current[layer.id];
          if (obj) {
            obj.updateMatrixWorld();
            tempVec.set(0.6, 0, 0).applyMatrix4(obj.matrixWorld);
            tempVec.project(camera);
            
            const x = (tempVec.x *  .5 + .5) * size.width;
            const y = (tempVec.y * -.5 + .5) * size.height;
            
            if (x > 0 && x < size.width && y > 0 && y < size.height) {
               newLabels.push({ id: layer.id, x, y, originalIdx: idx });
            }
          }
        });
        
        // Collision avoidance
        newLabels.sort((a, b) => a.y - b.y);
        let currentY = -Infinity;
        const minSpacing = 60;

        newLabels.forEach((l, i) => {
          const isRight = l.x > size.width / 2;
          const targetY = Math.max(currentY + minSpacing, l.y - 15);
          currentY = targetY;
          const labelX = isRight ? l.x + 140 : l.x - 140;
          
          const lineEl = document.getElementById(`line-${l.id}`);
          if (lineEl) {
            const path = `M ${l.x} ${l.y} L ${l.x + (isRight ? 25 : -25)} ${l.y} L ${labelX + (isRight ? -10 : 10)} ${targetY}`;
            lineEl.setAttribute('d', path);
            
            // Kinetic SVG Drawing
            const pathLen = 200; // approx
            const drawProgress = Math.max(0, Math.min(1, lp * 1.5 - (i * 0.05))); 
            lineEl.style.strokeDasharray = pathLen;
            lineEl.style.strokeDashoffset = pathLen * (1 - drawProgress);
          }
          
          const textEl = document.getElementById(`text-${l.id}`);
          if (textEl) {
            textEl.style.left = `${labelX}px`;
            textEl.style.top = `${targetY}px`;
            textEl.style.transform = isRight ? 'translate(0, -50%)' : 'translate(-100%, -50%)';
            
            // Kinetic Text Staggering
            const textProgress = Math.max(0, Math.min(1, lp * 1.5 - (i * 0.05) - 0.2));
            textEl.style.opacity = textProgress;
            textEl.style.transform += ` translateX(${isRight ? (1 - textProgress) * -20 : (1 - textProgress) * 20}px)`;
          }

          const leftEl = document.getElementById(`text-left-${l.id}`);
          const rightEl = document.getElementById(`text-right-${l.id}`);
          if (leftEl && rightEl) {
            leftEl.style.display = isRight ? 'none' : 'block';
            rightEl.style.display = isRight ? 'block' : 'none';
          }
        });
      }
    }
  });

  return (
    <>
      <ambientLight intensity={0.5} color="#001133" />
      <directionalLight position={[6, 8, 5]} intensity={1.8} color="#ffffff" castShadow />
      <spotLight position={[-6, 4, -8]} intensity={4.5} color="#00ffff" angle={0.5} penumbra={1} />
      <spotLight position={[6, -4, 8]} intensity={3.5} color="#ff3300" angle={0.5} penumbra={1} />
      <directionalLight position={[0, -5, 2]} intensity={1.0} color="#00aaff" />

      <group ref={rootGroup}>
        {HARDWARE_LAYERS.map(layer => {
          const Component = layer.Component;
          return (
            <group key={layer.id} ref={el => layerRefs.current[layer.id] = el}>
              <Component />
            </group>
          );
        })}
      </group>

      <EffectComposer disableNormalPass multisampling={4}>
        <Bloom luminanceThreshold={0.2} luminanceSmoothing={0.9} intensity={1.5} mipmapBlur />
        <Noise opacity={0.035} />
      </EffectComposer>

      <Html fullscreen style={{ pointerEvents: 'none', zIndex: 100 }} zIndexRange={[100, 0]}>
        <div id="eclipse-annotations-root" style={{ position: 'absolute', inset: 0, opacity: 0, transition: 'opacity 0.1s', willChange: 'opacity' }}>
          <svg style={{ position: 'absolute', inset: 0, width: '100vw', height: '100vh', overflow: 'visible' }}>
            {HARDWARE_LAYERS.filter(l => l.label).map(l => (
              <path key={l.id + '_line'} id={`line-${l.id}`} fill="none" stroke="rgba(255,255,255,0.45)" strokeWidth="1.5" />
            ))}
          </svg>
          {HARDWARE_LAYERS.filter(l => l.label).map(l => (
            <div key={l.id + '_text'} id={`text-${l.id}`} style={{ position: 'absolute', color: '#fff', fontFamily: "'Inter', sans-serif", textTransform: 'uppercase', letterSpacing: '0.15em', whiteSpace: 'nowrap', willChange: 'transform, opacity' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div id={`text-left-${l.id}`} style={{ textAlign: 'right', display: 'none' }}>
                  <div style={{ fontSize: '0.65rem', fontWeight: 600, color: '#f0f0f0', letterSpacing: '0.2em' }}>{l.label.title}</div>
                  <div style={{ fontSize: '0.5rem', color: '#E07A5F', fontWeight: 500, marginTop: '4px', letterSpacing: '0.1em' }}>{l.label.spec}</div>
                </div>
                <div style={{ width: 5, height: 5, borderRadius: '50%', background: '#fff', boxShadow: '0 0 8px rgba(255,255,255,0.8)' }} />
                <div id={`text-right-${l.id}`} style={{ textAlign: 'left', display: 'none' }}>
                  <div style={{ fontSize: '0.65rem', fontWeight: 600, color: '#f0f0f0', letterSpacing: '0.2em' }}>{l.label.title}</div>
                  <div style={{ fontSize: '0.5rem', color: '#E07A5F', fontWeight: 500, marginTop: '4px', letterSpacing: '0.1em' }}>{l.label.spec}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Html>
    </>
  );
}
