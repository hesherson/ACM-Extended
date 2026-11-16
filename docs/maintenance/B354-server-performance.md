# B354 server performance audit

The comparison used the locally installed ACE PBOs and ACE's upstream medical and cargo source. ACE initializes cargo from the vehicle being configured. Medical activity starts from events such as a wound or treatment and runs where the patient is local. ACM Extended already uses owner-local active patient lists for much of its medical work. The cold-chain code was still searching for deployed coolers even though the engine already exposes their initialization events.

## Changes

- Register deployed cooler boxes on the server through core class init hooks, including when the optional equipment PBO is absent. The cooler tick prunes deleted references and returns immediately with an empty list. Both cold-chain paths now use this list. This removes the 39 scheduled class-wide queries per minute and the extra queries from event-driven passes.
- Compare the local player's loose blood and cooler inventory across loadout events. A weapons, bandages or clothing change with the same relevant inventory no longer requests a server pass. The server still coalesces bursts.
- Use native cargo counts by class in the generic inventory and cooler reconciliation passes. Preserve the release-before-admission ordering and use the same server clock. Reuse each sorted list of floating blood ages during a batch admission.
- Publish a new loose-blood exposure baseline when the duration can no longer be predicted from the prior sample. Changes in inventory and seeded ages still publish. Optional legacy auto-cover keeps publishing its sampled age.
- Skip the duplicate aspiration episode lookup without an emesis receipt during idle discovery. Keep its cadence and reuse empty read-only map defaults. The training sweep now re-enrolls missing local patients and leaves scheduled pose/AI upkeep to the existing active worker.

## B355 follow-up

- Blood loadout events and known cooler transactions now reconcile the changed holder and existing exposure ledgers. The server still releases donor entries before matching new cargo. Periodic discovery covers arbitrary native or scripted inventory changes. Native cooler cargo admissions with an unknown participant retain the discovery pass.
- Fridge stock and expiration update at 1 Hz. The 4 Hz door and delivery callback avoids allocating viewer or grant maps on an idle fridge. Dispensing a bag still checks expiry immediately.
- The BVM cue and EMMA display read the native target first and share one fallback proximity sample per provider every quarter second. Ventilator lighting samples at 10 Hz while the display is open.
- The capture reports `bloodInventoryReconcile` alongside `bloodInventoryScan`, so a rare discovery pass is visible separately from normal transactions.

## Remaining costs to measure

| Area | Current work and scope |
| --- | --- |
| Loose blood inventory | Periodic discovery and native-only cooler admissions still enumerate units, corpses and vehicles. These paths cover inventory mutations with an unknown participant. |
| Idle medical discovery and ownership | Each owner checks its owned registry at 1 Hz. The fallback ownership sweep enumerates units every 30 seconds. Timings already exist for both callbacks. Compare healthy AI and equally populated missions with active casualties. |
| Fridges and other equipment | The 4 Hz server fridge callback checks door leases and pending delivery. The 10 Hz ventilator audio callback is scoped to registered patients. |
| CBRN and blast | Each active CBRN zone can do a radius query per second. With blast enabled, each detonation can also trigger proximity checks and several geometry rays per local casualty. Measure these under the mission's intended zone sizes and explosion rate. |
| Client visuals and menus | The SKED shoulder bag still enumerates units and corpses per client, including a listen host. Server captures from a dedicated instance are useful for distinguishing this from network and authority costs. |

## Dedicated-server capture

Run `["start", 180] call ACME_fnc_performanceDiagnostics` locally on the server. Use the [existing RPT export procedure](B286-performance-capture.md) after the capture. Include a stock-heavy mission, native cargo transfers, cooler deployment and deletion, and an idle run with no coolers. Use matching mission populations, settings and workload when comparing B353 and B354.

B354 records `bloodInventoryScan` and `deployedCoolerTick`. The latter includes any inventory scan it triggers synchronously, so adding those totals would double-count that work. The baseline lacks those named timing rows. Frame-time comparisons remain possible across both builds. Run profiling over several minutes to include the once-per-minute inventory pass. Source review and SQF-VM tests establish work removed and state behavior. Dedicated mission frame-time and wire traffic require live measurements.
