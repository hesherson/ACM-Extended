# B312 source validation

551 distinct selected tests passed in one finished-source regression run:

- 90 new B312 execution/contract cases cover mount/release, ownership/class/range/freeze guards, USB pairing and unplugging, per-episode replay fencing, patient slot reconciliation, native sensor cable selection, ASL curve geometry, bounded visual reuse/cleanup/backoff, mount deletion, external carry takeover, staged pickup refusal, schema-2 references/preflight/rollback, mounted inventory pickup and delayed Ventway binding handoff.
- Three new tests use HEMTT's native P3D reader to inspect the two original tray meshes and cable segment: finite geometry, small face counts, closed primitives, outward normals, procedural materials and autocenter metadata.
- 444 retained clinical/equipment/world persistence, transaction journal, B306–B310 monitoring/blood lifetime, build identity and journalled deployment cases passed.
- 14 retained B311 texture/visual gates passed, including all non-colour Tempus model/material/browser/function bytes remaining unchanged.

Execution fixtures replace native object handles, geometry/attachment commands, scheduler and transport boundaries explicitly. Production admission, epoch, selection, schema, rollback, slot and cache decisions execute unchanged. The cable worker is tested at its 16-bundle / 128-object cap, with stationary/sub-2-mm pose reuse, allocation failure backoff and complete cleanup. New tests retain live old-object references through deletion to expose the Ventway same-frame identity race. These are not native Arma networking or physics tests.

HEMTT 1.23.1 `check --error-on-all` passed: 64 addon configs, 2,271 SQF files and 15 stringtables, with 28 files validated for binarization. The optional wiki lookup used its bundled fallback. The current build contract and whitespace checks passed. Resource validation resolves 157 equipment references across eight runtime addons. Named remote-call coverage includes 35 literal targets; 22 core entries resolve. Only the two authenticated server request endpoints are newly remote-whitelisted; private mutation/restore/visual helpers remain local functions.

The prior B310 world fixtures now recognize schema-2 empty capture and substitute the newly observed native attachment boundary; their legacy-schema import and clinical/replay assertions remain in place. The prior B308 transaction fixtures represent unparented field objects, while B312 separately executes external-carry and mounted-pickup paths.

No existing Tempus body/model/texture/UI file is changed in B312. New meshes are generic ACME field trays and cosmetic cable segments. Native tray fit, port/anatomical calibration, streaming/3D rendering, vehicle attachment, ACE takeover, actual engine deletion/JIP order, low-FPS behavior, Windows PowerShell/binarization and the mission-specific persistence writer remain acceptance requirements. The integration candidate preserves supplied ODOL models and leaves source MLOD models unbinarized; the source installer performs a normal native Windows release.
