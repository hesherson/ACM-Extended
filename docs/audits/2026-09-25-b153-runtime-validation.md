# B153 validation

Base: `f4b2d4f` on `deploy/1.2.3-hotfix-player-facing-20260924`.

## Automated results

- **314 passed** in the combined CPR, Semi-Fowler's entry, BVM startup, direct-pressure persistence, server BVM lifecycle, compatibility, clinical binding, spawner, tray geometry, version, menu/death and historical pose suites.
- **228 passed** in the complete `test_bounded_head_*.py` group.
- **542 total passed, zero failures or skips** across these two non-overlapping runs.
- Public version, carry-drop ownership and wake-state reconciliation gates passed.
- `git diff --check` passed.

SQF execution used SQF-VM `v2026.04.03-ed9f5f5`. Tests execute the checked-out SQF with explicit substitutes for engine-only object, animation, UI, inventory and networking commands. Old fixture gaps for typed object defaults and the independent server clock were corrected; behavioral assertions were retained. These checks do not run the Arma engine.

The new behavior checks cover canceled Semi-Fowler's to CPR entries, replacement sessions, interrupted providers, duplicate entry, configured lowering durations, stale armor-repair deliveries, direct-pressure animation ownership during BVM/CPR transfers, missing/overwritten runtime functions, and handoff clock boundaries. Tray checks decode the actual shipped PAA pixels and verify proportions, mipmaps and bounds at standard and ultrawide dimensions.

## Build

HEMTT **1.22.0**, pinned to the repository's existing CI toolchain, successfully built the full fork using:

```text
hemtt release --no-bin --no-archive
```

The build rapified **16 addon configs**, compiled **1,634 SQF files**, checked **12 stringtables** and produced **14 PBOs**, matching signatures and a server key. There were no compiler errors; output retained existing lint suggestions and a fallback to HEMTT's bundled wiki metadata. Generated Python caches were removed from build inputs before the final package.

The Linux build does not run the Windows model/animation binarizer. Use ordinary `hemtt release` on the Windows build machine for the usual Workshop build.

## Limits

No Arma client, dedicated server or multiplayer session was available here. B153 is ready for the runtime checks in the accompanying patch notes, not a claim of live multiplayer acceptance or approval to promote to the public release branch.

The supplied RPT is evidence of an old, mixed installation: upstream ACM 1.4.8.0 plus only the Extended/itemtext PBOs at 1.2.2.1. It cannot establish B153 runtime behavior. Install the complete fork and disable the separate upstream ACM mod before retesting.
