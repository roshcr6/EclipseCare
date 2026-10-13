import React, { useMemo } from 'react';
import { RoundedBox, Instances, Instance, Extrude } from '@react-three/drei';
import * as THREE from 'three';

// ─────────────────────────────────────────────────────────────
// ECLIPSE HARDWARE DEFINITIONS (INDUSTRIAL PROCEDURAL GEOMETRY)
// ─────────────────────────────────────────────────────────────

// Premium physical materials
export const MATS = {
  housingMatte: new THREE.MeshStandardMaterial({
    color: '#1a1c20', metalness: 0.85, roughness: 0.3
  }),
  crystalGlass: new THREE.MeshPhysicalMaterial({
    color: '#ffffff', metalness: 0.1, roughness: 0.05,
    transmission: 0.98, ior: 1.55, thickness: 0.2, clearcoat: 1.0,
    clearcoatRoughness: 0.1
  }),
  pcbSubstrate: new THREE.MeshStandardMaterial({
    color: '#04070a', metalness: 0.3, roughness: 0.8
  }),
  copperTraces: new THREE.MeshStandardMaterial({
    color: '#b87333', metalness: 1.0, roughness: 0.4
  }),
  icPackage: new THREE.MeshStandardMaterial({
    color: '#0d0d0d', metalness: 0.6, roughness: 0.5
  }),
  smdCapacitor: new THREE.MeshStandardMaterial({
    color: '#c2b280', metalness: 0.3, roughness: 0.4
  }),
  batteryFoil: new THREE.MeshStandardMaterial({
    color: '#2a2d33', metalness: 0.6, roughness: 0.7
  }),
  opticalBlack: new THREE.MeshStandardMaterial({
    color: '#030303', metalness: 0.9, roughness: 0.1
  }),
  sensorWindow: new THREE.MeshPhysicalMaterial({
    color: '#000000', metalness: 0.9, roughness: 0.0,
    transmission: 1.0, ior: 1.5, clearcoat: 1.0
  }),
  hapticMetal: new THREE.MeshStandardMaterial({
    color: '#2d2f33', metalness: 0.9, roughness: 0.4
  }),
  goldPlating: new THREE.MeshStandardMaterial({
    color: '#d4af37', metalness: 1.0, roughness: 0.2
  }),
  siliconeBand: new THREE.MeshStandardMaterial({
    color: '#121418', metalness: 0.1, roughness: 0.85
  })
};

// ── 1. FRONT CRYSTAL / OUTER HOUSING ──
export function OuterHousing() {
  return (
    <group>
      <RoundedBox args={[1.6, 2.3, 0.15]} radius={0.3} smoothness={32} position={[0, 0, 0.4]}>
        <primitive object={MATS.crystalGlass} attach="material" />
      </RoundedBox>
      <mesh position={[0, 0, 0.3]}>
        <boxGeometry args={[1.56, 2.26, 0.08]} />
        <primitive object={MATS.housingMatte} attach="material" />
      </mesh>
      <mesh position={[0, 1.1, 0.3]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.02, 0.02, 1.0, 16]} />
        <meshStandardMaterial color="#333" metalness={0.9} roughness={0.2} />
      </mesh>
    </group>
  );
}

// ── 2. MAIN LOGIC BOARD (PCB) ──
export function MainLogicBoard() {
  const pcbShape = useMemo(() => {
    const s = new THREE.Shape();
    s.moveTo(-0.6, 0.9);
    s.lineTo(0.6, 0.9);
    s.lineTo(0.7, 0.7);
    s.lineTo(0.7, -0.7);
    s.lineTo(0.5, -0.9);
    s.lineTo(-0.5, -0.9);
    s.lineTo(-0.7, -0.7);
    s.lineTo(-0.7, 0.7);
    s.lineTo(-0.6, 0.9);
    return s;
  }, []);

  const traces = useMemo(() => {
    const arr = [];
    for (let i = 0; i < 300; i++) {
      const isVert = Math.random() > 0.5;
      const isData = Math.random() > 0.85;
      arr.push({
        pos: [(Math.random() - 0.5) * 1.2, (Math.random() - 0.5) * 1.6, 0.035],
        scale: isVert ? [0.005, Math.random() * 0.2 + 0.05, 0.002] : [Math.random() * 0.2 + 0.05, 0.005, 0.002],
        isData
      });
    }
    return arr;
  }, []);

  const extrudeSettings = { depth: 0.03, bevelEnabled: true, bevelSegments: 2, steps: 1, bevelSize: 0.01, bevelThickness: 0.01 };

  return (
    <group position={[0, 0, 0.15]}>
      <mesh>
        <extrudeGeometry args={[pcbShape, extrudeSettings]} />
        <primitive object={MATS.pcbSubstrate} attach="material" />
      </mesh>
      
      {/* Copper Traces */}
      <Instances range={traces.filter(t => !t.isData).length} limit={traces.length}>
        <boxGeometry args={[1, 1, 1]} />
        <primitive object={MATS.copperTraces} attach="material" />
        {traces.filter(t => !t.isData).map((t, i) => (
          <Instance key={i} position={t.pos} scale={t.scale} />
        ))}
      </Instances>

      {/* Glowing Data Traces */}
      <Instances range={traces.filter(t => t.isData).length} limit={traces.length}>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial color="#00ffff" emissive="#00ffff" emissiveIntensity={2.5} toneMapped={false} />
        {traces.filter(t => t.isData).map((t, i) => (
          <Instance key={i} position={t.pos} scale={t.scale} />
        ))}
      </Instances>

      <mesh position={[0, -0.85, 0.02]}>
        <boxGeometry args={[0.4, 0.08, 0.04]} />
        <primitive object={MATS.goldPlating} attach="material" />
      </mesh>
    </group>
  );
}

// ── 3. MAIN CONTROL MCU ──
export function ControlMCU() {
  const smds = useMemo(() => {
    const arr = [];
    for(let i=0; i<40; i++) {
      const angle = Math.random() * Math.PI * 2;
      const rad = 0.35 + Math.random() * 0.2;
      arr.push({
        pos: [Math.cos(angle) * rad, Math.sin(angle) * rad, 0.01],
        rot: [0, 0, Math.random() > 0.5 ? 0 : Math.PI/2]
      });
    }
    return arr;
  }, []);

  return (
    <group position={[0, 0.3, 0.2]}>
      <mesh>
        <boxGeometry args={[0.45, 0.45, 0.04]} />
        <primitive object={MATS.icPackage} attach="material" />
      </mesh>
      <mesh position={[0, 0, 0.015]}>
        <boxGeometry args={[0.3, 0.3, 0.02]} />
        <meshStandardMaterial color="#0a0a0a" metalness={0.9} roughness={0.2} />
      </mesh>
      <Instances range={smds.length} limit={smds.length}>
        <boxGeometry args={[0.02, 0.04, 0.02]} />
        <primitive object={MATS.smdCapacitor} attach="material" />
        {smds.map((s, i) => (
          <Instance key={i} position={s.pos} rotation={s.rot} />
        ))}
      </Instances>
      <mesh position={[0.4, 0.1, 0.01]}>
        <boxGeometry args={[0.12, 0.3, 0.03]} />
        <meshStandardMaterial color="#ddd" roughness={0.2} metalness={0.8} />
      </mesh>
      <mesh position={[0.4, 0.1, 0.026]}>
        <boxGeometry args={[0.08, 0.2, 0.005]} />
        <primitive object={MATS.goldPlating} attach="material" />
      </mesh>
    </group>
  );
}

// ── 4. TRI-AXIAL ACCELEROMETER ──
export function Accelerometer() {
  return (
    <group position={[-0.35, -0.2, 0.2]}>
      <mesh>
        <boxGeometry args={[0.15, 0.15, 0.03]} />
        <primitive object={MATS.icPackage} attach="material" />
      </mesh>
      <mesh position={[0, 0, 0.016]}>
        <ringGeometry args={[0.02, 0.04, 16]} />
        <meshStandardMaterial color="#333" />
      </mesh>
    </group>
  );
}

// ── 5. SKIN TEMPERATURE SENSOR ──
export function TemperatureSensor() {
  return (
    <group position={[0.35, -0.5, 0.2]}>
      <mesh>
        <cylinderGeometry args={[0.06, 0.06, 0.04, 16]} rotation-x={Math.PI / 2} />
        <primitive object={MATS.goldPlating} attach="material" />
      </mesh>
      <mesh position={[0, 0, 0.021]}>
        <cylinderGeometry args={[0.04, 0.04, 0.01, 16]} rotation-x={Math.PI / 2} />
        <meshStandardMaterial color="#111" />
      </mesh>
    </group>
  );
}

// ── 6. BATTERY CELL ──
export function BatteryCell() {
  return (
    <group position={[0, 0, -0.1]}>
      <RoundedBox args={[1.3, 1.6, 0.12]} radius={0.08} smoothness={8}>
        <primitive object={MATS.batteryFoil} attach="material" />
      </RoundedBox>
      <mesh position={[0, 0, 0.061]}>
        <planeGeometry args={[1.0, 1.3]} />
        <meshStandardMaterial color="#3a3e45" metalness={0.2} roughness={0.9} />
      </mesh>
      <mesh position={[0.2, 0.85, 0.02]}>
        <boxGeometry args={[0.12, 0.15, 0.01]} />
        <meshStandardMaterial color="#111" roughness={0.9} />
      </mesh>
    </group>
  );
}

// ── 7. HAPTIC MODULE ──
export function HapticModule() {
  return (
    <group position={[0, -0.85, -0.1]}>
      <RoundedBox args={[0.9, 0.25, 0.1]} radius={0.05} smoothness={4}>
        <primitive object={MATS.hapticMetal} attach="material" />
      </RoundedBox>
      <mesh position={[0, 0, 0.05]} rotation-z={Math.PI / 2} rotation-x={Math.PI / 2}>
        <cylinderGeometry args={[0.08, 0.08, 0.8, 16]} />
        <meshStandardMaterial color="#1f2124" metalness={1.0} roughness={0.2} />
      </mesh>
    </group>
  );
}

// ── 8. CHARGING SYSTEM (COIL) ──
export function ChargingCoil() {
  return (
    <group position={[0, 0, -0.25]}>
      <mesh>
        <cylinderGeometry args={[0.7, 0.7, 0.02, 32]} rotation-x={Math.PI / 2} />
        <meshStandardMaterial color="#080808" />
      </mesh>
      <mesh position={[0, 0, 0.01]}>
        <torusGeometry args={[0.65, 0.03, 16, 64]} />
        <meshStandardMaterial color="#222" metalness={0.9} roughness={0.3} />
      </mesh>
      {Array.from({ length: 6 }).map((_, i) => (
        <mesh key={i} position={[0, 0, 0.015]}>
          <ringGeometry args={[0.3 + i * 0.05, 0.33 + i * 0.05, 64]} />
          {i === 2 || i === 4 ? (
             <meshStandardMaterial color="#ff5500" emissive="#ff3300" emissiveIntensity={2.0} toneMapped={false} />
          ) : (
             <primitive object={MATS.copperTraces} attach="material" />
          )}
        </mesh>
      ))}
    </group>
  );
}

// ── 9. REAR SENSOR ASSEMBLY (PPG / OPTICAL) ──
export function RearSensorAssembly() {
  return (
    <group position={[0, 0, -0.35]}>
      <RoundedBox args={[1.56, 2.26, 0.1]} radius={0.25} smoothness={16} position={[0, 0, -0.05]}>
        <primitive object={MATS.housingMatte} attach="material" />
      </RoundedBox>
      <mesh position={[0, 0, -0.1]}>
        <torusGeometry args={[0.55, 0.05, 16, 64]} />
        <meshStandardMaterial color="#111" metalness={0.8} />
      </mesh>
      <mesh position={[0, 0, -0.11]}>
        <cylinderGeometry args={[0.54, 0.54, 0.02, 32]} rotation-x={Math.PI / 2} />
        <primitive object={MATS.opticalBlack} attach="material" />
      </mesh>
      <mesh position={[0, 0, -0.12]}>
        <cylinderGeometry args={[0.54, 0.54, 0.02, 32]} rotation-x={Math.PI / 2} />
        <primitive object={MATS.sensorWindow} attach="material" />
      </mesh>
      {[
        [-0.2, 0.2], [0.2, 0.2], [-0.2, -0.2], [0.2, -0.2]
      ].map(([x, y], i) => (
        <mesh key={i} position={[x, y, -0.115]}>
          <boxGeometry args={[0.1, 0.1, 0.01]} />
          <meshStandardMaterial color={i % 2 === 0 ? "#00ff33" : "#ff0000"} emissive={i % 2 === 0 ? "#00ff55" : "#ff3300"} emissiveIntensity={3.0} toneMapped={false} metalness={0.8} />
        </mesh>
      ))}
      <mesh position={[0, 0, -0.115]}>
        <cylinderGeometry args={[0.15, 0.15, 0.01, 32]} rotation-x={Math.PI / 2} />
        <meshStandardMaterial color="#000" metalness={0.9} roughness={0.1} />
      </mesh>
    </group>
  );
}

// ── 10. BAND ──
export function SiliconeBand() {
  return (
    <group position={[0, 0, -0.15]}>
      <mesh position={[0, 2.2, 0]} rotation-x={-0.1}>
        <boxGeometry args={[1.3, 2.2, 0.12]} />
        <primitive object={MATS.siliconeBand} attach="material" />
      </mesh>
      <mesh position={[0, -2.2, 0]} rotation-x={0.1}>
        <boxGeometry args={[1.3, 2.2, 0.12]} />
        <primitive object={MATS.siliconeBand} attach="material" />
      </mesh>
    </group>
  );
}

// ── 11. BLE / UWB ANTENNA ARRAY ──
export function AntennaArray() {
  return (
    <group position={[0, 0, 0.35]}>
      <mesh>
        <torusGeometry args={[0.72, 0.015, 16, 64]} />
        <meshStandardMaterial color="#00ffcc" emissive="#00ffcc" emissiveIntensity={1.5} toneMapped={false} />
      </mesh>
      <mesh position={[0.5, 0.5, 0.01]}>
        <boxGeometry args={[0.08, 0.04, 0.02]} />
        <primitive object={MATS.icPackage} attach="material" />
      </mesh>
      <mesh position={[-0.5, -0.5, 0.01]}>
        <boxGeometry args={[0.08, 0.04, 0.02]} />
        <primitive object={MATS.icPackage} attach="material" />
      </mesh>
    </group>
  );
}

// ── 12. SECURE ENCLAVE ──
export function SecureEnclave() {
  return (
    <group position={[0.25, 0.3, 0.2]}>
      <mesh>
        <boxGeometry args={[0.2, 0.2, 0.03]} />
        <primitive object={MATS.icPackage} attach="material" />
      </mesh>
      <mesh position={[0, 0, 0.016]}>
        <planeGeometry args={[0.15, 0.15]} />
        <meshStandardMaterial color="#222" metalness={0.9} />
      </mesh>
      <mesh position={[0, 0, 0.017]}>
        <ringGeometry args={[0.03, 0.04, 16]} />
        <meshStandardMaterial color="#ff0055" emissive="#ff0055" emissiveIntensity={2.0} toneMapped={false} />
      </mesh>
    </group>
  );
}

// ── 13. NFC COIL ──
export function NFCCoil() {
  return (
    <group position={[0, 0, -0.2]}>
      <mesh>
        <ringGeometry args={[0.45, 0.55, 64]} />
        <meshStandardMaterial color="#ffd700" emissive="#442200" metalness={1.0} roughness={0.3} />
      </mesh>
      <mesh position={[0, 0, 0.001]}>
         <ringGeometry args={[0.46, 0.47, 64]} />
         <meshStandardMaterial color="#ff9900" emissive="#ff6600" emissiveIntensity={1.5} toneMapped={false} />
      </mesh>
    </group>
  );
}

// ── 14. MEMS MICROPHONE ──
export function MEMSMicrophone() {
  return (
    <group position={[-0.45, 0.7, 0.2]}>
      <mesh>
        <boxGeometry args={[0.08, 0.08, 0.04]} />
        <meshStandardMaterial color="#d4af37" metalness={1.0} roughness={0.2} />
      </mesh>
      <mesh position={[0, 0, 0.021]}>
        <cylinderGeometry args={[0.015, 0.015, 0.005, 16]} rotation-x={Math.PI / 2} />
        <meshStandardMaterial color="#000" />
      </mesh>
    </group>
  );
}

// ── SYSTEM ARCHITECTURE HIERARCHY MAP ──
export const HARDWARE_LAYERS = [
  { id: 'front-shell',    Component: OuterHousing,       explodeZ: 5.5,  label: null },
  { id: 'antenna',        Component: AntennaArray,       explodeZ: 4.5,  label: { title: "BLE / UWB ANTENNA", spec: "SPATIAL AWARENESS" } },
  { id: 'mcu',            Component: ControlMCU,         explodeZ: 3.5,  label: { title: "MAIN CONTROL MCU", spec: "BLE / LOCAL PROCESSING" } },
  { id: 'secure-enclave', Component: SecureEnclave,      explodeZ: 2.7,  label: { title: "SECURE ENCLAVE", spec: "BIOMETRIC CRYPTOGRAPHY" } },
  { id: 'mems-mic',       Component: MEMSMicrophone,     explodeZ: 2.0,  label: { title: "MEMS MICROPHONE", spec: "ACOUSTIC ANALYSIS" } },
  { id: 'accelerometer',  Component: Accelerometer,      explodeZ: 1.5,  label: { title: "TRI-AXIAL ACCELEROMETER", spec: "MOTION / ADL TRACKING" } },
  { id: 'temp-sensor',    Component: TemperatureSensor,  explodeZ: 0.8,  label: { title: "SKIN TEMPERATURE SENSOR", spec: "BASELINE TEMPERATURE" } },
  { id: 'pcb',            Component: MainLogicBoard,     explodeZ: 0.0,  label: { title: "MAIN LOGIC BOARD", spec: "FR4 SUBSTRATE" } },
  { id: 'battery',        Component: BatteryCell,        explodeZ: -1.0, label: { title: "BATTERY CELL", spec: "POLYMER LITHIUM" } },
  { id: 'haptic',         Component: HapticModule,       explodeZ: -2.0, label: { title: "HAPTIC MODULE", spec: "LINEAR RESONANT" } },
  { id: 'nfc',            Component: NFCCoil,            explodeZ: -2.8, label: { title: "NFC COIL", spec: "SECURE ACCESS" } },
  { id: 'charging',       Component: ChargingCoil,       explodeZ: -3.5, label: { title: "CHARGING SYSTEM", spec: "INDUCTIVE COIL" } },
  { id: 'rear-sensor',    Component: RearSensorAssembly, explodeZ: -4.5, label: { title: "OPTICAL PPG SENSOR", spec: "HEART RATE / SpO₂" } },
  { id: 'band',           Component: SiliconeBand,       explodeZ: -5.5, label: null },
];
