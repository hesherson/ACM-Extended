# B313 candidate — equipment pickup custody

Version 1.2.4.1 / B313 / network protocol 6. Cumulative on B312; world schema 2 and legacy schema 1 import remain supported.

- Fixed pickup admitting a monitor taken by an external carrier while its old ACME mount flag was still present. Admission checks the actual attachment and reciprocal tray occupancy.
- Rechecks custody when the owner inventory acknowledgement arrives. If another system acquired the object during that interval, pickup stays reserved until release; retries reuse the same inventory receipt. ACME does not delete or detach the external carrier's object.
- Pickup immediately releases both physical USB ends and advances the LS connection episode. Repeated cleanup is harmless, and a stale reverse claim cannot unplug another pair. Wireless pairing remains separate.
- Runs setup/pickup reservation and acknowledgement decisions in an unscheduled section when called from scheduled mission code.
- Handles field monitors with no canonical patient without reading variables from a null patient.

Normal pickup from an ACME tray still releases that tray and transfers one item. Release equipment from an external carry/attachment before picking it up. If carry starts during a pending pickup, release it to let the existing pickup finish; no extra pickup or inventory grant is needed. A pending transfer continues to block a persistence checkpoint.

No new remote endpoint or save format is introduced. Existing generic field mounts, cable geometry, patient placement, Tempus artwork and clinical calculations are unchanged. Use the same complete B313 build on server, clients and HCs. Native Arma/ACE carry ordering, dedicated-server/JIP/low-FPS operation and Windows deployment acceptance remain pending. The signed Linux candidate retains unbinarized source MLOD assets; the source installer performs the normal native Windows release.

See B312-tempus-mounts-cables.md for field mounts, USB and persistence setup, and B310-world-equipment-persistence.md for the mission adapter contract.
