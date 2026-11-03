# B310 source validation

444 distinct selected checks passed on the finished source, in grouped runs:

- 59 B310 production-execution/contract cases: 54 portable world persistence and patient fencing cases, plus five native-boundary Ventway swap cases.
- 385 retained clinical/equipment/world persistence, world-journal readiness, B306–B309 equipment/monitor/blood lifetime, build identity and journalled deployment cases.

The main regression run passed 436 tests. Five separate swap cases and three final array-evidence/fence cases account for the other eight. No skipped cases are counted as passes. SQF execution substitutes native object allocation, deletion, geometry, scheduler, inventory and transport boundaries explicitly; production schema, binding, preflight, replay, rollback and custody decisions execute unchanged.

HEMTT 1.23.1 `check --error-on-all` passed: 64 addon configs, 2,258 SQF files and 15 stringtables. The optional wiki lookup used its bundled fallback. The current build identity and whitespace checks passed. Equipment references resolve 155 paths across eight runtime addons. The named remote-execution gates cover 33 literal targets and resolve 22 core entries; the four new world APIs are registered locally and are not remote whitelisted.

New cases cover exact ASL/orientation/manual placement, stable patient rebinding with recycled network IDs, malformed payloads, occupied slots/IDs, unresolved references, pending transfers, partial creation rollback, repeated imports, retired/rebound identities, caller-owned array mutation, changing live sensor arrays, Pro/LS pairing, LS disarming, native ventilator mount prerequisites and supplier/vehicle/recovery custody. Swap cases cover both circuit models, pose/allocation failure and duplicate enrollment.

No new artwork, HTML or model geometry is introduced in B310. Native Arma/dedicated-server, JIP/ownership migration, physics/rendering, Windows PowerShell and native model binarization remain acceptance requirements. The integration candidate retains MLOD models; the source deploy helper performs the normal native Windows release. The mission-specific persistence writer/order/atomicity must still be integrated and accepted separately.
