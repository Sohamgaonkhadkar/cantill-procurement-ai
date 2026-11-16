/* ------------------------------------------------------------------
 * Media registry — every photographic asset used by the product.
 * Files are imported (not referenced by remote URL) so the single-file
 * build inlines them; nothing depends on network access at runtime.
 * Licensing and attribution: see ASSET_CREDITS.md.
 * ------------------------------------------------------------------ */
import bearingMacro from "@/assets/media/images/bearing-macro.webp";
import fastenerMacro from "@/assets/media/images/fastener-macro.webp";
import hydraulicFitting from "@/assets/media/images/hydraulic-fitting.webp";
import safetyGlove from "@/assets/media/images/safety-glove.webp";
import pumpAssembly from "@/assets/media/images/pump-assembly.webp";
import circuitMacro from "@/assets/media/images/circuit-macro.webp";
import gearMacro from "@/assets/media/images/gear-macro.webp";
import cncToolDark from "@/assets/media/images/cnc-tool-dark.webp";
import robotWelding from "@/assets/media/images/robot-welding.webp";
import cncCoolant from "@/assets/media/images/cnc-coolant.webp";
import heroPoster from "@/assets/media/posters/cnc-turning-coolant.webp";
import heroVideo from "@/assets/media/videos/cnc-turning-coolant.mp4";

export type MediaAsset = {
  src: string;
  /** What the frame actually shows. Never implies a specific SKU. */
  alt: string;
  creator: string;
  source: string;
  /** Dominant mood, used to pick the overlay grade. */
  tone: "dark" | "mid" | "bright";
};

export const HERO_VIDEO = { src: heroVideo, poster: heroPoster, duration: 14 };
export const HERO_POSTER: MediaAsset = {
  src: heroPoster,
  alt: "CNC cutting tool working metal with coolant spray, macro cinematography",
  creator: "frank Diego",
  source:
    "https://www.pexels.com/video/cnc-machine-tool-cutting-metal-with-coolant-spray-5998850/",
  tone: "dark",
};

export const VISUALS = {
  awaiting: {
    src: cncToolDark,
    alt: "Close-up of a CNC milling tool on metal in low key light",
    creator: "Daniel Smyth",
    source:
      "https://www.pexels.com/photo/close-up-photo-of-metal-tool-10406128/",
    tone: "dark",
  },
  coolant: {
    src: cncCoolant,
    alt: "Metalworking fluid splashing over a cutting head during machining",
    creator: "Daniel Smyth",
    source:
      "https://www.pexels.com/photo/close-up-of-machine-splashing-milk-8956445/",
    tone: "dark",
  },
  welding: {
    src: robotWelding,
    alt: "Robotic arm grinding steel, throwing bright sparks",
    creator: "alex",
    source:
      "https://www.pexels.com/photo/a-robot-industrial-machine-grinding-a-steel-11951215/",
    tone: "dark",
  },
  gears: {
    src: gearMacro,
    alt: "Macro photograph of interlocking mechanical gears",
    creator: "Pixabay",
    source: "https://www.pexels.com/photo/clock-motor-209255/",
    tone: "mid",
  },
} satisfies Record<string, MediaAsset>;

/**
 * Category illustrations. These are photographic treatments of a material
 * family — they are explicitly NOT catalog photographs of a specific SKU.
 */
export const CATEGORY_VISUALS: Record<string, MediaAsset> = {
  BEARINGS: {
    src: bearingMacro,
    alt: "Macro photograph of polished steel ball bearings on a dark background",
    creator: "Kostiantyn Klymovets",
    source:
      "https://www.pexels.com/photo/macro-shot-of-metal-ball-bearings-in-ukraine-35568191/",
    tone: "dark",
  },
  FASTENERS: {
    src: fastenerMacro,
    alt: "Macro photograph of a machined screw thread showing cutting marks",
    creator: "Sonny Sixteen",
    source:
      "https://www.pexels.com/photo/close-up-of-metal-screw-with-textured-surface-31970894/",
    tone: "mid",
  },
  HYDRAULICS: {
    src: hydraulicFitting,
    alt: "Braided steel hose fittings and hex nuts on a black background",
    creator: "Nic Wood",
    source:
      "https://www.pexels.com/photo/flexible-water-pipe-with-steel-braid-28101094/",
    tone: "dark",
  },
  PPE: {
    src: safetyGlove,
    alt: "Close-up of black protective industrial gloves worn by a worker",
    creator: "Jimmy Nilsson Masth",
    source: "https://www.pexels.com/photo/a-person-wearing-gloves-11427398/",
    tone: "dark",
  },
  PUMPS: {
    src: pumpAssembly,
    alt: "Industrial pump and engine assembly with hoses and mechanical parts",
    creator: "Jonathan Cooper",
    source:
      "https://www.pexels.com/photo/close-up-of-a-blue-painted-engine-10290625/",
    tone: "mid",
  },
  CAPEX: {
    src: circuitMacro,
    alt: "Macro photograph of soldered circuit board components and connectors",
    creator: "Ivan Chumak",
    source:
      "https://www.pexels.com/photo/close-up-of-electronic-circuit-board-components-40068135/",
    tone: "mid",
  },
  TOOLING: {
    src: cncToolDark,
    alt: "Close-up of a CNC milling tool on metal in low key light",
    creator: "Daniel Smyth",
    source:
      "https://www.pexels.com/photo/close-up-photo-of-metal-tool-10406128/",
    tone: "dark",
  },
};

export const FALLBACK_VISUAL: MediaAsset = VISUALS.gears;

/** Resolve a category illustration; never invents a match for an unknown category. */
export function visualForCategory(
  category: string | null | undefined,
): MediaAsset | null {
  if (!category) return null;
  return CATEGORY_VISUALS[category.toUpperCase()] ?? null;
}
