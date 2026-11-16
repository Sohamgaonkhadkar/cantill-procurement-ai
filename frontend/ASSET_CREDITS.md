# Asset credits

All photography and footage in this project is sourced from **Pexels** under the Pexels License.

**Pexels License summary** — free to use for commercial and non-commercial purposes; no
permission or attribution required (attribution is appreciated and is recorded below);
the assets may be modified; they may not be sold unaltered, redistributed as stock, or
used in a way that implies endorsement by the creator or by any person/brand appearing in
the frame. Source: https://www.pexels.com/license/

No manufacturer or brand photography was used, and no image is presented as a photograph
of a specific SKU. The UI states this explicitly wherever a category illustration appears
("CATEGORY ILLUSTRATION · NOT A CATALOG PHOTOGRAPH OF THIS SKU").

## Storage and optimization

| Aspect | Detail |
| --- | --- |
| Location | `src/assets/media/{images,videos,posters}/` |
| Why not `public/media/` | The integrated application uses Vite asset imports and emits separately cached files in `dist/assets`; FastAPI or the Vercel CDN serves those files. |
| Image format | WebP, quality 72, requested pre-cropped at the exact display size from the Pexels/imgix CDN (`fm=webp&w=…&h=…&fit=crop&q=72`) |
| Total image weight | Restored from the credited original sources; current optimized images total approximately 680 KB |
| Video | `5998850-sd_640_360_30fps.mp4` (1.17 MB). The HD rendition is 10.2 MB and the UHD rendition 16.4 MB; the SD rendition was chosen deliberately so the clip stays an accent rather than a GPU/bandwidth burden. |
| Runtime behaviour | Images are lazy below the fold, `decoding="async"`, and fall back to a procedural `MediaFallback` on decode failure. The video is muted, looping, inline, control-free, paused by `IntersectionObserver` outside the viewport, and replaced by its poster still under `prefers-reduced-motion`. |

## Video

| File | Source page | Creator | License | Used in | Attribution required |
| --- | --- | --- | --- | --- | --- |
| `videos/cnc-turning-coolant.mp4` | https://www.pexels.com/video/cnc-machine-tool-cutting-metal-with-coolant-spray-5998850/ | frank Diego | Pexels License | Retained footage component; not autoplayed on the revised Overview | No (credited in-app and here) |
| `posters/cnc-turning-coolant.webp` | Poster frame of the same video | frank Diego | Pexels License | Static Overview industrial photograph | No |

## Photography

| File | Source page | Creator | License | Used in | Attribution required |
| --- | --- | --- | --- | --- | --- |
| `images/hero-cnc-poster.webp` | https://www.pexels.com/video/cnc-machine-tool-cutting-metal-with-coolant-spray-5998850/ | frank Diego | Pexels License | Hero poster | No |
| `images/bearing-macro.webp` | https://www.pexels.com/photo/macro-shot-of-metal-ball-bearings-in-ukraine-35568191/ | Kostiantyn Klymovets | Pexels License | `ProductVisual` → BEARINGS category (Request Studio, Decision X-Ray stage 1) | No |
| `images/fastener-macro.webp` | https://www.pexels.com/photo/close-up-of-metal-screw-with-textured-surface-31970894/ | Sonny Sixteen | Pexels License | `ProductVisual` → FASTENERS | No |
| `images/safety-glove.webp` | https://www.pexels.com/photo/a-person-wearing-gloves-11427398/ | Jimmy Nilsson Masth | Pexels License | `ProductVisual` → PPE | No |
| `images/cnc-tool-dark.webp` | https://www.pexels.com/photo/close-up-photo-of-metal-tool-10406128/ | Daniel Smyth | Pexels License | `ProductVisual` → TOOLING, category illustration only | No |
| `images/robot-welding.webp` | https://www.pexels.com/photo/a-robot-industrial-machine-grinding-a-steel-11951215/ | alex | Pexels License | Retained licensed media; not used as purchasing evidence | No |
| `images/cnc-coolant.webp` | https://www.pexels.com/photo/close-up-of-machine-splashing-milk-8956445/ | Daniel Smyth | Pexels License | Retained licensed industrial media | No |

## Also considered but not used

| Source | Reason |
| --- | --- |
| Pexels video `19791092` (turning steel on a CNC, 8 s) | Only a 16.4 MB UHD rendition was published; no acceptable small rendition. |
| Pexels video `8926577` (machine drilling metal) | A second simultaneous clip was judged unnecessary; the brief asked for one priority clip plus another only if it materially improved a page. Photography is used on those pages instead. |

## Non-photographic original assets

Created for this project, no third-party rights involved:

- CORVO monogram and wordmark (`src/components/Monogram.tsx`)
- Kinetic Procurement Core — procedural R3F geometry and GLSL (`src/components/CoreScene.tsx`)
- Decision X-Ray exploded layers (`src/components/XRayScene.tsx`)
- Bearing technical schematic — original drawing, not a catalog image (`src/components/BearingSchematic.tsx`)
- Policy Reactor node geometry, Batch Lab pipeline graphics, Supplier Constellation plot, procedural fallback textures

No challenge dataset is published in source. The integrated application has no mock-data mode; automated tests seed clearly synthetic records into an isolated real backend database.

## Corvo 2 font licenses and illustration accuracy

Archivo, IBM Plex Sans and IBM Plex Mono are self-hosted as four Latin WOFF2 files. Their SIL Open Font License texts are retained in `src/assets/fonts/archivo-OFL.txt`, `ibmplexsans-OFL.txt` and `ibmplexmono-OFL.txt`. Font sources: [Google Fonts](https://github.com/google/fonts), with Archivo by Omnibus-Type and Plex by IBM. No external font request is required at runtime.

The previous clock, water-pipe, generic engine and circuit images were removed from category selection. Categories without an appropriate image display the actual catalog record and an explicit missing-photograph state. Category photos are illustrations, never product verification or evidence that a specific SKU was supplied. The Overview uses the credited CNC photograph without a decorative 3D overlay.
