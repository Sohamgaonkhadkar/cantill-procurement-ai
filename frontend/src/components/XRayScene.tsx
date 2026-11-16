import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { RoundedBox } from "@react-three/drei";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type MutableRefObject,
} from "react";
import * as THREE from "three";
import { getDeviceTier, prefersReducedMotion } from "@/lib/config";

export type XPlate = { title: string; value: string; sub: string };
export type ViewState = { yaw: number; pitch: number };

type Props = {
  plates: XPlate[];
  selected: number;
  route: "direct" | "sourcing" | null;
  view: MutableRefObject<ViewState>;
  onSelect: (i: number) => void;
  runId: number;
};

export const LAYER_COLORS = [
  "#76A0F4",
  "#82929A",
  "#D8DEDD",
  "#68B8B4",
  "#A9C5FA",
  "#D8A58D",
  "#76A0F4",
];
const SPACING = 1.12;

function segment(mesh: THREE.Mesh, a: THREE.Vector3, b: THREE.Vector3) {
  const dir = new THREE.Vector3().subVectors(b, a);
  const len = dir.length();
  mesh.position.copy(a).add(b).multiplyScalar(0.5);
  mesh.quaternion.setFromUnitVectors(
    new THREE.Vector3(0, 1, 0),
    dir.normalize(),
  );
  mesh.scale.set(1, Math.max(len, 0.0001), 1);
}

function gridTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 512;
  const ctx = c.getContext("2d")!;
  ctx.clearRect(0, 0, 512, 512);
  ctx.strokeStyle = "rgba(183,179,215,0.22)";
  ctx.lineWidth = 2;
  for (let i = 0; i <= 512; i += 64) {
    ctx.beginPath();
    ctx.moveTo(i, 0);
    ctx.lineTo(i, 512);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(0, i);
    ctx.lineTo(512, i);
    ctx.stroke();
  }
  ctx.strokeStyle = "rgba(215,255,63,0.5)";
  ctx.lineWidth = 4;
  ctx.strokeRect(2, 2, 508, 508);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function Stack({ plates, selected, route, view, onSelect, runId }: Props) {
  const root = useRef<THREE.Group>(null);
  const layers = useRef<(THREE.Group | null)[]>([]);
  const plateMats = useRef<THREE.MeshPhysicalMaterial[]>([]);
  const chain = useRef<THREE.Mesh[]>([]);
  const branchA = useRef<THREE.Mesh>(null);
  const branchB = useRef<THREE.Mesh>(null);
  const pulses = useRef<THREE.Mesh[]>([]);
  const progress = useRef(0);
  const reduce = useMemo(() => prefersReducedMotion(), []);

  const plateGeo = useMemo(() => new THREE.BoxGeometry(4.4, 0.03, 2.5), []);
  const gridTex = useMemo(() => gridTexture(), []);
  const gridMat = useMemo(
    () =>
      new THREE.MeshBasicMaterial({
        map: gridTex,
        transparent: true,
        opacity: 0.55,
        depthWrite: false,
      }),
    [gridTex],
  );
  const segGeo = useMemo(() => new THREE.BoxGeometry(0.012, 1, 0.012), []);
  const pulseGeo = useMemo(() => new THREE.SphereGeometry(0.05, 12, 12), []);

  useEffect(() => {
    progress.current = 0;
  }, [runId]);

  const invalidate = useThree((state) => state.invalidate);
  const remainingFrames = useRef(120);
  useEffect(() => {
    const refresh = () => {
      remainingFrames.current = 120;
      invalidate();
    };
    refresh();
    window.addEventListener("corvo:xray-interaction", refresh);
    return () => window.removeEventListener("corvo:xray-interaction", refresh);
  }, [selected, runId, invalidate]);
  useFrame((state, dt) => {
    if (remainingFrames.current > 0) {
      remainingFrames.current--;
      state.invalidate();
    }
    progress.current = Math.min(
      1,
      progress.current + dt * (reduce ? 10 : 0.55),
    );
    const p = progress.current;
    const e = 1 - Math.pow(1 - p, 3);

    if (root.current) {
      const targetY =
        -(((plates.length - 1) / 2 - selected) * SPACING * e) * 0.6;
      root.current.position.y += (targetY - root.current.position.y) * 0.08;
      root.current.rotation.y +=
        (view.current.yaw - root.current.rotation.y) * 0.09;
      root.current.rotation.x +=
        (view.current.pitch - root.current.rotation.x) * 0.09;
    }

    layers.current.forEach((g, i) => {
      if (!g) return;
      const isSel = i === selected;
      const align = (1 - e) * (i % 2 === 0 ? 0.55 : -0.45);
      const tx = align + (isSel ? 0 : 0);
      const tz = isSel ? 0.7 : -0.35 * Math.abs(i - selected) * 0.5;
      g.position.set(
        g.position.x + (tx - g.position.x) * 0.1,
        ((plates.length - 1) / 2 - i) * SPACING * e,
        g.position.z + (tz - g.position.z) * 0.1,
      );
      const m = plateMats.current[i];
      if (m) {
        m.opacity += ((isSel ? 0.62 : 0.2) - m.opacity) * 0.12;
        m.emissiveIntensity +=
          ((isSel ? 0.45 : 0.06) - m.emissiveIntensity) * 0.12;
      }
    });

    // connections between layers — lit when they touch the selected layer
    const pos = (i: number) =>
      layers.current[i]?.position ?? new THREE.Vector3();
    chain.current.forEach((m, i) => {
      if (!m) return;
      const a = pos(i).clone();
      const b = pos(i + 1).clone();
      segment(m, a, b);
      const mat = m.material as THREE.MeshBasicMaterial;
      const lit = i === selected - 1 || i === selected;
      mat.opacity += ((lit ? 0.95 : 0.22) - mat.opacity) * 0.12;
      mat.color.set(lit ? "#A9C5FA" : "#82929A");
    });

    // route split after the last layer
    const last = pos(plates.length - 1).clone();
    const endA = new THREE.Vector3(last.x + 2.9, last.y + 1.25, last.z - 0.2);
    const endB = new THREE.Vector3(last.x + 2.9, last.y - 1.35, last.z + 0.3);
    if (branchA.current) {
      segment(branchA.current, last, endA);
      const mat = branchA.current.material as THREE.MeshBasicMaterial;
      const on = route === "direct";
      mat.opacity +=
        ((on ? 1 : route === null ? 0.12 : 0.1) - mat.opacity) * 0.1;
      mat.color.set("#68B8B4");
    }
    if (branchB.current) {
      segment(branchB.current, last, endB);
      const mat = branchB.current.material as THREE.MeshBasicMaterial;
      const on = route === "sourcing";
      mat.opacity +=
        ((on ? 1 : route === null ? 0.12 : 0.1) - mat.opacity) * 0.1;
      mat.color.set(on ? "#D8A58D" : "#D8DEDD");
    }

    // pulses travel the chain once the layers have aligned
    pulses.current.forEach((m, k) => {
      if (!m) return;
      const u = (k * 0.33) % 1;
      const f = u * (plates.length - 1);
      const i0 = Math.min(plates.length - 2, Math.floor(f));
      const frac = f - i0;
      const a = pos(i0);
      const b = pos(i0 + 1);
      m.position.lerpVectors(a, b, frac);
      m.visible = p > 0.85;
      m.scale.setScalar(0.9 + Math.sin(u * Math.PI) * 0.8);
    });
  });

  return (
    <group ref={root}>
      {plates.map((plate, i) => (
        <group
          key={plate.title}
          ref={(g) => {
            layers.current[i] = g;
          }}
          position={[0, 0, 0]}
        >
          <RoundedBox
            args={[4.4, 0.035, 2.5]}
            radius={0.03}
            smoothness={3}
            onClick={(e) => {
              e.stopPropagation();
              onSelect(i);
            }}
            onPointerOver={() => (document.body.style.cursor = "pointer")}
            onPointerOut={() => (document.body.style.cursor = "")}
          >
            <meshPhysicalMaterial
              ref={(m: THREE.MeshPhysicalMaterial | null) => {
                if (m) plateMats.current[i] = m;
              }}
              color="#141a42"
              transparent
              opacity={0.2}
              roughness={0.18}
              metalness={0.2}
              clearcoat={1}
              emissive={LAYER_COLORS[i]}
              emissiveIntensity={0.06}
            />
          </RoundedBox>
          <mesh
            geometry={plateGeo}
            material={gridMat}
            position={[0, 0.021, 0]}
            rotation={[0, 0, 0]}
            scale={[1, 1, 1]}
          />
          <mesh position={[0, 0.03, 0]} rotation={[-Math.PI / 2, 0, 0]}>
            <planeGeometry args={[4.4, 2.5]} />
            <meshBasicMaterial transparent opacity={0} />
          </mesh>
          {/* Plate labels are rendered as a DOM overlay by DecisionXray so that
              unmounting the canvas cannot race with portal cleanup. */}
        </group>
      ))}

      {Array.from({ length: plates.length - 1 }, (_, i) => i).map((i) => (
        <mesh
          key={`c${i}`}
          ref={(m) => {
            if (m) chain.current[i] = m;
          }}
          geometry={segGeo}
          renderOrder={4}
        >
          <meshBasicMaterial
            color="#82929A"
            transparent
            opacity={0.22}
            toneMapped={false}
          />
        </mesh>
      ))}
      <mesh ref={branchA} geometry={segGeo} renderOrder={4}>
        <meshBasicMaterial
          color="#68B8B4"
          transparent
          opacity={0.1}
          toneMapped={false}
        />
      </mesh>
      <mesh ref={branchB} geometry={segGeo} renderOrder={4}>
        <meshBasicMaterial
          color="#D8DEDD"
          transparent
          opacity={0.1}
          toneMapped={false}
        />
      </mesh>
      {[0, 1, 2].map((k) => (
        <mesh
          key={`p${k}`}
          geometry={pulseGeo}
          ref={(m) => {
            if (m) pulses.current[k] = m;
          }}
        >
          <meshBasicMaterial color="#A9C5FA" toneMapped={false} />
        </mesh>
      ))}
    </group>
  );
}

export function XRayScene(props: Props) {
  const tier = useMemo(() => getDeviceTier(), []);
  const root = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(true);
  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) =>
      setVisible(entry.isIntersecting),
    );
    if (root.current) observer.observe(root.current);
    return () => observer.disconnect();
  }, []);
  return (
    <div ref={root} className="absolute inset-0">
      <Canvas
        frameloop={visible ? "demand" : "never"}
        dpr={tier === "high" ? [1, 1.6] : [1, 1.2]}
        camera={{ position: [0, 3.9, 8.6], fov: 30 }}
        gl={{ antialias: tier !== "mobile", alpha: true }}
      >
        <ambientLight intensity={0.6} />
        <pointLight
          position={[3, 5, 4]}
          intensity={18}
          color="#ffffff"
          distance={18}
        />
        <Stack {...props} />
      </Canvas>
    </div>
  );
}
