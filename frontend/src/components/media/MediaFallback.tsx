import { cn } from "@/utils/cn";

/**
 * Procedural stand-in shown while media loads, or permanently if a file fails
 * to decode. Never leaves a broken image icon or an empty hole in a layout.
 */
export function MediaFallback({
  label,
  className,
}: {
  label?: string;
  className?: string;
}) {
  return (
    <div
      className={cn("absolute inset-0 overflow-hidden bg-midnight", className)}
      aria-hidden
    >
      <svg
        className="h-full w-full"
        preserveAspectRatio="xMidYMid slice"
        viewBox="0 0 400 300"
      >
        <defs>
          <linearGradient id="mf-g" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#141a42" />
            <stop offset="1" stopColor="#080b1f" />
          </linearGradient>
          <pattern
            id="mf-hatch"
            width="7"
            height="7"
            patternTransform="rotate(38)"
            patternUnits="userSpaceOnUse"
          >
            <line
              x1="0"
              y1="0"
              x2="0"
              y2="7"
              stroke="#6246ff"
              strokeOpacity="0.28"
              strokeWidth="1.4"
            />
          </pattern>
        </defs>
        <rect width="400" height="300" fill="url(#mf-g)" />
        <rect width="400" height="300" fill="url(#mf-hatch)" />
        <circle
          cx="286"
          cy="96"
          r="54"
          fill="none"
          stroke="#d7ff3f"
          strokeOpacity="0.22"
          strokeDasharray="3 6"
        />
        <circle
          cx="286"
          cy="96"
          r="26"
          fill="none"
          stroke="#32e6d2"
          strokeOpacity="0.3"
        />
      </svg>
      {label ? (
        <div className="absolute inset-x-0 bottom-0 p-3">
          <span className="num text-[10px] tracking-[0.16em] text-lavender/70">
            {label}
          </span>
        </div>
      ) : null}
    </div>
  );
}
