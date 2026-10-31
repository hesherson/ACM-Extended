# 1.2.4.1 / B236 — audited-candidate corrections

Base: B235, 90e47ed7a2fc457099255f477f2b476fdae2ce9b.

B236 is a corrective candidate, not public-release approval. Server, clients and
headless clients must use the same complete build. No Workshop publication is
performed by the build/deployment helpers.

## Clinical transaction

A real, provider-local supply reservation is bound to patient, catheter UID,
action, token, clinical epoch, deadline, provider and original donor/vehicle
provenance before BEGIN. The patient owner requires the replicated exact scope.
A delayed scope does not send a premature negative acknowledgement or refund;
the existing request retry waits for replication. Same-token retries still use
the patient's idempotent receipt. A different request cannot rebind the same
live reservation. Accepted consumables are retired once; an unknown timed-out
outcome is committed rather than manufacturing replacement stock.

Both saline flushes and field-IV needles use this boundary. Normal flush volume,
field-IV sequencing, physiological formulas and carrier/animation geometry are
unchanged. A raw crystalloid dispatch now requires exactly one finite scalar in
(0, 0.250] liters, retaining the 10 mL flush, 30 mL HTS and 250 mL mannitol paths.
This is a per-message bound, not an aggregate rate limit.

**Trust limit:** replicated client reservations and CBA object locality are not
cryptographic sender authentication. Deliberately forged client state or repeated
raw script-level commands remain outside this fix. A server-authoritative
inventory/clinical RPC protocol would require a separate compatible migration
and native multiplayer acceptance. B236 does not certify an anti-cheat boundary.

## Deployment

`tools/Deploy-ACME-B236.ps1` builds from the normal repository and deploys to both
that folder and `.hemttout/build`. It requires Python 3.9+, Git and HEMTT. Close
Arma and every local dedicated server before starting. The script does not reset,
clean, mirror or replace source directories.

`tools/deploy_acme_release.py` requires the exact 14 PBOs, their signatures and one
public signing key. Every PBO's HEMTT signature and embedded commit/version are
verified; a hash manifest binds subsequent staging to those verified bytes.
Extra active PBOs in either installed target are rejected rather than silently
retained or deleted. An optional server key target is included in the transaction
and copy verification. Other server trust keys are not removed.

All old artifacts are backed up and all new artifacts staged before replacement.
OS-level locking prevents competing helpers. Handled failures restore the prior
artifact sets. Abrupt process termination leaves `.git/acme-deploy/active.json`
and backups; a new deployment refuses to continue until recovery. Concurrent
unrelated edits encountered in recovery are preserved and cause a hard stop.
This is a journalled multi-file transaction, not an atomic directory swap or a
claim of hardware/power-loss durability. Backups are intentionally retained.

Recovery from the established checkout (Arma stopped):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "F:\ACM-Extended\tools\Deploy-ACME-B236.ps1" -Recover
```

After recovery, rebuild/redeploy B236; restored PBOs can be older than the source.
Do not launch an installation reported as unfinished or recovery-required.

## Validation gates

The old monolithic full-addon run is replaced with deterministic SHA-256 module
allocation: eight addon shards and four root shards. Every discovered test module
must occur exactly once, each report must exist, and all existing testcase
occurrences must survive without worse outcomes. A timeout/missing report cannot
be represented as removed tests or success.

The audited 83-module current-test selection is retained, with automatic inclusion
of all build tests numbered B203 and later (no upper build cutoff). Every selected
case must pass, without legacy-error/skip exemptions. A separate strict full-suite
gate requires every case to pass and remains red for inherited failures/errors
or skips. A passing parity job is not a clean suite and never approves release.

Reviewed fixture repairs retain assertions where possible: real owner registry
for coagulation discovery, exact local writer boundary for CBRN effects, and an
SQF-VM map-default adapter for IO lifecycle tests. Selected stale tests of carrier
restoration, pinned menu ordering, build identity and thoracostomy dispatch now
check current behavior rather than retired source layout. Remaining historical
failures must be individually dispositioned; none are globally xfailed/deleted.
The full field-IV workflow fixture now executes the negative provider ACK and
actual single-use refund before modelling a fresh inventory reservation; it no
longer reuses the rejected receipt ID. Original dressing/patency assertions remain.

## Required native acceptance — not executed by Linux tests

Record Windows HEMTT check/release, exact installed-file verification, and matching
1.2.4.1/B236 manifests on server, both clients and any headless client. Then test:

1. Two medics treating the same/different patients: normal IV flush and field-IV
   completion, spam/retry/cancel, timeout, inventory from medic/patient/vehicle,
   disconnect/rejoin and owner transfer. Verify stock/volume exactly once.
2. Direct pressure, CPR/BVM swap, carrier restoration, prone/recovery/Semi-Fowler,
   chest seal/thoracostomy, auscultation, narc box/transfusion, and ventilator/NIV
   inside and outside vehicles, including controlled NPCs and dead casualties.
3. Repeat with the dedicated Antistasi scenario and actual CBA/ACE versions; inspect
   client/server/HC RPTs, frame performance and build-mismatch enforcement.
4. Windows deployment interruption/recovery, stale-PBO refusal, and optional
   server-key copy verification with Arma stopped.

Native rendering, animation continuity, network ordering, remote-client resistance
and Windows PowerShell 5.1 execution are not proven by SQF-VM or filesystem mocks.
