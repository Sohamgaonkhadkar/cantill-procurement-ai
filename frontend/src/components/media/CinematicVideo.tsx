import { useEffect, useRef, useState } from "react";
import { cn } from "@/utils/cn";
import { prefersReducedMotion } from "@/lib/config";
import { IndustrialImage } from "./IndustrialImage";
import { HERO_POSTER, type MediaAsset } from "./assets";

type Props = {
  src: string;
  poster: MediaAsset;
  className?: string;
  /** Only play while genuinely on screen — avoids background GPU cost. */
  observe?: boolean;
  children?: React.ReactNode;
};

/**
 * Decorative industrial footage: muted, looping, inline, no controls.
 * Pauses outside the viewport, and under reduced motion the poster still is
 * used instead of the clip so nothing moves. Falls back to the photograph if
 * the codec is unsupported or the file fails to load.
 */
export function CinematicVideo({
  src,
  poster,
  className,
  observe = true,
  children,
}: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);
  const reduce = prefersReducedMotion();

  useEffect(() => {
    const v = videoRef.current;
    if (!v || reduce || failed) return;
    if (!observe) {
      v.play().catch(() => setFailed(true));
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting && e.intersectionRatio > 0.12) {
            v.play().catch(() => {});
          } else {
            v.pause();
          }
        }
      },
      { threshold: [0, 0.12, 0.5] },
    );
    if (wrapRef.current) io.observe(wrapRef.current);
    return () => {
      io.disconnect();
      v.pause();
    };
  }, [observe, reduce, failed]);

  if (reduce || failed) {
    return (
      <div ref={wrapRef} className={cn("relative overflow-hidden", className)}>
        <IndustrialImage
          asset={poster}
          className="absolute inset-0 h-full w-full"
          grade="none"
          priority
        />
        {children}
        <span className="num absolute bottom-2 right-3 text-[9px] tracking-[0.14em] text-lavender/50">
          {reduce ? "STATIC FRAME · REDUCED MOTION" : "STATIC FRAME"}
        </span>
      </div>
    );
  }

  return (
    <div
      ref={wrapRef}
      className={cn("relative overflow-hidden bg-midnight", className)}
    >
      {/* Poster stays mounted underneath so there is never a blank flash. */}
      <IndustrialImage
        asset={poster}
        className="absolute inset-0 h-full w-full"
        grade="none"
        priority
        grain={false}
      />
      <video
        ref={videoRef}
        className="absolute inset-0 h-full w-full object-cover"
        src={src}
        poster={HERO_POSTER.src}
        muted
        loop
        playsInline
        autoPlay
        preload="metadata"
        disablePictureInPicture
        controls={false}
        aria-hidden
        tabIndex={-1}
        onError={() => setFailed(true)}
        onLoadedData={() => setFailed((f) => f)}
      />
      {children}
    </div>
  );
}
