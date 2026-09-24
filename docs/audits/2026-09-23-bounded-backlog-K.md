# Bounded K: tag-color selection owns its delayed focus

Parent: `8ceec1ce08bd16af28064e3914f7277da010c6b1` (I-J).

## Runtime correction

Both existing color-selection callbacks looked up whichever Draw Syringe display existed when their 0.01-second focus delay fired. The pending selector could focus another display/provider/page. The stored selector could additionally focus another selected record or a later editor session. Repeated color choices could leave an older focus request active, including a color-to-None-to-same-color sequence.

Only `skTagColor` and `skPendingTagColor` change runtime. They capture the current display and provider and use a display-local color-selection generation. Every accepted color, including None, invalidates an earlier selection's focus. Stored focus additionally requires the same editor generation, selected stable syringe ID and current color. Pending focus requires the preparation page and matching current color. No new event loop, network write or timer is added. The existing 0.01-second delay, color writes, list reset, redraw calls, tag contents, selected-syringe identity and None-versus-text focus targets remain unchanged.

## Evidence and boundaries

28 new SQF execution cases reproduce 14 failing and 14 passing controls on the unchanged I-J runtime. All 28 pass on the candidate. They cover closed/reopened displays, provider/page changes, changed editor/selection/removal/color, same-color reselection, stable-ID reordering, negative row callbacks and normal pending/stored selection. Adjacent editor and syringe-identity execution checks are retained.

These are recorded engine-boundary requests, not live Arma UI rendering or scheduling. The source handlers still perform the existing immediate color write before the deferred focus logic; this correction does not authorize or generation-scope stale incoming selection events. Manual focus changes within an otherwise current delay, same-context page round-trips, general modal ownership and IME behavior remain outside this correction. No medication/physiology/animation changes or stable-release approval. This runtime correction does not itself resolve an original H-index entry; the index remains 119 until bounded L.
