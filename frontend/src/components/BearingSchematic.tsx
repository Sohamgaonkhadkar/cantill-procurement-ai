import { cn } from "@/utils/cn";

/**
 * Original technical schematic (not a catalog photograph) of a sealed deep-groove
 * ball bearing. Shown only when the backend has matched a bearing item.
 */
export function BearingSchematic({
  className,
  code,
}: {
  className?: string;
  code?: string;
}) {
  const balls = Array.from({ length: 8 }, (_, i) => {
    const a = (i / 8) * Math.PI * 2 - Math.PI / 2;
    return { x: 200 + Math.cos(a) * 92, y: 200 + Math.sin(a) * 92 };
  });
  return (
    <svg
      viewBox="0 0 400 400"
      className={cn("h-full w-full", className)}
      role="img"
      aria-label={`Schematic of ${code ?? "ball bearing"}`}
    >
      <defs>
        <radialGradient id="bs-bg" cx="35%" cy="30%" r="80%">
          <stop offset="0" stopColor="#1d2556" />
          <stop offset="1" stopColor="#080b1f" />
        </radialGradient>
        <linearGradient id="bs-steel" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#f5f3ec" />
          <stop offset="0.35" stopColor="#8d8fa6" />
          <stop offset="0.6" stopColor="#2b2f48" />
          <stop offset="1" stopColor="#c9c7e8" />
        </linearGradient>
        <radialGradient id="bs-ball" cx="35%" cy="30%" r="70%">
          <stop offset="0" stopColor="#ffffff" />
          <stop offset="0.3" stopColor="#b7b3d7" />
          <stop offset="1" stopColor="#2a1b8c" />
        </radialGradient>
        <filter id="bs-glow" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="3" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <rect width="400" height="400" fill="url(#bs-bg)" />
      <g stroke="#6246ff" strokeOpacity="0.18">
        {Array.from({ length: 9 }, (_, i) => (
          <line key={`h${i}`} x1="0" x2="400" y1={i * 50} y2={i * 50} />
        ))}
        {Array.from({ length: 9 }, (_, i) => (
          <line key={`v${i}`} y1="0" y2="400" x1={i * 50} x2={i * 50} />
        ))}
      </g>
      <circle
        cx="200"
        cy="200"
        r="150"
        fill="none"
        stroke="#d7ff3f"
        strokeOpacity="0.25"
        strokeDasharray="2 6"
      />
      {/* outer ring */}
      <circle
        cx="200"
        cy="200"
        r="132"
        fill="none"
        stroke="url(#bs-steel)"
        strokeWidth="26"
      />
      {/* cage */}
      <circle
        cx="200"
        cy="200"
        r="92"
        fill="none"
        stroke="#32e6d2"
        strokeOpacity="0.35"
        strokeWidth="6"
      />
      {/* balls */}
      {balls.map((b, i) => (
        <circle
          key={i}
          cx={b.x}
          cy={b.y}
          r="17"
          fill="url(#bs-ball)"
          filter="url(#bs-glow)"
        />
      ))}
      {/* inner ring */}
      <circle
        cx="200"
        cy="200"
        r="66"
        fill="none"
        stroke="url(#bs-steel)"
        strokeWidth="24"
      />
      <circle
        cx="200"
        cy="200"
        r="36"
        fill="#080b1f"
        stroke="#d7ff3f"
        strokeOpacity="0.8"
        strokeWidth="1.5"
      />
      <line
        x1="200"
        y1="164"
        x2="200"
        y2="236"
        stroke="#d7ff3f"
        strokeOpacity="0.35"
      />
      {/* annotations */}
      <g fontFamily="IBM Plex Mono, monospace" fontSize="11" fill="#b7b3d7">
        <line
          x1="332"
          y1="128"
          x2="374"
          y2="92"
          stroke="#b7b3d7"
          strokeOpacity="0.6"
        />
        <text x="300" y="82">
          OUTER RING
        </text>
        <line
          x1="290"
          y1="296"
          x2="364"
          y2="338"
          stroke="#32e6d2"
          strokeOpacity="0.7"
        />
        <text x="250" y="352" fill="#32e6d2">
          CAGE · 8 ELEMENTS
        </text>
        <line
          x1="200"
          y1="36"
          x2="200"
          y2="8"
          stroke="#b7b3d7"
          strokeOpacity="0.6"
        />
        <text x="138" y="26">
          ID Ø25 MM
        </text>
        <line
          x1="46"
          y1="200"
          x2="8"
          y2="200"
          stroke="#d7ff3f"
          strokeOpacity="0.7"
        />
        <text x="10" y="186" fill="#d7ff3f">
          2RS SEAL
        </text>
      </g>
      <text
        x="20"
        y="384"
        fontFamily="IBM Plex Mono, monospace"
        fontSize="10"
        fill="#b7b3d7"
        opacity="0.8"
      >
        SCHEMATIC · ORIGINAL DRAWING · NOT A CATALOG PHOTO
      </text>
    </svg>
  );
}
