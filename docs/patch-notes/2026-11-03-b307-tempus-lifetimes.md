# B307 — Tempus patient and charge lifetimes

Continues B306 `76c9b59109be6058b53a5216a0a6e3df5b3b8950`. Public version remains 1.2.4.1. This local candidate includes the B306 equipment integration and leaves the main/dev release boundaries unchanged.

## Corrections

- Tempus Pro and LS vitals feeds now own a local generation. A retired callback cannot clear a replacement feed's ownership marker, publish values for a replaced patient, or disconnect that replacement. Late feed requests must still name the connected patient. Duplicate starts remain idempotent; locality transfer releases the old local handler before asking the new owner to feed it.
- LS charge start captures a unique token, original patient, clinical epoch, complete power-cycle stamp and selected energy. Ready must return that exact in-progress context within 15 seconds. Completed charge expires after 20 seconds. Replayed, replaced, disconnected, reset or power-cycled contexts cannot become a new charge.
- LS shock requests include the charge token. The patient owner checks the original patient/epoch, power stamp, original energy and expiry before invoking the existing native shock backend. Existing sender, reach, timestamp, replay and native-pad restoration checks remain in place.
- Charge-alarm callbacks compare their complete authorization before sounding or expiring. An old callback removes itself without disarming a replacement charge.
- Pad changes, power-off, cable range loss, inventory loss and moving a device retire charge authorization. Pad changes also clear the former browser snapshot and stop automatic reuse of the old patient's pacer settings. A moved LS assigns the moving provider as operator and retires the source-device pacing request before starting the destination feed.
- The LS browser follows native patient/clinical identity. Patient changes clear charge, pending synchronization and pacing presentation. Missing charge authorization clears a stale charged display, including a restored browser snapshot. Ordinary native polling lets a newly started charge complete its browser handshake.
- Added B307 identity and journalled Windows deployment entry point. The full artifact set remains 27 PBOs.

## Remaining work and acceptance

This is a source/build/browser/SQF-VM validated candidate, not native multiplayer acceptance. The VM replaces engine object, UI and network boundaries; Chromium is not Arma's embedded control.

Test Pro/LS reconnection A→B→A; rapid disarm/recharge near the old expiry; heal/reset while charging/pacing; power cycling; device pickup/place; cable range loss; two nearby operators; patient-owner/server/HC changes; and JIP on a dedicated server with the same complete build everywhere. Assess real transport/animation/key placement in Arma. Low-server-FPS event ordering and simultaneous clients still require native testing.

B306's remaining physical equipment work is unchanged: automatic worn HPMK presentation is disabled; dynamic cooler opening, Ventway cable/variant presentation and live 3D display projection, and physical Pro/LS docking remain pending. Existing clinical equipment custody and cooler inventories remain authoritative. Do not describe this update as completing those presentation features or cross-session persistence.
