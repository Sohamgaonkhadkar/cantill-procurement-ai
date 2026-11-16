import { animate, motion, useReducedMotion, useSpring } from "motion/react";
import {
  forwardRef,
  useEffect,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type ReactNode,
} from "react";
import { ArrowUpRight, Loader2 } from "lucide-react";
import { cn } from "@/utils/cn";
import { ApiError, type RequestStatus, type Urgency } from "@/api";

export const CHAMFER =
  "polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 12px 100%, 0 calc(100% - 12px))";
export const CHAMFER_SM =
  "polygon(0 0, calc(100% - 7px) 0, 100% 7px, 100% 100%, 7px 100%, 0 calc(100% - 7px))";
export const EASE_OUT = [0.16, 1, 0.3, 1] as const;

/* ---------- Panels ---------- */

type Tone = "dark" | "paper" | "ultra" | "lime" | "plain";
const TONE: Record<Tone, string> = {
  dark: "surface-dark text-porcelain",
  paper:
    "paper-texture text-ink border border-ink/10 shadow-[0_30px_60px_-35px_rgba(8,11,31,0.55)]",
  ultra:
    "bg-ultra-deep/70 text-porcelain border border-ultra-hi/25 shadow-[0_0_80px_-20px_rgba(98,70,255,0.6)]",
  lime: "bg-lime text-ink",
  plain: "",
};

export function Panel({
  tone = "dark",
  className,
  style,
  children,
  ...rest
}: HTMLAttributes<HTMLDivElement> & { tone?: Tone }) {
  return (
    <div
      className={cn("relative", TONE[tone], className)}
      style={style}
      {...rest}
    >
      {children}
    </div>
  );
}

/* ---------- Buttons ---------- */

type Variant = "lime" | "ghost" | "ink" | "ultra" | "danger" | "paper";
const BTN: Record<Variant, string> = {
  lime: "bg-lime text-ink hover:bg-[#e4ff73] sheen-hover",
  ultra: "bg-ultra text-porcelain hover:bg-ultra-hi sheen-hover",
  ghost:
    "bg-white/[0.05] text-porcelain hover:bg-white/[0.1] ring-1 ring-inset ring-lavender/20",
  ink: "bg-ink text-porcelain hover:bg-ink-2",
  paper: "bg-white text-ink ring-1 ring-inset ring-ink/15 hover:bg-porcelain-2",
  danger:
    "bg-coral/10 text-coral ring-1 ring-inset ring-coral/50 hover:bg-coral/20",
};

export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: Variant;
    size?: "sm" | "md" | "lg";
    arrow?: boolean;
    busy?: boolean;
  }
>(function Button(
  {
    variant = "ghost",
    size = "md",
    arrow,
    busy,
    className,
    children,
    disabled,
    ...rest
  },
  ref,
) {
  const sizes = {
    sm: "min-h-8 py-1.5 px-3 text-[12px]",
    md: "min-h-10 py-2 px-4 text-[13px]",
    lg: "min-h-12 py-3 px-6 text-[14px]",
  };
  return (
    <button
      ref={ref}
      disabled={disabled || busy}
      style={{ clipPath: CHAMFER_SM }}
      className={cn(
        "group inline-flex items-center justify-center gap-2 font-medium tracking-tight transition-colors duration-200 disabled:opacity-40",
        BTN[variant],
        sizes[size],
        className,
      )}
      {...rest}
    >
      {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
      <span className="relative z-[1] inline-flex items-center gap-2">
        {children}
      </span>
      {arrow ? (
        <ArrowUpRight
          className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
          aria-hidden
        />
      ) : null}
    </button>
  );
});

/** Pulls its child slightly toward the pointer. Use on selected primary actions only. */
export function Magnetic({
  children,
  strength = 0.22,
  className,
}: {
  children: ReactNode;
  strength?: number;
  className?: string;
}) {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const x = useSpring(0, { stiffness: 260, damping: 18, mass: 0.4 });
  const y = useSpring(0, { stiffness: 260, damping: 18, mass: 0.4 });
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div
      ref={ref}
      className={cn("inline-block", className)}
      style={{ x, y }}
      onPointerMove={(e) => {
        const r = ref.current!.getBoundingClientRect();
        x.set((e.clientX - (r.left + r.width / 2)) * strength);
        y.set((e.clientY - (r.top + r.height / 2)) * strength);
      }}
      onPointerLeave={() => {
        x.set(0);
        y.set(0);
      }}
    >
      {children}
    </motion.div>
  );
}

/* ---------- Status ---------- */

const ROUTE_DARK: Record<string, string> = {
  CONTRACT_PO: "bg-mint/12 text-mint ring-1 ring-inset ring-mint/45",
  SPOT_PO: "bg-lime/12 text-lime ring-1 ring-inset ring-lime/45",
  RFQ: "bg-coral/12 text-coral ring-1 ring-inset ring-coral/50",
  RFP: "bg-ultra-hi/15 text-[#cfc6ff] ring-1 ring-inset ring-ultra-hi/55",
  NOT_PROCESSED:
    "bg-transparent text-lavender ring-1 ring-dashed ring-lavender/50 border border-dashed border-lavender/50",
};
const ROUTE_PAPER: Record<string, string> = {
  CONTRACT_PO: "bg-mint/25 text-[#00574e] ring-1 ring-inset ring-[#00574e]/40",
  SPOT_PO: "bg-lime/70 text-ink ring-1 ring-inset ring-ink/30",
  RFQ: "bg-coral/20 text-[#9e2f1e] ring-1 ring-inset ring-[#9e2f1e]/40",
  RFP: "bg-ultra/15 text-[#3b25b8] ring-1 ring-inset ring-ultra/40",
  NOT_PROCESSED: "bg-transparent text-ink-2 border border-dashed border-ink/35",
};
const ROUTE_GLYPH: Record<string, string> = {
  CONTRACT_PO: "◆",
  SPOT_PO: "▲",
  RFQ: "◐",
  RFP: "▣",
  NOT_PROCESSED: "○",
};

export function RouteTag({
  route,
  tone = "dark",
  className,
}: {
  route: string;
  tone?: "dark" | "paper";
  className?: string;
}) {
  return (
    <span
      className={cn(
        "num inline-flex items-center gap-1.5 whitespace-nowrap px-2 py-[3px] text-[11px] font-medium tracking-[0.04em]",
        tone === "dark"
          ? (ROUTE_DARK[route] ?? ROUTE_DARK.RFP)
          : (ROUTE_PAPER[route] ?? ROUTE_PAPER.RFP),
        className,
      )}
      style={{ clipPath: CHAMFER_SM }}
    >
      <span aria-hidden className="text-[9px] opacity-80">
        {ROUTE_GLYPH[route] ?? "◇"}
      </span>
      {route}
    </span>
  );
}

export function RequestStatusTag({
  status,
  tone = "dark",
}: {
  status: RequestStatus;
  tone?: "dark" | "paper";
}) {
  const map: Record<RequestStatus, { label: string; cls: string }> = {
    pending: {
      label: "AWAITING REVIEW",
      cls: tone === "dark" ? "text-lime" : "text-[#4d5a00]",
    },
    approved: {
      label: "APPROVED",
      cls: tone === "dark" ? "text-mint" : "text-[#00574e]",
    },
    overridden: {
      label: "OVERRIDDEN",
      cls: tone === "dark" ? "text-copper" : "text-[#8a4a1f]",
    },
  };
  const s = map[status];
  return (
    <span
      className={cn(
        "num inline-flex items-center gap-2 text-[11px] tracking-[0.06em]",
        s.cls,
      )}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full bg-current",
          status === "pending" && "live-dot",
        )}
        aria-hidden
      />
      {s.label}
    </span>
  );
}

export function UrgencyTag({ urgency }: { urgency: Urgency }) {
  return (
    <span
      className={cn(
        "num text-[11px]",
        urgency === "Emergency" ? "text-coral" : "text-lavender",
      )}
    >
      {urgency}
    </span>
  );
}

/* ---------- Typography ---------- */

export function Eyebrow({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("eyebrow text-lavender", className)}>{children}</div>
  );
}

/** Masked word reveal. Each word rises out of its own clipping box. */
export function MaskText({
  text,
  className,
  delay = 0,
  step = 0.07,
}: {
  text: string;
  className?: string;
  delay?: number;
  step?: number;
}) {
  const reduce = useReducedMotion();
  const words = text.split(" ");
  return (
    <span className={cn("inline-block", className)} aria-label={text}>
      {words.map((w, i) => (
        <span
          key={`${w}-${i}`}
          className="mr-[0.2em] inline-block overflow-hidden pb-[0.06em] align-bottom"
          aria-hidden
        >
          <motion.span
            className="inline-block"
            initial={reduce ? false : { y: "110%" }}
            animate={{ y: "0%" }}
            transition={{
              duration: 0.95,
              delay: delay + i * step,
              ease: EASE_OUT,
            }}
          >
            {w}
          </motion.span>
        </span>
      ))}
    </span>
  );
}

/** Animates a displayed figure only when the underlying value changes. */
export function Counter({
  value,
  className,
  format,
}: {
  value: number | null | undefined;
  className?: string;
  format?: (n: number) => string;
}) {
  const fmt = format ?? ((n: number) => Math.round(n).toLocaleString("en-IN"));
  const [shown, setShown] = useState<number | null>(value ?? null);
  const prev = useRef<number | null>(value ?? null);
  useEffect(() => {
    if (value === null || value === undefined) {
      prev.current = null;
      setShown(null);
      return;
    }
    if (prev.current === value) return;
    const from = prev.current ?? 0;
    prev.current = value;
    const controls = animate(from, value, {
      duration: 0.9,
      ease: EASE_OUT,
      onUpdate: (v) => setShown(v),
    });
    return () => controls.stop();
  }, [value]);
  return (
    <span className={cn("num", className)}>
      {shown === null ? "—" : fmt(shown)}
    </span>
  );
}

/* ---------- Surfaces ---------- */

/** Local light that follows the pointer. Apply only to selected technical surfaces. */
export function Spotlight({
  children,
  className,
  color = "rgba(98,70,255,0.22)",
}: {
  children: ReactNode;
  className?: string;
  color?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  return (
    <div
      ref={ref}
      className={cn("group relative", className)}
      onPointerMove={(e) => {
        const r = ref.current!.getBoundingClientRect();
        ref.current!.style.setProperty("--mx", `${e.clientX - r.left}px`);
        ref.current!.style.setProperty("--my", `${e.clientY - r.top}px`);
      }}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 z-0 opacity-0 transition-opacity duration-500 group-hover:opacity-100"
        style={{
          background: `radial-gradient(340px circle at var(--mx,50%) var(--my,50%), ${color}, transparent 62%)`,
        }}
      />
      <div className="relative z-[1]">{children}</div>
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn("animate-pulse rounded-sm bg-white/[0.06]", className)}
      aria-hidden
    />
  );
}

export function LoadingBlock({
  label = "Loading",
  rows = 4,
}: {
  label?: string;
  rows?: number;
}) {
  return (
    <div className="space-y-3 p-6" role="status" aria-live="polite">
      <div className="eyebrow text-lavender">{label}…</div>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-7 w-full" />
      ))}
    </div>
  );
}

export function ErrorBlock({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry?: () => void;
}) {
  const err = error instanceof Error ? error : new Error("Unknown error");
  const unreachable = error instanceof ApiError && error.status === 0;
  return (
    <div role="alert" className="border border-coral/50 bg-coral/[0.07] p-5">
      <div className="eyebrow text-coral">Request failed</div>
      <p className="mt-2 text-[14px] text-porcelain/90">{err.message}</p>
      {error instanceof ApiError ? (
        <div className="mt-2 text-xs">
          {
            (
              {
                403: "Your role cannot perform this action.",
                409: "This action conflicts. Refresh and review before retrying.",
                422: "Correct the request or uploaded data.",
                429: "Too many attempts. Wait before retrying.",
                503: "Service temporarily unavailable.",
              } as Record<number, string>
            )[error.status]
          }
          {error.retryAfter ? ` Retry after ${error.retryAfter} seconds.` : ""}
          {error.details.length ? (
            <pre className="mt-2 whitespace-pre-wrap">
              {JSON.stringify(error.details, null, 2)}
            </pre>
          ) : null}
        </div>
      ) : null}
      {unreachable ? (
        <p className="mt-2 text-[12px] text-lavender">
          The live API is unavailable. Please retry when connectivity is
          restored.
        </p>
      ) : null}
      {onRetry ? (
        <Button className="mt-4" size="sm" variant="danger" onClick={onRetry}>
          Retry
        </Button>
      ) : null}
    </div>
  );
}

export function EmptyBlock({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-start gap-3 p-8">
      <div className="relative h-12 w-12">
        <svg viewBox="0 0 48 48" className="h-12 w-12" aria-hidden>
          <circle
            cx="24"
            cy="24"
            r="20"
            fill="none"
            stroke="currentColor"
            strokeDasharray="3 5"
            className="text-lavender/50"
          />
          <circle
            cx="24"
            cy="24"
            r="8"
            fill="none"
            stroke="currentColor"
            className="text-lime"
          />
        </svg>
      </div>
      <div className="font-display text-[20px] font-medium">{title}</div>
      <p className="max-w-md text-[13px] text-lavender">{body}</p>
      {action}
    </div>
  );
}

export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="num rounded-[3px] border border-lavender/30 bg-white/5 px-1.5 py-[1px] text-[10px] text-lavender">
      {children}
    </kbd>
  );
}

/** Heading block for every page: eyebrow + masked display title + lede. */
export function PageHeading({
  eyebrow,
  title,
  lede,
  className,
  size = "lg",
}: {
  eyebrow: string;
  title: string;
  lede?: string;
  className?: string;
  size?: "lg" | "xl";
}) {
  return (
    <div className={cn("space-y-4", className)}>
      <Eyebrow>
        <span className="text-lime">●</span> {eyebrow}
      </Eyebrow>
      <h1
        className={cn(
          "font-display font-medium leading-[0.92] tracking-[-0.03em]",
          size === "xl"
            ? "text-[clamp(38px,5vw,72px)]"
            : "text-[clamp(34px,4vw,52px)]",
        )}
      >
        <MaskText text={title} />
      </h1>
      {lede ? (
        <p className="max-w-xl text-[15px] leading-relaxed text-lavender">
          {lede}
        </p>
      ) : null}
    </div>
  );
}
