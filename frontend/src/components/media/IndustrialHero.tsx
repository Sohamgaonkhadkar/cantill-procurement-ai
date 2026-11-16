import gsap from "gsap";
import {
  motion,
  useReducedMotion,
  useScroll,
  useTransform,
} from "motion/react";
import { useEffect, useRef, useState, type RefObject } from "react";
import { useNavigate } from "react-router-dom";
import { Upload } from "lucide-react";
import { useOverview, usePolicies, useRequests } from "@/api/hooks";
import { CoreScene, STAGES } from "@/components/CoreScene";
import {
  Button,
  Counter,
  EASE_OUT,
  ErrorBlock,
  Eyebrow,
  LoadingBlock,
  Magnetic,
} from "@/components/ui";
import { formatDate, pad } from "@/lib/format";
import { cn } from "@/utils/cn";
import { CinematicVideo } from "./CinematicVideo";
import { EditorialReveal, SweepLine, VerticalLabel } from "./EditorialReveal";
import { HERO_POSTER, HERO_VIDEO } from "./assets";

const STAGE_TARGET = [
  "/request-studio",
  "/batch-lab",
  "/decision-xray",
  "/policy-reactor",
  "/inbox",
] as const;

/**
 * The Overview hero: three depth layers in one composition.
 *
 *  back   real CNC footage inside a chamfered window, graded to the palette
 *  middle the interactive Kinetic Core, floating above the machinery
 *  front  editorial typography, deliberately overlapping the footage edge
 *
 * Entry is a single coordinated timeline: footage → sweep line → masked
 * headline → core → metrics. Scroll narrows the footage window and settles the
 * scene into the operational queue below.
 */
export function IndustrialHero({
  scrollRef,
}: {
  scrollRef: RefObject<HTMLElement | null>;
}) {
  const navigate = useNavigate();
  const reduce = useReducedMotion();
  const heroRef = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<number | null>(null);
  const overview = useOverview();
  const policies = usePolicies();
  const requests = useRequests();

  const { scrollYProgress } = useScroll({
    container: scrollRef,
    target: heroRef,
    offset: ["start start", "end start"],
  });
  // Footage window closes up and the core drifts/rotates as the queue arrives.
  const windowScaleX = useTransform(
    scrollYProgress,
    [0, 1],
    [1, reduce ? 1 : 0.82],
  );
  const windowY = useTransform(scrollYProgress, [0, 1], [0, reduce ? 0 : -54]);
  const coreScale = useTransform(
    scrollYProgress,
    [0, 1],
    [1, reduce ? 1 : 0.86],
  );
  const coreRotate = useTransform(
    scrollYProgress,
    [0, 1],
    [0, reduce ? 0 : -7],
  );
  const typeY = useTransform(scrollYProgress, [0, 1], [0, reduce ? 0 : -26]);
  const typeOpacity = useTransform(scrollYProgress, [0.35, 0.95], [1, 0.15]);
  const scrim = useTransform(scrollYProgress, [0, 1], [0.06, 0.4]);

  const firstQueued = requests.data?.items.find(
    (r) => r.approval_status === "pending",
  )?.id;
  const activePolicy = policies.data?.items
    .filter(
      (p) =>
        p.status === "active" &&
        p.effective_date <=
          new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" }),
    )
    .sort((a, b) => b.effective_date.localeCompare(a.effective_date))[0];
  const m = overview.data;
  const stageDetail = hover !== null ? STAGES[hover] : null;

  // Single entry timeline. Everything is sequenced, nothing fires at once.
  useEffect(() => {
    if (reduce) return;
    const ctx = gsap.context(() => {
      gsap.set([".hero-window", ".hero-core", ".hero-metrics"], { opacity: 0 });
      const tl = gsap.timeline({ defaults: { ease: "expo.out" } });
      tl.fromTo(
        ".hero-window",
        { opacity: 0, clipPath: "inset(0 0 0 100%)" },
        { opacity: 1, clipPath: "inset(0 0 0 0%)", duration: 1.15 },
        0,
      )
        .fromTo(
          ".hero-core",
          { opacity: 0, scale: 0.94 },
          { opacity: 1, scale: 1, duration: 1.2 },
          0.62,
        )
        .fromTo(
          ".hero-metrics",
          { opacity: 0, y: 26 },
          { opacity: 1, y: 0, duration: 0.8 },
          1.02,
        );
    }, heroRef);
    return () => ctx.revert();
  }, [reduce]);

  return (
    <section
      ref={heroRef}
      className="industrial-hero relative flex flex-col overflow-hidden md:block md:h-[calc(100vh-68px)] md:min-h-[680px]"
    >
      {/* ---------- BACK LAYER: real industrial footage in a shaped window ---------- */}
      <motion.div
        className="hero-window hero-window-clip relative h-[40vh] w-full md:absolute md:bottom-[132px] md:right-0 md:top-0 md:h-auto md:w-[63%]"
        style={{
          scaleX: windowScaleX,
          y: windowY,
          transformOrigin: "100% 50%",
        }}
      >
        <CinematicVideo
          src={HERO_VIDEO.src}
          poster={HERO_POSTER}
          className="absolute inset-0 h-full w-full"
        >
          {/* Photographic grade. Deliberately light on the right so the machined
              material stays visible; density is concentrated only where the
              editorial type overlaps the footage on the left. */}
          <div
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                "linear-gradient(94deg, rgba(8,11,31,0.97) 0%, rgba(8,11,31,0.78) 24%, rgba(20,26,66,0.18) 52%, rgba(8,11,31,0.3) 100%)",
            }}
            aria-hidden
          />
          {/* Violet light spill rather than a dark vignette, so the metal reads. */}
          <div
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                "radial-gradient(62% 62% at 52% 48%, rgba(98,70,255,0.26), transparent 72%)",
            }}
            aria-hidden
          />
          <motion.div
            className="pointer-events-none absolute inset-0 bg-midnight"
            style={{ opacity: scrim }}
            aria-hidden
          />
          <div
            className="pointer-events-none absolute inset-x-0 bottom-0 h-44 bg-gradient-to-t from-midnight via-midnight/60 to-transparent"
            aria-hidden
          />
        </CinematicVideo>
      </motion.div>

      {/* Precision line sweeping across the whole hero once */}
      <SweepLine className="top-[38%] z-20" delay={0.42} />

      {/* ---------- MIDDLE LAYER: interactive Kinetic Core ---------- */}
      <motion.div
        className="hero-core relative z-10 -mt-[13vh] h-[38vh] w-full md:absolute md:bottom-[132px] md:right-0 md:top-0 md:mt-0 md:h-auto md:w-[60%]"
        style={{ scale: coreScale, rotate: coreRotate }}
      >
        <div className="hero-machine-view absolute inset-0 bottom-[140px]">
          <CoreScene
            activeStage={hover}
            onHoverStage={setHover}
            onSelectStage={(i) =>
              navigate(
                i === 2 && firstQueued
                  ? `/decision-xray/${firstQueued}?run_id=${String(requests.data?.items[0]?.run_id ?? overview.data?.latest_run?.id ?? "")}`
                  : STAGE_TARGET[i],
              )
            }
            onCoreClick={() =>
              navigate(
                firstQueued
                  ? `/decision-xray/${firstQueued}?run_id=${String(requests.data?.items[0]?.run_id ?? overview.data?.latest_run?.id ?? "")}`
                  : "/decision-xray",
              )
            }
          />
        </div>
        {/* Stage rail — DOM overlay, focusable and screen-reader reachable.
            Hovering syncs with the in-canvas nodes; clicking opens that stage's workspace. */}
        <div className="absolute right-5 top-1/2 z-20 hidden -translate-y-1/2 flex-col gap-1.5 md:flex">
          {STAGES.map((s, i) => (
            <button
              key={s.key}
              type="button"
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
              onFocus={() => setHover(i)}
              onBlur={() => setHover(null)}
              onClick={() =>
                navigate(
                  i === 2 && firstQueued
                    ? `/decision-xray/${firstQueued}?run_id=${String(requests.data?.items[0]?.run_id ?? overview.data?.latest_run?.id ?? "")}`
                    : STAGE_TARGET[i],
                )
              }
              aria-current={hover === i}
              className={cn(
                "num whitespace-nowrap px-2.5 py-2 text-left text-[10px] tracking-[0.14em] transition-colors",
                hover === i
                  ? "bg-lime text-ink"
                  : "bg-midnight/70 text-lavender ring-1 ring-inset ring-lavender/25 hover:text-porcelain",
              )}
            >
              {String(i + 1).padStart(2, "0")} {s.key}
            </button>
          ))}
        </div>
        <div className="pointer-events-none absolute left-8 top-7 space-y-1">
          <div className="eyebrow text-lavender/85">
            CORE-7 · 3 RINGS · 5 STAGES
          </div>
          <div className="num text-[10px] tracking-[0.1em] text-lavender/60">
            POLICY {activePolicy?.version ?? "—"} ·{" "}
            {activePolicy?.rules.length ?? 0} RULES
          </div>
        </div>

        {/* Stage explanation, anchored bottom-left of the core */}
        <div className="hero-stage-note absolute bottom-8 left-8 w-[300px]">
          <motion.div
            key={hover ?? "idle"}
            initial={reduce ? false : { opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.32, ease: EASE_OUT }}
            className="surface-dark p-4"
          >
            <div className="num flex items-center justify-between text-[10px] tracking-[0.16em] text-lavender">
              <span>
                {stageDetail
                  ? `STAGE ${pad((hover ?? 0) + 1, 2)} / 05`
                  : "HOVER A STAGE"}
              </span>
              <span className="text-lime">
                {stageDetail ? stageDetail.key : "INTAKE → ROUTE"}
              </span>
            </div>
            <p className="mt-2 text-[13px] leading-relaxed text-porcelain/90">
              {stageDetail
                ? stageDetail.note
                : "Five stages turn raw requests into one controlled decision. Select a stage to inspect it in its workspace."}
            </p>
          </motion.div>
        </div>
        <div className="pointer-events-none absolute bottom-8 right-8 hidden text-right xl:block">
          <div className="num text-[10px] tracking-[0.2em] text-mint">
            ▲ PURCHASE ORDER
          </div>
          <div className="num mt-1 text-[10px] tracking-[0.2em] text-lime">
            ▼ SOURCING
          </div>
        </div>
      </motion.div>

      {/* ---------- FRONT LAYER: editorial typography ---------- */}
      <motion.div
        className="hero-type relative z-20 flex flex-col justify-center px-6 pb-7 pt-5 md:absolute md:bottom-[132px] md:left-0 md:top-0 md:w-[46%] md:min-w-[400px] md:px-12 xl:px-16"
        style={{ y: typeY, opacity: typeOpacity }}
      >
        <div className="pointer-events-none absolute -left-1 top-1/2 hidden -translate-y-1/2 xl:block">
          <VerticalLabel>MACHINE INTELLIGENCE · EST. 2026</VerticalLabel>
        </div>
        <EditorialReveal
          baseDelay={0.5}
          eyebrow={
            <Eyebrow>
              <span className="text-lime">■</span> CORVO SYSTEM / PROCUREMENT
              OPERATIONS
            </Eyebrow>
          }
          lines={[
            "PROCUREMENT",
            <>
              IN{" "}
              <span
                key="motion"
                className="text-transparent"
                style={{ WebkitTextStroke: "1.5px #d7ff3f" }}
              >
                MOTION.
              </span>
            </>,
          ]}
          lineClassName="font-display text-[clamp(46px,4.3vw,66px)] font-medium leading-[0.86] tracking-[-0.045em]"
          headingAs="h1"
          lede={
            <p className="max-w-md text-[16px] leading-relaxed text-lavender">
              Every request has a route.{" "}
              <span className="text-porcelain">
                Every decision has a reason.
              </span>
            </p>
          }
          actions={
            <div className="flex flex-wrap items-center gap-3">
              <Magnetic>
                <Button
                  variant="lime"
                  size="lg"
                  arrow
                  onClick={() => navigate("/request-studio")}
                >
                  New purchase request
                </Button>
              </Magnetic>
              <Magnetic>
                <Button
                  variant="ghost"
                  size="lg"
                  onClick={() => navigate("/batch-lab")}
                >
                  <Upload className="h-4 w-4" aria-hidden />
                  Process batch
                </Button>
              </Magnetic>
            </div>
          }
        />
        <div className="num mt-7 flex flex-wrap gap-x-5 gap-y-1 text-[11px] tracking-[0.1em] text-lavender">
          <span>
            POLICY{" "}
            <span className="text-porcelain">
              {activePolicy?.version ?? "—"}
            </span>
          </span>
          <span>
            EFFECTIVE{" "}
            <span className="text-porcelain">
              {activePolicy ? formatDate(activePolicy.effective_date) : "—"}
            </span>
          </span>
          <span>
            RULES{" "}
            <span className="text-porcelain">
              {activePolicy?.rules.length ?? "—"}
            </span>
          </span>
        </div>
      </motion.div>

      {/* ---------- Metrics ribbon ---------- */}
      <div className="hero-metrics relative z-30 grid grid-cols-2 border-t border-lavender/15 bg-midnight/82 backdrop-blur-md md:absolute md:inset-x-0 md:bottom-0 md:h-[132px] md:grid-cols-4">
        {overview.isPending ? (
          <div className="col-span-4">
            <LoadingBlock label="Reading live metrics" rows={1} />
          </div>
        ) : overview.isError ? (
          <div className="col-span-4 p-4">
            <ErrorBlock
              error={overview.error}
              onRetry={() => overview.refetch()}
            />
          </div>
        ) : (
          <>
            <Metric
              label="AWAITING REVIEW"
              value={m?.pending_requirements}
              tone="lime"
            />
            <Metric
              label="APPROVED ORDERS"
              value={m?.purchase_orders}
              tone="mint"
            />
            <Metric
              label="SOURCING RECORDS"
              value={m?.sourcing_requests}
              tone="coral"
            />
            <div className="flex flex-col justify-end border-l border-lavender/15 px-5 pb-4 pt-4 md:px-7 md:pb-5 md:pt-0">
              <div className="eyebrow text-[10px] text-lavender">
                ACTIVE POLICY
              </div>
              <div className="num mt-2 font-display text-[38px] font-medium leading-none tracking-[-0.03em] text-porcelain md:text-[54px]">
                {activePolicy?.version ?? "—"}
              </div>
            </div>
          </>
        )}
      </div>
      <span className={cn("sr-only")}>
        Background footage: {HERO_POSTER.alt} — {HERO_POSTER.creator}, Pexels.
      </span>
    </section>
  );
}

function Metric({
  label,
  value,
  tone,
}: {
  label: string;
  value: number | undefined;
  tone: "lime" | "mint" | "coral";
}) {
  const color = { lime: "text-lime", mint: "text-mint", coral: "text-coral" }[
    tone
  ];
  return (
    <div className="flex flex-col justify-end border-l border-lavender/15 px-5 pb-4 pt-4 first:border-l-0 md:px-7 md:pb-5 md:pt-0">
      <div className="flex items-center gap-2">
        <span
          className={`live-dot h-1.5 w-1.5 rounded-full bg-current ${color}`}
          aria-hidden
        />
        <span className="eyebrow text-[10px] text-lavender">{label}</span>
      </div>
      <div className="mt-1 flex items-baseline gap-3">
        <Counter
          value={value}
          format={(n) => pad(Math.round(n))}
          className="font-display text-[40px] font-medium leading-none tracking-[-0.04em] text-porcelain md:text-[60px]"
        />
      </div>
    </div>
  );
}
