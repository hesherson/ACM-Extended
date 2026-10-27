# B287 cooler lifecycle and persistence

B287 fixes blood exposure resetting across cooler operations, gives each carried cooler its own native inventory identity, and adds an equipment-save boundary. Stable remains version 1.2.4.1. All participants must use the same complete build. This is a candidate; native multiplayer acceptance is still required.

## Behavior

- Each converted cooler uses a hidden native magazine carrier with the same visible name, image, and mass. Its ammunition field is an opaque nonrecycled server-ledger token, never blood volume. Ordinary Gear transfers move the token; independent coolers of the same type have separate contents and clocks. Public Arsenal cooler items remain fresh issuance inputs.
- State is `[baseClass, coolantStartServerTime, [[bagClass,warmSeconds],...], lastSampleServerTime]`. Reads advance elapsed exposure only for the part of an interval after coolant expires. Neither delayed callbacks nor repeated calls at one timestamp grant fresh coolant. Quiet carried coolers require no periodic metadata commits.
- Carried load/unload/draw operations claim the exact carrier before editing. Failed native removals or additions preserve their source. Capacity uses 250/500/1000 mL volume rather than bag count. The manager selects individual cooler instances.
- The server serializes shared-box draws and deploy/pack transitions. Coolant and per-bag exposure move together; editor boxes initialize once. Boxes are excluded from ordinary loose aging. Packing refuses unrelated cargo and validates physical placement before retiring the source.
- Loose admissions preserve conservative measured exposure. Inventory-replication lag queues a source exposure rather than acknowledging an absent bag. Replays cannot apply the same exposure to a later replacement. World reconciliation is coalesced per frame; quiet boxes avoid repeated state broadcasts.
- Ordinary spiking and Y-set preparation use the same identified source path. The overloaded 4U pickup shortcut also moves exact identified carriers, preserves other cargo, and fences in-flight saves. UI continuations retain patient/access intent and stop when the user changes context. Funding and recovery never infer success from a timeout.

## Save integration

CBA extended loadouts save normalized coolant age and accumulated bag exposure, not raw mission-time timestamps. Restore validates the whole payload, binds it to actual saved carrier tuples, and issues fresh noncolliding live tokens. Duplicate callbacks cannot restock an already applied save. Incomplete funding is retained and fenced from later kit/locality generations.

Mission persistence for raw loadouts, crates and recreated boxes must explicitly save/restore the versioned metadata. This does not automatically integrate arbitrary Antistasi/Liberation save implementations. Offline aging defaults to paused; a mission can supply an explicit validated duration. See [the adapter guide](../maintenance/B287-cooler-persistence.md).

## Practical limits

Ordinary ACM blood items have class/count identity, not native per-bag IDs. Simultaneous indistinguishable same-class/same-count swaps through arbitrary external scripts cannot be reconstructed exactly; reconciliation keeps conservative existing exposure. The cooler carriers themselves have independent native IDs. This change does not claim universal compatibility with third-party code that copies or rewrites native inventory without its metadata.

Execution tests replace native inventory/config/UI/network boundaries and exercise production SQF transitions. They do not reproduce Arma's replication ordering, real collision objects, display rendering or native server scheduling. Native acceptance must include two identical coolers, transfers through player/AI/corpse/vehicle/ground cargo, low server FPS, simultaneous box use, full inventory, repeated packing, expiry during a request, and the mission's actual save adapter.
