/* Runtime configuration. Set in .env (see .env.example). */

export const DATA_MODE = "live";
export const IS_MOCK = false;
export const API_BASE_URL = (
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? ""
).replace(/\/$/, "");

export const APP_NAME = "corvo.";
export const INTRO_KEY = "corvo.intro.seen.v1";

/** Coarse device tier used to decide how much 3D work to do. */
export function getDeviceTier(): "high" | "low" | "mobile" {
  if (typeof window === "undefined") return "low";
  const mobile =
    window.matchMedia("(max-width: 900px)").matches ||
    window.matchMedia("(pointer: coarse)").matches;
  if (mobile) return "mobile";
  const cores = navigator.hardwareConcurrency ?? 4;
  const mem =
    (navigator as Navigator & { deviceMemory?: number }).deviceMemory ?? 8;
  return cores >= 8 && mem >= 8 ? "high" : "low";
}

export function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}
