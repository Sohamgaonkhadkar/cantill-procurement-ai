import gsap from "gsap";
import { useEffect, useRef } from "react";
import { Monogram, Wordmark } from "./Monogram";

/**
 * One-time brand entry (~1.4s). Three rings draw, rotate into alignment,
 * the lime emitter pops and the wordmark resolves. Skippable with any key or click.
 */
export function Intro({ onDone }: { onDone: () => void }) {
  const root = useRef<HTMLDivElement>(null);
  const finished = useRef(false);

  useEffect(() => {
    const finish = () => {
      if (finished.current) return;
      finished.current = true;
      onDone();
    };
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({ onComplete: finish });
      gsap.set(".intro-arc", { transformOrigin: "50% 50%" });
      tl.fromTo(
        ".intro-arc",
        { strokeDasharray: 200, strokeDashoffset: 200, opacity: 0 },
        {
          strokeDashoffset: 0,
          opacity: 1,
          duration: 0.55,
          stagger: 0.09,
          ease: "power3.out",
        },
        0,
      )
        .fromTo(
          ".intro-arc",
          { rotate: (i: number) => [-140, 95, 210][i] },
          { rotate: 0, duration: 0.7, ease: "expo.out", stagger: 0.05 },
          0.12,
        )
        .fromTo(
          ".intro-emitter",
          { scale: 0, transformOrigin: "50% 50%" },
          { scale: 1, duration: 0.4, ease: "back.out(2.4)" },
          0.78,
        )
        .fromTo(
          ".intro-word",
          { yPercent: 115 },
          { yPercent: 0, duration: 0.6, ease: "expo.out" },
          0.86,
        )
        .fromTo(
          ".intro-meta",
          { opacity: 0 },
          { opacity: 1, duration: 0.35 },
          0.95,
        )
        .to(root.current, {
          opacity: 0,
          duration: 0.32,
          ease: "power2.inOut",
          delay: 0.22,
        });
    }, root);

    const onKey = () => {
      ctx.revert();
      finish();
    };
    window.addEventListener("keydown", onKey, { once: true });
    return () => {
      window.removeEventListener("keydown", onKey);
      ctx.revert();
    };
  }, [onDone]);

  return (
    <div
      ref={root}
      className="fixed inset-0 z-[300] flex flex-col items-center justify-center bg-midnight"
      role="dialog"
      aria-label="CORVO introduction"
    >
      <div className="pointer-events-none absolute inset-0 grid-bg opacity-[0.35] [mask-image:radial-gradient(circle_at_center,black,transparent_70%)]" />
      <div className="relative flex flex-col items-center gap-7">
        <svg viewBox="0 0 64 64" className="h-40 w-40" aria-hidden>
          <circle cx="32" cy="32" r="30" fill="#6246ff" opacity="0.14" />
          <path
            className="intro-arc"
            d="M 40.1 13.9 A 27 27 0 1 1 13.9 40.1"
            fill="none"
            stroke="#f5f3ec"
            strokeWidth="2.6"
            strokeLinecap="round"
          />
          <path
            className="intro-arc"
            d="M 22.5 14.6 A 19 19 0 1 1 14.6 42.5"
            fill="none"
            stroke="#8f7bff"
            strokeWidth="2.6"
            strokeLinecap="round"
          />
          <path
            className="intro-arc"
            d="M 27 22 A 11.5 11.5 0 1 1 22 42"
            fill="none"
            stroke="#b7b3d7"
            strokeOpacity="0.8"
            strokeWidth="2"
            strokeLinecap="round"
          />
          <circle
            className="intro-emitter"
            cx="50"
            cy="32"
            r="4.2"
            fill="#d7ff3f"
          />
        </svg>
        <div className="overflow-hidden">
          <div className="intro-word">
            <Wordmark className="text-[46px]" />
          </div>
        </div>
        <div className="intro-meta eyebrow text-lavender opacity-0">
          Procurement intelligence engine
        </div>
      </div>
      <button
        onClick={() => {
          finished.current = true;
          onDone();
        }}
        className="absolute bottom-8 right-8 eyebrow text-lavender underline-offset-4 hover:text-lime hover:underline"
      >
        Skip intro ⏎
      </button>
      <Monogram size={0} className="hidden" glow={false} />
    </div>
  );
}
