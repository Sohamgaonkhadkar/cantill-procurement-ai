# Asset credits

All photography and footage in this project is sourced from **Pexels** under the Pexels License.

**Pexels License summary** — free to use for commercial and non-commercial purposes; no
permission or attribution required (attribution is appreciated and is recorded below);
the assets may be modified; they may not be sold unaltered, redistributed as stock, or
used in a way that implies endorsement by the creator or by any person/brand appearing in
the frame. Source: [Pexels License](https://www.pexels.com/license/)

No manufacturer or brand photography was used, and no image is presented as a photograph
of a specific SKU. The UI states this explicitly wherever a category illustration appears
("CATEGORY ILLUSTRATION · NOT A CATALOG PHOTOGRAPH OF THIS SKU").

## Storage and optimization

| Aspect | Detail |
| --- | --- |
| Location | `src/assets/media/{images,videos,posters}/` |
| Why not `public/media/` | The integrated application uses Vite asset imports and emits separately cached files in `dist/assets`; FastAPI or the Vercel CDN serves those files. |
| Image format | WebP files imported by the media registry; served locally through hashed Vite assets |
| Video | One locally served MP4, with a credited WebP poster and reduced-motion still. |
| Runtime behaviour | Images are lazy below the fold, `decoding="async"`, and fall back to a procedural `MediaFallback` on decode failure. The video is muted, looping, inline, control-free, paused by `IntersectionObserver` outside the viewport, and replaced by its poster still under `prefers-reduced-motion`. |

## Video

| File | Source page | Creator | License | Used in | Attribution required |
| --- | --- | --- | --- | --- | --- |
| `videos/cnc-turning-coolant.mp4` | https://www.pexels.com/video/cnc-machine-tool-cutting-metal-with-coolant-spray-5998850/ | frank Diego | Pexels License | Overview hero back layer (`IndustrialHero`) | No (credited in-app and here) |
| `posters/cnc-turning-coolant.webp` | Poster frame of the same video | frank Diego | Pexels License | Hero poster / reduced-motion still | No |

## Photography

| File | Source page | Creator | License | Used in | Attribution required |
| --- | --- | --- | --- | --- | --- |
| `images/bearing-macro.webp` | https://www.pexels.com/photo/macro-shot-of-metal-ball-bearings-in-ukraine-35568191/ | Kostiantyn Klymovets | Pexels License | `ProductVisual` → BEARINGS category (Request Studio and Supplier Constellation) | No |
| `images/fastener-macro.webp` | https://www.pexels.com/photo/close-up-of-metal-screw-with-textured-surface-31970894/ | Sonny Sixteen | Pexels License | `ProductVisual` → FASTENERS | No |
| `images/hydraulic-fitting.webp` | https://www.pexels.com/photo/flexible-water-pipe-with-steel-braid-28101094/ | Nic Wood | Pexels License | `ProductVisual` → HYDRAULICS | No |
| `images/safety-glove.webp` | https://www.pexels.com/photo/a-person-wearing-gloves-11427398/ | Jimmy Nilsson Masth | Pexels License | `ProductVisual` → PPE | No |
| `images/pump-assembly.webp` | https://www.pexels.com/photo/close-up-of-a-blue-painted-engine-10290625/ | Jonathan Cooper | Pexels License | `ProductVisual` → PUMPS | No |
| `images/circuit-macro.webp` | https://www.pexels.com/photo/close-up-of-electronic-circuit-board-components-40068135/ | Ivan Chumak | Pexels License | `ProductVisual` → CAPEX / electrical | No |
| `images/cnc-tool-dark.webp` | https://www.pexels.com/photo/close-up-photo-of-metal-tool-10406128/ | Daniel Smyth | Pexels License | `ProductVisual` → TOOLING, and the "AWAITING ITEM RESOLUTION" state | No |
| `images/gear-macro.webp` | https://www.pexels.com/photo/clock-motor-209255/ | Pixabay | Pexels License | Overview transition, Batch Lab intake and fallback visual | No |
| `images/cnc-coolant.webp` | https://www.pexels.com/photo/close-up-of-machine-splashing-milk-8956445/ | Daniel Smyth | Pexels License | Contract Vault transition band | No |

## Non-photographic original assets

Created for this project, no third-party rights involved:

- CORVO monogram and wordmark (`src/components/Monogram.tsx`)
- Kinetic Procurement Core — procedural R3F geometry and GLSL (`src/components/CoreScene.tsx`)
- Decision X-Ray exploded layers (`src/components/XRayScene.tsx`)
- Bearing technical schematic — original drawing, not a catalog image (`src/components/BearingSchematic.tsx`)
- Policy Reactor node geometry, Batch Lab pipeline graphics, Supplier Constellation plot, procedural fallback textures

No challenge dataset is published in source. Live mode has no synthetic response fallback. The separate public demo persists explicitly fictional records in an isolated database schema; Batch Lab also offers a labeled, non-persisting synthetic preview. Both calculate outcomes through the real procurement engine. Automated tests seed synthetic records into an isolated real backend database. Photography, footage and procedural scenes are presentation assets, not evidence of supplier inventory or an exact catalog SKU.
