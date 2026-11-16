import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Line } from "@react-three/drei";
import { Bloom, EffectComposer } from "@react-three/postprocessing";
import { useEffect, useMemo, useRef, type MutableRefObject } from "react";
import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { getDeviceTier, prefersReducedMotion } from "@/lib/config";

export const STAGES = [
  {
    key: "INTAKE",
    ring: 0,
    note: "Requests arrive from Request Studio, CSV batches and ERP extracts.",
  },
  {
    key: "RESOLVE",
    ring: 0,
    note: "Descriptions are matched to catalog codes with a visible confidence and evidence trail.",
  },
  {
    key: "GROUP",
    ring: 1,
    note: "Compatible lines merge into requirements; separations keep their reasons.",
  },
  {
    key: "POLICY",
    ring: 2,
    note: "Versioned rules evaluate in priority order. The first match decides.",
  },
  {
    key: "ROUTE",
    ring: 1,
    note: "The machine splits into a direct purchase order or a sourcing event.",
  },
] as const;

const LIME_C = new THREE.Color("#d7ff3f");
const VIOLET_C = new THREE.Color("#6246ff");

/* ---------- Procedural atmosphere: grain, light scatter, soft lens warp near the core ---------- */

const atmosphereVert = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const atmosphereFrag = /* glsl */ `
  uniform float uTime;
  uniform vec2 uPointer;
  uniform float uEnergy;
  varying vec2 vUv;

  float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float noise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
  }

  void main() {
    vec2 uv = vUv;
    vec2 p = uv - 0.5;
    p.x *= 1.6;
    vec2 m = uPointer * 0.5 + 0.5;
    vec2 toCore = uv - vec2(0.5, 0.5);
    float d = length(toCore);
    uv += toCore * exp(-d * 4.0) * 0.03 * sin(uTime * 0.6 + d * 12.0);

    float n = noise(uv * 3.0 + vec2(uTime * 0.04, -uTime * 0.02));
    float n2 = noise(uv * 9.0 - uTime * 0.05);
    vec3 base = vec3(0.031, 0.043, 0.122);
    vec3 violet = vec3(0.384, 0.274, 1.0);
    vec3 coral = vec3(1.0, 0.4, 0.31);
    vec3 mint = vec3(0.196, 0.902, 0.824);

    float glow = exp(-length(p) * 2.6) * (0.5 + uEnergy * 0.3);
    vec3 col = base;
    col += violet * glow * 0.5;
    col += violet * smoothstep(0.55, 0.0, length(p - vec2(0.45, -0.25))) * 0.1 * (0.6 + n);
    col += coral * smoothstep(0.7, 0.0, length(vUv - vec2(0.05, 0.98))) * 0.06;
    col += mint * smoothstep(0.35, 0.0, abs(vUv.y - 0.5 + sin(vUv.x * 6.0 + uTime * 0.4) * 0.05)) * 0.03;

    float cd = length(vUv - m);
    float shift = 0.0025 * exp(-cd * 6.0);
    col.r += shift * 8.0 * violet.r;
    col.b -= shift * 6.0;

    float g = hash(gl_FragCoord.xy + fract(uTime) * 100.0) - 0.5;
    col += g * 0.016;
    col *= 0.86 + n2 * 0.1;
    // Local, translucent glow. A full-alpha plane hides the photograph even
    // when the WebGL renderer itself has a transparent clear colour.
    float feather = 1.0 - smoothstep(0.12, 0.55, length(vUv - 0.5));
    gl_FragColor = vec4(col * 0.62, feather * 0.18);
  }
`;

function Atmosphere({
  pointer,
  reduce,
}: {
  pointer: MutableRefObject<THREE.Vector2>;
  reduce: boolean;
}) {
  const mat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: atmosphereVert,
        fragmentShader: atmosphereFrag,
        uniforms: {
          uTime: { value: 0 },
          uPointer: { value: new THREE.Vector2() },
          uEnergy: { value: 0.5 },
        },
        depthWrite: false,
        transparent: true,
        blending: THREE.NormalBlending,
      }),
    [],
  );
  const { viewport } = useThree();
  useFrame((state) => {
    mat.uniforms.uTime.value = reduce ? 0 : state.clock.elapsedTime;
    (mat.uniforms.uPointer.value as THREE.Vector2).lerp(pointer.current, 0.05);
  });
  return (
    <mesh position={[0, 0, -9]} material={mat} renderOrder={-1}>
      <planeGeometry args={[viewport.width * 3, viewport.height * 3]} />
    </mesh>
  );
}

/* ---------- Receding procedural grid ---------- */

const gridVert = /* glsl */ `
  varying vec3 vWorld;
  void main() {
    vec4 w = modelMatrix * vec4(position, 1.0);
    vWorld = w.xyz;
    gl_Position = projectionMatrix * viewMatrix * w;
  }
`;
const gridFrag = /* glsl */ `
  varying vec3 vWorld;
  uniform float uTime;
  void main() {
    vec2 g = vWorld.xz / 1.2;
    vec2 gr = abs(fract(g - 0.5) - 0.5) / fwidth(g);
    float line = 1.0 - min(min(gr.x, gr.y), 1.0);
    float fade = smoothstep(12.0, 2.0, length(vWorld.xz));
    float pulse = 0.6 + 0.4 * sin(uTime * 0.7 - length(vWorld.xz) * 0.6);
    vec3 col = vec3(0.384, 0.274, 1.0) * pulse;
    gl_FragColor = vec4(col, line * fade * 0.32);
  }
`;

function Grid({ reduce }: { reduce: boolean }) {
  const mat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: gridVert,
        fragmentShader: gridFrag,
        uniforms: { uTime: { value: 0 } },
        transparent: true,
        depthWrite: false,
      }),
    [],
  );
  useFrame((s) => {
    mat.uniforms.uTime.value = reduce ? 0 : s.clock.elapsedTime;
  });
  return (
    <mesh
      rotation={[-Math.PI / 2, 0, 0]}
      position={[0, -2.6, 0]}
      material={mat}
    >
      <planeGeometry args={[30, 30]} />
    </mesh>
  );
}

/* ---------- Core glow ---------- */

function glowTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 256;
  const ctx = c.getContext("2d")!;
  const g = ctx.createRadialGradient(128, 128, 0, 128, 128, 128);
  g.addColorStop(0, "rgba(143,123,255,0.95)");
  g.addColorStop(0.25, "rgba(98,70,255,0.45)");
  g.addColorStop(0.6, "rgba(98,70,255,0.08)");
  g.addColorStop(1, "rgba(98,70,255,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 256, 256);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

const coreVert = /* glsl */ `
  varying vec3 vN;
  varying vec3 vV;
  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    vN = normalize(normalMatrix * normal);
    vV = normalize(-mv.xyz);
    gl_Position = projectionMatrix * mv;
  }
`;
const coreFrag = /* glsl */ `
  varying vec3 vN;
  varying vec3 vV;
  uniform float uTime;
  uniform float uHot;
  void main() {
    float fres = pow(1.0 - abs(dot(normalize(vN), normalize(vV))), 2.2);
    vec3 violet = vec3(0.384, 0.274, 1.0);
    vec3 lav = vec3(0.718, 0.702, 0.843);
    vec3 hot = vec3(0.84, 1.0, 0.25);
    float pulse = 0.85 + 0.15 * sin(uTime * 2.2);
    vec3 col = mix(violet * 0.45, lav, fres) * pulse;
    col += hot * uHot * 0.35 * fres;
    gl_FragColor = vec4(col, 0.92);
  }
`;

/* ---------- The machine ---------- */

export type CoreProps = {
  activeStage: number | null;
  onHoverStage: (i: number | null) => void;
  onSelectStage: (i: number) => void;
  onCoreClick: () => void;
};

const RING_R = [2.35, 1.82, 1.32] as const;

type MachineProps = CoreProps & {
  pointer: MutableRefObject<THREE.Vector2>;
  reduce: boolean;
  tier: "high" | "low" | "mobile";
};

function Machine({
  activeStage,
  onHoverStage,
  onSelectStage,
  onCoreClick,
  pointer,
  reduce,
  tier,
}: MachineProps) {
  const group = useRef<THREE.Group>(null);
  const ring0 = useRef<THREE.Group>(null);
  const ring1 = useRef<THREE.Group>(null);
  const ring2 = useRef<THREE.Group>(null);
  const channelMats = useRef<THREE.MeshBasicMaterial[]>([]);
  const pulses = useRef<THREE.Mesh[]>([]);
  const seg = tier === "mobile" ? 48 : 110;

  const coreMat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: coreVert,
        fragmentShader: coreFrag,
        uniforms: { uTime: { value: 0 }, uHot: { value: 0.25 } },
        transparent: true,
      }),
    [],
  );
  const glowMat = useMemo(
    () =>
      new THREE.SpriteMaterial({
        map: glowTexture(),
        color: "#8f7bff",
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        opacity: 0.85,
      }),
    [],
  );
  const coreGeo = useMemo(
    () => new THREE.IcosahedronGeometry(0.62, tier === "mobile" ? 2 : 4),
    [tier],
  );
  const wireGeo = useMemo(() => new THREE.IcosahedronGeometry(0.86, 1), []);
  const ringGeo = useMemo(
    () =>
      RING_R.map(
        (r, i) => new THREE.TorusGeometry(r, [0.09, 0.075, 0.06][i], 24, seg),
      ),
    [seg],
  );
  const channelGeo = useMemo(
    () =>
      RING_R.map(
        (r, i) => new THREE.TorusGeometry(r, [0.012, 0.01, 0.009][i], 8, seg),
      ),
    [seg],
  );
  const glassGeo = useMemo(
    () => RING_R.map((r) => new THREE.TorusGeometry(r, 0.03, 16, seg)),
    [seg],
  );
  const clampGeo = useMemo(() => new THREE.BoxGeometry(0.2, 0.12, 0.14), []);
  const nodeGeo = useMemo(() => new THREE.SphereGeometry(0.07, 20, 20), []);
  const pulseGeo = useMemo(() => new THREE.SphereGeometry(0.04, 10, 10), []);

  const ringMat = useMemo(
    () =>
      new THREE.MeshPhysicalMaterial({
        color: "#c7c9d9",
        metalness: 1,
        roughness: 0.26,
        clearcoat: 0.6,
        clearcoatRoughness: 0.2,
        envMapIntensity: 1.25,
      }),
    [],
  );
  const glassMat = useMemo(
    () =>
      new THREE.MeshPhysicalMaterial({
        color: "#8f7bff",
        roughness: 0.1,
        metalness: 0,
        transmission: tier === "high" ? 0.9 : 0,
        opacity: tier === "high" ? 1 : 0.3,
        transparent: tier !== "high",
        thickness: 0.4,
        ior: 1.4,
        emissive: "#2a1b8c",
        emissiveIntensity: 0.4,
      }),
    [tier],
  );
  const copper = useMemo(
    () =>
      new THREE.MeshPhysicalMaterial({
        color: "#d08c5a",
        metalness: 1,
        roughness: 0.22,
        envMapIntensity: 1.4,
      }),
    [],
  );
  const dark = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: "#1d2556",
        metalness: 0.8,
        roughness: 0.4,
      }),
    [],
  );
  const wireMat = useMemo(
    () =>
      new THREE.MeshBasicMaterial({
        color: "#6246ff",
        wireframe: true,
        transparent: true,
        opacity: 0.35,
      }),
    [],
  );

  // Stage nodes laid along the path: INTAKE → RESOLVE → GROUP → POLICY → ROUTE.
  const stageNodes = useMemo(() => {
    const angles = [-0.9, -0.1, 0.85, 1.7, 2.35];
    const radii = [2.35, 2.35, 1.82, 1.32, 1.82];
    return angles.map(
      (a, i) =>
        new THREE.Vector3(
          Math.cos(a) * radii[i],
          Math.sin(a) * radii[i] * 0.95,
          (i - 2) * 0.12,
        ),
    );
  }, []);
  const pathA = useMemo(
    () =>
      new THREE.CatmullRomCurve3([
        new THREE.Vector3(0, 0, 0),
        ...stageNodes,
        new THREE.Vector3(3.6, 1.6, 0.4),
      ]),
    [stageNodes],
  );
  const pathB = useMemo(
    () =>
      new THREE.CatmullRomCurve3([
        stageNodes[4],
        new THREE.Vector3(3.2, -1.2, 0.6),
        new THREE.Vector3(3.9, -2.2, 0.2),
      ]),
    [stageNodes],
  );
  const pathAPoints = useMemo(() => pathA.getPoints(120), [pathA]);
  const pathBPoints = useMemo(() => pathB.getPoints(60), [pathB]);

  const tmp = useMemo(() => new THREE.Vector3(), []);
  const tmpColor = useMemo(() => new THREE.Color(), []);
  const tilt = useMemo(() => new THREE.Vector2(), []);

  useFrame((state, dt) => {
    const t = reduce ? 0 : state.clock.elapsedTime;
    if (!reduce) {
      if (ring0.current) {
        ring0.current.rotation.x += dt * 0.22;
        ring0.current.rotation.z += dt * 0.05;
      }
      if (ring1.current) ring1.current.rotation.y -= dt * 0.34;
      if (ring2.current) {
        ring2.current.rotation.z += dt * 0.52;
        ring2.current.rotation.x = 0.7 + Math.sin(t * 0.3) * 0.04;
      }
    }
    // Cursor-reactive, angle-limited tilt (never more than ~13°).
    tilt.set(pointer.current.x * 0.22, pointer.current.y * 0.14);
    if (group.current) {
      group.current.rotation.y += (tilt.x - group.current.rotation.y) * 0.05;
      group.current.rotation.x += (-tilt.y - group.current.rotation.x) * 0.05;
    }
    coreMat.uniforms.uTime.value = t;
    const activeRing = activeStage !== null ? STAGES[activeStage].ring : -1;
    channelMats.current.forEach((m, i) => {
      if (!m) return;
      const on = i === activeRing;
      m.opacity += ((on ? 1 : 0.22) - m.opacity) * 0.12;
      tmpColor.copy(on ? LIME_C : VIOLET_C);
      m.color.lerp(tmpColor, 0.12);
    });
    const hotTarget = activeStage !== null ? 1 : 0.25;
    coreMat.uniforms.uHot.value +=
      (hotTarget - coreMat.uniforms.uHot.value) * 0.08;

    pulses.current.forEach((m, i) => {
      if (!m) return;
      const isA = i < 6;
      const curve = isA ? pathA : pathB;
      const speed = isA ? 0.16 : 0.22;
      const u = reduce
        ? (i * 0.13) % 1
        : (t * speed + (i % 6) * 0.17 + (isA ? 0 : 0.5)) % 1;
      curve.getPointAt(u, tmp);
      m.position.copy(tmp);
      m.scale.setScalar(0.8 + Math.sin(u * Math.PI) * 0.6);
    });
  });

  return (
    <group ref={group}>
      <mesh
        geometry={coreGeo}
        material={coreMat}
        onClick={onCoreClick}
        onPointerOver={() => (document.body.style.cursor = "pointer")}
        onPointerOut={() => (document.body.style.cursor = "")}
      />
      <mesh geometry={wireGeo} material={wireMat} renderOrder={2} />
      <sprite scale={[3.4, 3.4, 1]} material={glowMat} />

      {[ring0, ring1, ring2].map((ref, i) => (
        <group key={i} ref={ref}>
          <mesh geometry={ringGeo[i]} material={ringMat} />
          <mesh geometry={channelGeo[i]} renderOrder={3}>
            <meshBasicMaterial
              ref={(m) => {
                if (m) channelMats.current[i] = m;
              }}
              color="#6246ff"
              transparent
              opacity={0.6}
              toneMapped={false}
            />
          </mesh>
          <mesh geometry={glassGeo[i]} material={glassMat} />
          {[0, 1.57, 3.14, 4.71].map((a) => (
            <mesh
              key={a}
              geometry={clampGeo}
              material={i === 1 ? copper : dark}
              position={[Math.cos(a) * RING_R[i], Math.sin(a) * RING_R[i], 0]}
              rotation={[0, 0, a + Math.PI / 2]}
            />
          ))}
        </group>
      ))}

      {STAGES.map((s, i) => {
        const isActive = activeStage === i;
        return (
          <group key={s.key} position={stageNodes[i]}>
            <mesh
              geometry={nodeGeo}
              scale={isActive ? 1.6 : 1}
              onPointerOver={() => onHoverStage(i)}
              onPointerOut={() => onHoverStage(null)}
              onClick={() => onSelectStage(i)}
            >
              <meshBasicMaterial
                color={isActive ? "#d7ff3f" : "#b7b3d7"}
                toneMapped={false}
              />
            </mesh>
            {/* Stage labels are rendered as a DOM overlay by the host page.
                drei's <Html> portals raced with React unmounting the canvas on
                route change; the in-canvas nodes stay hoverable and clickable. */}
          </group>
        );
      })}

      <Line
        points={pathAPoints}
        color="#32e6d2"
        lineWidth={1}
        transparent
        opacity={0.55}
      />
      <Line
        points={pathBPoints}
        color="#d7ff3f"
        lineWidth={1}
        transparent
        opacity={0.4}
      />
      {Array.from({ length: 8 }).map((_, i) => (
        <mesh
          key={`p${i}`}
          geometry={pulseGeo}
          ref={(m) => {
            if (m) pulses.current[i] = m;
          }}
        >
          <meshBasicMaterial
            color={i < 6 ? "#32e6d2" : "#d7ff3f"}
            toneMapped={false}
          />
        </mesh>
      ))}
      {/* Route endpoints are rendered as DOM by the hero, which keeps them inside
          the viewport; in-canvas labels projected past the right edge. */}
    </group>
  );
}

/** The Kinetic Procurement Core — rendered with R3F, procedural geometry and GLSL. */
export function CoreScene(props: CoreProps) {
  const pointer = useRef(new THREE.Vector2(0, 0));
  const tier = useMemo(() => getDeviceTier(), []);
  const reduce = useMemo(() => prefersReducedMotion(), []);
  const wrap = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = wrap.current;
    if (!el) return;
    const onMove = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      pointer.current.set(
        ((e.clientX - r.left) / r.width) * 2 - 1,
        -(((e.clientY - r.top) / r.height) * 2 - 1),
      );
    };
    const onLeave = () => pointer.current.set(0, 0);
    window.addEventListener("pointermove", onMove);
    el.addEventListener("pointerleave", onLeave);
    return () => {
      window.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerleave", onLeave);
    };
  }, []);

  return (
    <div ref={wrap} className="absolute inset-0">
      <Canvas
        dpr={tier === "high" ? [1, 1.75] : [1, 1.25]}
        camera={{ position: [0, 0.2, 11.4], fov: 34 }}
        gl={{
          antialias: tier !== "mobile",
          alpha: true,
          powerPreference: "high-performance",
        }}
        onCreated={({ gl, scene }) => {
          gl.toneMapping = THREE.ACESFilmicToneMapping;
          gl.toneMappingExposure = 1.05;
          gl.setClearAlpha(0);
          const pmrem = new THREE.PMREMGenerator(gl);
          scene.environment = pmrem.fromScene(
            new RoomEnvironment(),
            0.04,
          ).texture;
          // No scene.background: the industrial footage shows through the canvas.
        }}
      >
        <ambientLight intensity={0.25} />
        <directionalLight
          position={[-4, 5, 4]}
          intensity={2.2}
          color="#d7ff3f"
        />
        <directionalLight
          position={[5, -2, 3]}
          intensity={0.8}
          color="#ff664f"
        />
        <pointLight
          position={[0, 0, 1.2]}
          intensity={6}
          color="#6246ff"
          distance={6}
        />
        <Atmosphere pointer={pointer} reduce={reduce} />
        <Grid reduce={reduce} />
        <Machine {...props} pointer={pointer} reduce={reduce} tier={tier} />
        {tier === "high" ? (
          <EffectComposer multisampling={0}>
            <Bloom
              intensity={0.28}
              luminanceThreshold={0.62}
              luminanceSmoothing={0.25}
              mipmapBlur
            />
          </EffectComposer>
        ) : null}
      </Canvas>
    </div>
  );
}
