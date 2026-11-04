# B311 source validation

217 distinct selected tests passed on the completed source:

- 14 new texture/visual gates check DXT1/opacity, square mip chains, original base provenance, clipped self-contained vector regions, embedded base/normalized UV aspect, model/material/UI byte preservation, rendered edit isolation and bounded native PAA conversion error.
- 203 retained Tempus clinical/lifetime, patient-equipment, world persistence/model-swap, identity and journalled-deployment cases passed.

The before/after control renders are full-size 4096×4096 RGBA images made with the same source background and sampling geometry. No pixel outside the 17 declared print rectangles changes before DXT compression. Their alpha remains fully opaque. Native PAA decoding confirms the texture was not accidentally reduced to the overlay, and its colour error remains within the visual gate. Source images were inspected after rendering; the original Pro maker mark and source surface design remain visible.

HEMTT 1.23.1 `check --error-on-all` passed: 64 configs, 2,258 SQF files and 15 stringtables. Optional wiki lookup uses its bundled fallback. Current build identity and whitespace checks pass. The equipment gate resolves 155 references across eight runtime addons; named remote-call gates cover 33 literal targets and resolve 22 core entries.

No new SQF gameplay behavior or browser HTML is introduced. The runtime changes are the two colour atlases and B311 build identity. Tests compare every other Tempus Pro/LS file with B310, including supplied ODOL models, material maps, browser content and key overlays. The integration release keeps the supplied ODOL models and leaves other MLOD source models unbinarized; the source installer performs the normal Windows release.

No Arma/dedicated-server, native texture streaming, 3D rendering, Windows PowerShell or native model-binarization acceptance was executed. Read B311-tempus-panel-art.md for the visual acceptance list, scope, texture budget and rebuild instructions. B310 mission-backend hookup requirements remain unchanged.
