import {
  AnimatePresence,
  motion,
  useMotionValue,
  useReducedMotion,
  useSpring,
  useTransform,
} from "motion/react";
import { useState } from "react";
import { BearingSchematic } from "@/components/BearingSchematic";
import { cn } from "@/utils/cn";
import { IndustrialImage } from "./IndustrialImage";
import { MediaFallback } from "./MediaFallback";
import { VISUALS, visualForCategory, type MediaAsset } from "./assets";

type Props = {
  /** Catalog category from the backend. Unknown categories get no photograph. */
  category: string | null | undefined;
  itemCode?: string | null;
  itemName?: string | null;
  confidence?: number | null;
  /** Technical annotations drawn from real matched-item data only. */
  facts?: { label: string; value: string }[];
  className?: string;
  compact?: boolean;
  style?: React.CSSProperties;
};

/**
 * Category illustration with a PHOTO / TECHNICAL VIEW toggle.
 * The photograph crossfades into the original bearing schematic through a mask,
 * and a measurement line traces the frame while technical labels settle.
 *
 * The image is a material-family illustration, never a claim about a specific
 * SKU; the caption says so explicitly.
 */
export function ProductVisual({
  category,
  itemCode,
  itemName,
  confidence,
  facts = [],
  className,
  compact = false,
  style,
}: Props) {
  const [mode, setMode] = useState<"photo" | "technical">("photo");
  const reduce = useReducedMotion();
  const asset: MediaAsset | null = visualForCategory(category);
  const resolved = !!category && !!itemCode;

  // Restrained pointer tilt so the item feels like a physical object.
  const mx = useMotionValue(0);
  const my = useMotionValue(0);
  const rx = useSpring(useTransform(my, [-0.5, 0.5], [5, -5]), {
    stiffness: 150,
    damping: 20,
  });
  const ry = useSpring(useTransform(mx, [-0.5, 0.5], [-6, 6]), {
    stiffness: 150,
    damping: 20,
  });

  const schematicAvailable = category?.toUpperCase() === "BEARINGS";

  return (
    <motion.div
      className={cn(
        "relative overflow-hidden bg-midnight ring-1 ring-inset ring-lavender/15",
        className,
      )}
      style={
        reduce
          ? style
          : { ...style, rotateX: rx, rotateY: ry, transformPerspective: 1100 }
      }
      onPointerMove={(e) => {
        const r = e.currentTarget.getBoundingClientRect();
        mx.set((e.clientX - r.left) / r.width - 0.5);
        my.set((e.clientY - r.top) / r.height - 0.5);
      }}
      onPointerLeave={() => {
        mx.set(0);
        my.set(0);
      }}
    >
      <AnimatePresence mode="wait" initial={false}>
        {resolved ? (
          asset ? (
            <motion.div
              key={`photo-${asset.src}`}
              className="absolute inset-0"
              initial={reduce ? false : { clipPath: "inset(0 0 100% 0)" }}
              animate={{ clipPath: "inset(0 0 0% 0)" }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.85, ease: [0.16, 1, 0.3, 1] }}
            >
              <IndustrialImage
                asset={asset}
                className="absolute inset-0 h-full w-full"
                grade={asset.tone === "bright" ? "ink" : "violet"}
                priority
                grain={!compact}
              />
            </motion.div>
          ) : (
            <motion.div
              key="nophoto"
              className="absolute inset-0"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <MediaFallback
                label={`NO CATEGORY ILLUSTRATION FOR ${category}`}
              />
              <div className="absolute inset-0 flex items-end p-4">
                <p className="text-[12px] text-lavender">
                  Item <span className="num text-porcelain">{itemCode}</span> is
                  matched, but no illustration exists for category{" "}
                  <span className="num text-porcelain">{category}</span>. No
                  image is substituted.
                </p>
              </div>
            </motion.div>
          )
        ) : (
          <motion.div
            key="awaiting"
            className="absolute inset-0"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
          >
            <IndustrialImage
              asset={VISUALS.awaiting}
              className="absolute inset-0 h-full w-full"
              grade="ink"
              priority
            />
            <div className="absolute inset-0 flex flex-col justify-between p-4">
              <span className="num text-[10px] tracking-[0.18em] text-lavender/80">
                ITEM RESOLUTION · PENDING
              </span>
              <div>
                <div className="font-display text-[clamp(20px,2.4vw,30px)] font-medium leading-tight tracking-[-0.02em] text-porcelain">
                  AWAITING ITEM RESOLUTION
                </div>
                <p className="mt-1 max-w-xs text-[12px] text-lavender">
                  Describe the item or enter a catalog code. The specification
                  assembles as the backend resolves it.
                </p>
              </div>
            </div>
            {!reduce ? (
              <span
                className="pointer-events-none absolute inset-x-0 h-16 bg-gradient-to-b from-transparent via-lime/12 to-transparent"
                style={{ animation: "scan 4.2s linear infinite" }}
                aria-hidden
              />
            ) : null}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Measurement line + corner ticks: technical framing over the photograph */}
      {resolved ? (
        <svg
          className="pointer-events-none absolute inset-0 h-full w-full"
          viewBox="0 0 400 260"
          preserveAspectRatio="none"
          aria-hidden
        >
          <motion.line
            x1="18"
            y1="228"
            x2="382"
            y2="228"
            stroke="#d7ff3f"
            strokeOpacity="0.75"
            strokeWidth="1"
            initial={reduce ? false : { pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 1.1, delay: 0.35, ease: [0.16, 1, 0.3, 1] }}
          />
          {[18, 382].map((x) => (
            <motion.line
              key={x}
              x1={x}
              y1="222"
              x2={x}
              y2="234"
              stroke="#d7ff3f"
              strokeOpacity="0.9"
              strokeWidth="1"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.9 }}
            />
          ))}
          {[
            [18, 18],
            [382, 18],
            [18, 242],
            [382, 242],
          ].map(([x, y], i) => (
            <motion.path
              key={i}
              d={`M ${x - 8} ${y} L ${x} ${y} L ${x} ${y + (y < 100 ? 8 : -8)}`}
              fill="none"
              stroke="#32e6d2"
              strokeOpacity="0.7"
              strokeWidth="1.2"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 + i * 0.08 }}
            />
          ))}
        </svg>
      ) : null}

      {/* Technical labels */}
      {resolved ? (
        <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-midnight via-midnight/80 to-transparent px-4 pb-4 pt-10">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div className="min-w-0">
              <div className="num text-[10px] tracking-[0.16em] text-lime">
                {itemCode}
                {typeof confidence === "number"
                  ? ` · MATCH ${Math.round(confidence * 100)}%`
                  : ""}
              </div>
              {itemName ? (
                <div className="mt-1 truncate font-display text-[17px] font-medium tracking-[-0.01em] text-porcelain">
                  {itemName}
                </div>
              ) : null}
            </div>
            {facts.length ? (
              <dl className="flex flex-wrap gap-x-4 gap-y-1">
                {facts.map((f) => (
                  <div key={f.label} className="text-right">
                    <dt className="num text-[9px] tracking-[0.14em] text-lavender">
                      {f.label}
                    </dt>
                    <dd className="num text-[12px] text-porcelain">
                      {f.value}
                    </dd>
                  </div>
                ))}
              </dl>
            ) : null}
          </div>
          <div className="num mt-2 text-[9px] tracking-[0.12em] text-lavender/70">
            CATEGORY ILLUSTRATION · NOT A CATALOG PHOTOGRAPH OF THIS SKU
          </div>
        </div>
      ) : null}

      {/* Photo / technical toggle */}
      {resolved && schematicAvailable ? (
        <div
          className="absolute right-3 top-3 flex bg-midnight/80 p-0.5 ring-1 ring-inset ring-lavender/25 backdrop-blur-sm"
          role="group"
          aria-label="Visual mode"
        >
          {(["photo", "technical"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              aria-pressed={mode === m}
              className={cn(
                "num px-2.5 py-1 text-[9px] tracking-[0.12em] transition-colors",
                mode === m
                  ? "bg-lime text-ink"
                  : "text-lavender hover:text-porcelain",
              )}
            >
              {m === "photo" ? "PHOTO" : "TECHNICAL"}
            </button>
          ))}
        </div>
      ) : null}

      {/* Technical view overlays the schematic with a mask wipe */}
      <AnimatePresence>
        {resolved && schematicAvailable && mode === "technical" ? (
          <motion.div
            key="schematic"
            className="absolute inset-0 z-[2] bg-midnight"
            initial={
              reduce ? { opacity: 0 } : { clipPath: "inset(0 100% 0 0)" }
            }
            animate={reduce ? { opacity: 1 } : { clipPath: "inset(0 0% 0 0)" }}
            exit={reduce ? { opacity: 0 } : { clipPath: "inset(0 0 0 100%)" }}
            transition={{ duration: 0.7, ease: [0.7, 0, 0.17, 1] }}
          >
            <BearingSchematic
              code={itemCode ?? undefined}
              className="h-full w-full"
            />
          </motion.div>
        ) : null}
      </AnimatePresence>
    </motion.div>
  );
}
