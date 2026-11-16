import gsap from "gsap";
import { motion, useReducedMotion } from "motion/react";
import { useEffect, useRef, type ReactNode } from "react";
import { cn } from "@/utils/cn";

const EASE = [0.16, 1, 0.3, 1] as const;

/** One line of display type rising out of a hard mask. */
export function MaskLine({
  children,
  className,
  delay = 0,
  duration = 1,
  as: Tag = "span",
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
  duration?: number;
  as?: "span" | "div" | "h1" | "h2";
}) {
  const reduce = useReducedMotion();
  return (
    <Tag className={cn("block overflow-hidden pb-[0.08em]", className)}>
      <motion.span
        className="block will-change-transform"
        initial={reduce ? false : { y: "112%" }}
        animate={{ y: "0%" }}
        transition={{
          duration: reduce ? 0 : duration,
          delay: reduce ? 0 : delay,
          ease: EASE,
        }}
      >
        {children}
      </motion.span>
    </Tag>
  );
}

/** A thin precision line that sweeps once across a composition. */
export function SweepLine({
  className,
  delay = 0.3,
  color = "#d7ff3f",
  vertical = false,
}: {
  className?: string;
  delay?: number;
  color?: string;
  vertical?: boolean;
}) {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (reduce || !ref.current) return;
    const ctx = gsap.context(() => {
      gsap.fromTo(
        ref.current,
        vertical ? { scaleY: 0, opacity: 1 } : { scaleX: 0, opacity: 1 },
        {
          [vertical ? "scaleY" : "scaleX"]: 1,
          duration: 0.7,
          delay,
          ease: "expo.inOut",
          onComplete: () => gsap.to(ref.current, { opacity: 0, duration: 0.5 }),
        },
      );
    });
    return () => ctx.revert();
  }, [reduce, delay, vertical]);
  return (
    <span
      ref={ref}
      aria-hidden
      className={cn(
        "pointer-events-none absolute block",
        vertical ? "top-0 h-full w-px" : "left-0 h-px w-full",
        className,
      )}
      style={{
        background: vertical
          ? `linear-gradient(180deg, transparent, ${color}, transparent)`
          : `linear-gradient(90deg, transparent, ${color}, transparent)`,
        transformOrigin: vertical ? "top" : "left",
        opacity: reduce ? 0 : undefined,
        boxShadow: `0 0 18px ${color}`,
      }}
    />
  );
}

/** Vertical running label — used to break the grid deliberately. */
export function VerticalLabel({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "num flex items-center gap-3 text-[10px] tracking-[0.28em] text-lavender/70",
        className,
      )}
      style={{ writingMode: "vertical-rl" }}
    >
      <span className="h-8 w-px bg-lavender/30" aria-hidden />
      {children}
    </div>
  );
}

/**
 * Coordinated editorial reveal: eyebrow → masked display lines → lede → actions.
 * Delays are staggered so nothing fires at once.
 */
export function EditorialReveal({
  eyebrow,
  lines,
  lede,
  actions,
  className,
  baseDelay = 0,
  lineClassName,
  headingAs = "div",
}: {
  eyebrow: ReactNode;
  lines: ReactNode[];
  lede?: ReactNode;
  actions?: ReactNode;
  className?: string;
  baseDelay?: number;
  /** Typography applied to every masked display line. */
  lineClassName?: string;
  /** Semantic element wrapping the display lines. */
  headingAs?: "h1" | "h2" | "div";
}) {
  const reduce = useReducedMotion();
  const Heading = headingAs;
  return (
    <div className={cn("space-y-5", className)}>
      <motion.div
        initial={reduce ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: baseDelay, ease: EASE }}
      >
        {eyebrow}
      </motion.div>
      <Heading className="space-y-1">
        {lines.map((line, i) => (
          <MaskLine
            key={i}
            delay={baseDelay + 0.12 + i * 0.11}
            duration={1.05}
            className={lineClassName}
          >
            {line}
          </MaskLine>
        ))}
      </Heading>
      {lede ? (
        <motion.div
          initial={reduce ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: baseDelay + 0.55, ease: EASE }}
        >
          {lede}
        </motion.div>
      ) : null}
      {actions ? (
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: baseDelay + 0.72, ease: EASE }}
        >
          {actions}
        </motion.div>
      ) : null}
    </div>
  );
}
