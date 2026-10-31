# B228 transfusion network and misuse audit

Baseline: B227 `6135b2758ff1c8a772da2cef40939642ab1b174e`.

This patch keeps version 1.2.4.1 and the existing F:\ACM-Extended installation and .hemttout\build launch path. It does not alter the debug renderer, patient wake graph or treatment choreography.

## Requested behavior

Both the 25 mL prime and each queued saline flush now use the actual-admission fluid ledger and saline compartment. The reserve is debited by drained volume, the patient is credited by admitted volume, and existing infiltration remains a loss rather than systemic fluid. The existing IO-fluid response also runs when fluid actually enters an IO. No retroactive fluid is invented for primes completed in earlier builds.

The single service control occupies the former Flush position above Move and Pull Bag. It reads Prime Line (25 mL) on unprimed tubing, Priming... during that job, Flush Line after priming, and Flush In Progress... (n) during a queued flush. A required flush on an empty blood limb flashes red. Left-click retains 50 mL queueing; right-click removes only an unstarted tail entry and uses the inherited native button click sample. The post-two-unit 25 mL minimum / 50 mL preference is unchanged.

Warm blood tooltip: `LifeWarmer Quantum inline: <current mL> mL remaining.`

Foreground transfusion and roller-clamp displays protect their clicks from both immediate and deferred DP/hang-bag cancellation handlers. The Stop/Start control describes the manual flow switch only; it no longer diagnoses occlusion or cardiac arrest. Actual admission restrictions remain on the patient owner.

## Confirmed findings and corrections

### 1. Y-refill rejection fell through to acceptance

Nested SQF `exitWith` statements exited an inner conditional, not the surrounding claim case. A live blood limb, live saline reserve, dirty Y line or conflicting claim could therefore be rejected and then still reserved, with contradictory acknowledgements. Rejections now leave the claim case before mutation. A duplicate claim must match provider, request ID, limb mode and epoch; it does not renew the original lease. Claims use shared server time and are replicated. Finalization rechecks provider, access and clinical epoch.

### 2. The menu could publish a stale remote bag map

The former UI repair pass could overwrite the casualty owner's current whole bag map. UI now asks the owner to create missing zero-volume markers from current owner state. It does not send a viewer's volume/map snapshot. Discovery is limited to once per second and sends no repair request when both limbs are already represented; owner repair is independently bounded. The legacy retag callback now targets exactly the requested part, IV/IO kind and site, and retires on loss of ownership, epoch, access or tubing. Y topology mutation itself rejects non-owners.

### 3. Service commands were not fully bound to their target

Prime/flush/cancel now require a bounded unique request ID, a shared-clock issue time, the exact saline UID and the current clinical epoch. Cancel additionally identifies the active job, preventing an old cancellation from removing a new job's queue. Corrupt job quantities, site/key mismatches, unexpected queued volumes and medicated reserves are rejected before debit. The service cannot redirect into a replacement bag. Removing tubing retires its jobs.

### 4. Service delivery bypassed some normal admission boundaries

B227 priming intentionally consumed fluid outside the patient; its separate path also ignored several flow gates. Both service modes now obey manual stop, physical access/occlusion and the existing CO/CPR perfusion rule. A stopped interval does not create a catch-up bolus. Each actual debit republishes the corresponding job progress instead of leaving up to a second of stale remaining work at ownership transfer. Bag, ledger and job variables are still separate engine publications, not an atomic network transaction.

### 5. Saline/used-bag acknowledgements could recreate stock

Pull, discard and rejected rehang results previously relied on small, evicting seen-ID caches; rehang rejection could fall back to a record supplied in an unsolicited result. They now settle only a locally pending request, against its actual provider and patient. A result cannot create inventory merely by supplying a bag record, and repeated acknowledgements cannot recreate it after the original pending entry is consumed. Controlled-unit changes do not redirect returned stock.

Pull, discard and rehang commits use shared-clock request deadlines and replicated bounded receipts. Live receipts are not evicted to accept more requests. Discard also fingerprints current bag identities, so an old click cannot tear down newly replaced bags. Rehanging checks positive finite volume not exceeding original capacity and rejects an occupied Y limb, a dirty blood line or active service. Used stock is still reserved before sending a rehang request.

### 6. Discarding tubing could convert a medication carrier to plain saline

The old salvage path removed medication metadata while returning the carrier as an ordinary used fluid bag. Medicated carriers are now excluded from ordinary salvage when the tubing is discarded. Ordinary blood and saline retain their exact remaining volumes; spent medication is discarded, matching the existing Pull Bag rule. This is not a new medication recycling mechanism.

### 7. Old pressure-cuff requests could bypass the time check

Omitting the newer pump protocol selected a legacy path without its deadline. Pump requests now require the existing current protocol and valid shared-clock time, and recheck actual access and stable bag identity. Receipt capacity is bounded without evicting still-live requests. First application still requires the reusable infuser; subsequent pumps do not consume another item. Existing physical cuff placement on a corpse remains possible; it does not bypass separate patient-admission restrictions.

Inline warmer fitting and prepared-set attachment also recheck the provider's current ability to act. The warmer does not appear merely because a stale remote request once had a valid provider.

## Scope and limits

This is a source review plus selected production-SQF executions with explicit engine-boundary fixtures, HEMTT checks and package verification. It is not a live Arma dedicated-server session. Native event ordering, packet timing, JIP, abrupt owner loss and simultaneous inventory windows still require in-game testing.

These checks constrain ordinary UI operations and stale/duplicate protocol requests. CBA events and client-owned game state are not a security boundary against arbitrary injected SQF, hostile public-variable writes, forged messages matching a pending request, or server/admin script execution. No anti-cheat certification or claim that all possible exploits are eliminated is made.

Unconfirmed inventory transactions are not automatically refunded on timeout: doing that without an owner decision could duplicate an item already attached to the patient. Abrupt disconnects/owner loss around settlement therefore require testing for both consistency and recovery, not just duplicate prevention. The engine does not atomically publish the bag map, patient compartments and job state together. The patch narrows the inconsistent-state window but does not claim to prove crash-atomic settlement.

Compatible clients/server must all use B228 for these updated request shapes. Do not assess this build's networking by mixing old and new components.

## Regression coverage

New cases execute actual service planning/start/tick, refill claim, salvage commit/result, pressure commit, topology repair and input callbacks, while representing displays, sound, object locality, transport and physiological admission as engine boundaries. They cover:

- exact 25/50/100 mL accounting, partial admission, queue removal and original bag identity;
- paused/occluded/arrest flow, CPR, no catch-up debit and IO effects only after admission;
- malformed jobs, replay windows, receipt capacity, owner loss and per-debit progress publication;
- conflicting/duplicate refill claims and exact-site retagging;
- shared button state, red flashing, inherited RMB sound and preservation of background DP;
- stale/unsolicited/refunded inventory responses, occupied Y limbs and medication-carrier salvage;
- unchanged debug renderer and non-diagnostic Stop/Start text.

The two B227 priming test instances now expect patient credit rather than zero credit, as requested. The historical corpse-cuff test uses the mandatory modern protocol while retaining its physical-attachment expectations. Other baseline test fixture edits expose the new pure helper and explicitly model new engine boundaries; build-marker expectations advance to B228.

## Native acceptance checklist

1. On IV and IO, prime 25 mL; then exhaust blood and request 50 and 100 mL flushes. Compare reserve loss with admitted saline, including obstruction and infiltration. Check priming changes the SAME button into Flush Line.
2. At 25, 49 and 50 mL remaining after two units, confirm minimum/preference and the required-flush red pulse. Right-click while service runs removes only queued work, plays one click and never refunds delivered fluid.
3. Keep DP or a held bag active behind the transfusion menu. Right-click the service control and blank UI, then use the roller clamp. Close the menu and verify deliberate outside RMB can still cancel the hold.
4. Confirm Stop/Start reveals no arrest/occlusion diagnosis; blocked flow remains blocked. The warmer tooltip must track current blood volume without accumulating older suffixes.
5. With two providers, race refill, prime, flush, pull, discard and rehang on one line and on bilateral sites. No request may use another site's bag or create extra stock. Repeat source switching and EFAK-shared supplies.
6. Transfer patient ownership or disconnect/reconnect the provider during active service and between inventory request and acknowledgement. Inspect bag volume, patient saline, remaining queue, reservations and RPTs. Resolve uncertain transactions from the owner, never by manually granting a duplicate refund.
7. Pump the infuser repeatedly and after bag replacement; verify bounded pressure, correct supply checks, decay and no old-bag pressure applied to a replacement.
8. Retest attached NIV/CPAP custody, spontaneous-breath requirements, CPR after carrier removal, and B225 wake/lying behavior using matching B228 clients/server.
