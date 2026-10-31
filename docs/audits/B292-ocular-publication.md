# B292 ocular publication review

Candidate: **1.2.4.1 / B292**, protocol **2**, **19 addons**, based on
B291 `a27c15221cdc96a43efe30b2ef60619a73deb898`.

## Problem and behavior

The one-second ocular worker remains active for shield wearers and permanent
ocular casualties. B291 published an unchanged eye-severity flag on each tick,
and shield recovery also published its entire terminal transaction map even
when it was empty or unchanged. These owner broadcasts did not represent a
clinical or inventory transition.

B292 publishes eye severity and removed-shield metadata only when they change.
Ordinary structural recovery still publishes changed anatomy immediately, with
an exact healthy endpoint. The recovery array is copied before mutation so a
reference into stored state cannot conceal a real change from the comparison.

Shield recovery publishes terminal history only after deleting an expired,
settled record. Deleting the final record still publishes the empty map.
Unacknowledged spent records remain protected; expiry and orphan retirement,
owner routing, equipment custody, inventory settlement and dead-casualty
handling retain their existing rules.

All B291 burn, infection, ocular and DD1380 features remain included. Public
version stays **1.2.4.1** and protocol stays **2**. Use the complete B292 package
on the server, clients and headless clients because every component carries
its exact build stamp.

## Verification

- All **15 new publication cases failed against B291**, reproducing the
  redundant writes. All 15 pass after the fix.
- **163/163** selected ocular treatment, publication, checkpoint, physiology and
  owner-recovery cases pass; zero failures/errors/skips.
- **687/687** root tests pass; zero failures/errors/skips.
- Strict HEMTT check passes: **2,130 SQFs / 15 stringtables / 22 rapified
  configs**. Build identity and the native-owner audit pass with zero violations.
- A signed `hemtt release --no-bin` candidate contains **19 PBOs**; all
  **19 signatures** verify. Every PBO config carries B292, and both changed
  ocular runtime sources match the packaged bytes exactly.

These checks measure publication requests at an explicit engine boundary.
They do not measure live network bandwidth, frame time or packet delivery.
The container build omits Arma Tools model/animation binarization. A Windows
build and the B291 native acceptance matrix remain necessary for engine
rendering, inventory transport, multiplayer ownership and save/restart checks.
The candidate remains draft and unmerged.

## Deployment

Close Arma and local servers. Preserve any local edits before updating; the
helper refuses a dirty source checkout and does not discard work.

```powershell
Set-Location 'F:\ACM-Extended'
git fetch origin
git switch fix/b205-network-continuation-20260930
git pull --ff-only origin fix/b205-network-continuation-20260930
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\Deploy-ACME-B292.ps1
```

Confirm **1.2.4.1 / B292** on every machine. Retain the server profile and the
existing [B288 persistence adapter](../maintenance/B288-persistence-adapter.md).
Do not also load a standalone DD1380 copy. The Windows helper runs native
`hemtt release`; the downloadable container package is a signed test candidate.
