import {
  motion,
  useReducedMotion,
  useScroll,
  useTransform,
} from "motion/react";
import { useRef, type RefObject } from "react";
import { cn } from "@/utils/cn";
import { IndustrialImage } from "./IndustrialImage";
import { SweepLine, VerticalLabel } from "./EditorialReveal";
import type { MediaAsset } from "./assets";

/**
 * Full-bleed photographic strip used as a material transition between a
 * cinematic dark scene and a light operational surface. Deliberately
 * asymmetric: the statement sits off-grid while the photograph drifts.
 */
export function MaterialBand({
  asset,
  statement,
  caption,
  vertical,
  scrollRef,
  className,
  height = 210,
}: {
  asset: MediaAsset;
  statement: string;
  caption?: string;
  vertical?: string;
  scrollRef?: RefObject<HTMLElement | null>;
  className?: string;
  height?: number;
}) {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll(
    scrollRef
      ? {
          container: scrollRef,
          target: ref,
          offset: ["start end", "end start"],
        }
      : undefined,
  );
  const y = useTransform(
    scrollYProgress,
    [0, 1],
    [reduce ? 0 : 34, reduce ? 0 : -34],
  );
  const labelX = useTransform(
    scrollYProgress,
    [0, 1],
    [reduce ? 0 : -40, reduce ? 0 : 40],
  );

  return (
    <div
      ref={ref}
      className={cn("relative overflow-hidden bg-midnight", className)}
      style={{ height }}
    >
      <motion.div className="absolute inset-0" style={{ y }}>
        <IndustrialImage
          asset={asset}
          className="h-[130%] w-full"
          grade="violet"
          parallax={0}
        />
      </motion.div>
      <div
        className="pointer-events-none absolute inset-0 bg-gradient-to-r from-midnight via-midnight/55 to-transparent"
        aria-hidden
      />
      <SweepLine className="top-0" delay={0.1} color="#32e6d2" />

      <div className="relative flex h-full items-center justify-between gap-8 px-8 md:px-12">
        <motion.div className="max-w-[62%]" style={{ x: labelX }}>
          <div className="eyebrow text-mint">MATERIAL RECORD</div>
          <p className="mt-2 font-display text-[clamp(24px,3vw,42px)] font-medium leading-[0.98] tracking-[-0.03em] text-porcelain">
            {statement}
          </p>
          {caption ? (
            <p className="num mt-2 text-[11px] tracking-[0.08em] text-lavender">
              {caption}
            </p>
          ) : null}
        </motion.div>
        {vertical ? (
          <VerticalLabel className="hidden shrink-0 lg:flex">
            {vertical}
          </VerticalLabel>
        ) : null}
      </div>
    </div>
  );
}
