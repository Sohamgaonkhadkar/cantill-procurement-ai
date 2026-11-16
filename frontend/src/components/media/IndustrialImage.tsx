import {
  motion,
  useReducedMotion,
  useScroll,
  useTransform,
  type MotionValue,
} from "motion/react";
import { useRef, useState } from "react";
import { cn } from "@/utils/cn";
import { MediaFallback } from "./MediaFallback";
import type { MediaAsset } from "./assets";

type Grade = "violet" | "coral" | "mint" | "ink" | "none";

const GRADE: Record<Grade, string> = {
  violet:
    "linear-gradient(115deg, rgba(8,11,31,0.94) 0%, rgba(42,27,140,0.55) 45%, rgba(8,11,31,0.86) 100%)",
  coral:
    "linear-gradient(115deg, rgba(8,11,31,0.92) 0%, rgba(255,102,79,0.28) 50%, rgba(8,11,31,0.9) 100%)",
  mint: "linear-gradient(115deg, rgba(8,11,31,0.9) 0%, rgba(50,230,210,0.22) 55%, rgba(8,11,31,0.92) 100%)",
  ink: "linear-gradient(180deg, rgba(8,11,31,0.55) 0%, rgba(8,11,31,0.92) 100%)",
  none: "none",
};

type Props = {
  asset: MediaAsset;
  className?: string;
  imgClassName?: string;
  grade?: Grade;
  /** Cinematic slow push. Disabled automatically under reduced motion. */
  kenBurns?: boolean;
  /** Scroll-linked vertical drift, in px. Needs a scroll container ref. */
  parallax?: number;
  scrollContainer?: React.RefObject<HTMLElement | null>;
  priority?: boolean;
  grain?: boolean;
  children?: React.ReactNode;
  style?: React.CSSProperties;
};

/**
 * Photograph with a colour grade matched to the CORVO palette, a mask reveal,
 * optional Ken Burns / parallax, and a procedural fallback on decode failure.
 */
export function IndustrialImage({
  asset,
  className,
  imgClassName,
  grade = "violet",
  kenBurns = false,
  parallax = 0,
  scrollContainer,
  priority = false,
  grain = true,
  children,
  style,
}: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const reduce = useReducedMotion();

  const { scrollYProgress } = useScroll(
    parallax && scrollContainer
      ? {
          container: scrollContainer,
          target: ref,
          offset: ["start end", "end start"],
        }
      : undefined,
  );
  const animatedY = useTransform(
    scrollYProgress,
    [0, 1],
    [-parallax, parallax],
  );
  const y: MotionValue<number> | number = parallax && !reduce ? animatedY : 0;

  return (
    <div
      ref={ref}
      className={cn("relative overflow-hidden bg-midnight", className)}
      style={style}
    >
      {failed ? <MediaFallback label="IMAGE UNAVAILABLE" /> : null}
      {!failed ? (
        <motion.div
          className="absolute inset-0"
          style={parallax ? { y } : undefined}
          initial={false}
          animate={
            loaded && !reduce && kenBurns ? { scale: 1.09 } : { scale: 1 }
          }
          transition={
            kenBurns
              ? {
                  duration: 18,
                  repeat: Infinity,
                  repeatType: "reverse",
                  ease: "linear",
                }
              : { duration: 1.2, ease: [0.16, 1, 0.3, 1] }
          }
        >
          <img
            src={asset.src}
            alt={asset.alt}
            loading={priority ? "eager" : "lazy"}
            decoding="async"
            fetchPriority={priority ? "high" : "auto"}
            onLoad={() => setLoaded(true)}
            onError={() => setFailed(true)}
            className={cn(
              "h-full w-full object-cover transition-opacity duration-700",
              loaded ? "opacity-100" : "opacity-0",
              imgClassName,
            )}
          />
        </motion.div>
      ) : null}
      {grade !== "none" ? (
        <div
          className="pointer-events-none absolute inset-0"
          style={{ background: GRADE[grade] }}
          aria-hidden
        />
      ) : null}
      {grain ? (
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.16] mix-blend-overlay"
          style={{
            backgroundImage:
              "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='140' height='140'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>\")",
          }}
          aria-hidden
        />
      ) : null}
      {children}
    </div>
  );
}
