import { cn } from "@/utils/cn";

/** Three mechanical arcs forming a open "C", with a lime emitter for the full stop. */
function arc(cx: number, cy: number, r: number, a0: number, a1: number) {
  const p = (deg: number) => {
    const t = (deg * Math.PI) / 180;
    return [cx + r * Math.cos(t), cy + r * Math.sin(t)] as const;
  };
  const [x0, y0] = p(a0);
  const [x1, y1] = p(a1);
  return `M ${x0.toFixed(2)} ${y0.toFixed(2)} A ${r} ${r} 0 1 1 ${x1.toFixed(2)} ${y1.toFixed(2)}`;
}

export function Monogram({
  size = 36,
  className,
  glow = true,
}: {
  size?: number;
  className?: string;
  glow?: boolean;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      className={cn("shrink-0", className)}
      aria-hidden
    >
      <defs>
        <linearGradient id="mono-g1" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#f5f3ec" />
          <stop offset="1" stopColor="#D8DEDD" />
        </linearGradient>
        <linearGradient id="mono-g2" x1="0" y1="1" x2="1" y2="0">
          <stop offset="0" stopColor="#4678E8" />
          <stop offset="1" stopColor="#82929A" />
        </linearGradient>
      </defs>
      {glow ? (
        <circle cx="32" cy="32" r="30" fill="#4678E8" opacity="0.18" />
      ) : null}
      <path
        d={arc(32, 32, 27, 42, 318)}
        fill="none"
        stroke="url(#mono-g1)"
        strokeWidth="3.2"
        strokeLinecap="round"
      />
      <path
        d={arc(32, 32, 19, 58, 302)}
        fill="none"
        stroke="url(#mono-g2)"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <path
        d={arc(32, 32, 11.5, 30, 330)}
        fill="none"
        stroke="#D8DEDD"
        strokeOpacity="0.7"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx="50" cy="32" r="4.2" fill="#76A0F4" />
      <circle
        cx="50"
        cy="32"
        r="8"
        fill="none"
        stroke="#76A0F4"
        strokeOpacity="0.35"
      />
    </svg>
  );
}

/** Lockup used in the rail and intro. */
export function Wordmark({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "font-display text-[22px] font-semibold tracking-[-0.04em] text-porcelain",
        className,
      )}
    >
      corvo<span className="text-lime">.</span>
    </span>
  );
}
