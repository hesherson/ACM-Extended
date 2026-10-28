# B288 persistence, network and UI review

Version **1.2.4.1 / B288**, protocol **2**, candidate. This retains B285's syringe delivery ordering and B286's unconscious-AI work reductions. Medmash remains on `dev`; the stable release still contains 14 addons. The draft PR is not release approval.

## Persistence corrections

- Prepared syringes and IV/Y sets export their real contents, volumes and patient ties. Saved native tuples fund fresh identities through retry journals. Server profile reservations prevent ordinary restart token reuse; duplicate holders cannot steal a preparation still physically in its certified custody.
- The acid/base maintenance clock rebases after restore, including legacy raw-clock saves. Clinical object references carry a mission incarnation and optional adapter-assigned durable ID. Reused network IDs cannot silently reconnect an unrelated provider or device.
- Partial vials, used bags, carried ventilator battery/settings and removed-vest cargo have validated equipment snapshots. Cargo remains available until imported native grants settle; repeated imports cannot refill supplies already consumed in the same kit.
- Coolant, blood exposure, donor collection age and fridge restock progress save durations. Native fresh-blood class parsing uses its volume component rather than mistaking the donor ID suffix for volume. Portable donor facts accompany hung, prepared and used blood; missing provenance is fenced.
- Failed/busy CBA captures have an explicit readiness marker. Local retry callbacks hand the adapter one native-plus-metadata capture. Coordinated server leases require participant captures and owner validation; external mission gameplay must remain quiesced until the checkpoint finishes.
- Metadata import retries its original funding without reapplying native loadouts. Kit/locality changes retire the former admission period. Pending or uncertain transfers are not treated as empty inventories or successful saves.

See [the mission adapter contract](../maintenance/B288-persistence-adapter.md) and [the finite inventory identity domain](../maintenance/B288-inventory-persistence.md). A mission saving only native arrays still needs an adapter.

## Network and UI corrections

The review covers production callbacks, owner dispatch, replay decisions, native placement readback, display lifecycle, selection state, function/control registration and the retained UI regression inventory. Native display controls were checked against the supplied ACE source as well as this repository.

- Delayed first cooler draw/deploy requests cannot execute in a later kit or provider locality period. Previously accepted receipts keep their original custody semantics.
- Fridge and fresh-blood return grants retain funded products until delivery proof. Replay cannot debit twice or materialize another item. Native inventory-full spill behavior is verified instead of assuming a false ACE return means no item appeared.
- Fridge items use the generic captured-machine delivery journal. A new owner with native cargo but missing public receipts cannot receive another copy. Fridge Give only presents the result; uncertain stock readback never funds an item, and orphaned products retain their metadata without polling forever.
- Remove/Pull/Y-salvage returns use canonical products and a server delivery journal. The original source machine certifies the completed debit; the original recipient machine must prove or cancel a dispatched placement before another owner can deliver it. UI result callbacks only update presentation. Deleted recipients and unproved partial writes remain explicit held funding and block checkpoints; they never redirect silently into a replacement actor's kit.
- A partial used bag enters Y preparation with its exact remaining volume. The final build consumes its immutable row and native supplies together; cancellation does not create a full-size replacement bag. Filled collection kits return an exact fresh used product without depending on another configured donor ID.
- Temporary infusion-flow pauses are patient-owner operations tied to the exact bag, access, patient generation and provider session. Closing a stale dialog cannot restore a whole outdated flow array or override a later manual setting. Failed constructors clean up their own pause, and obsolete constructors cannot capture a newer dialog.
- Ventilator panels validate clinician, current reach, clinical generation and exact carried/attached device context. Actions reject stale contexts before the next display tick. Readouts and edits use current device settings rather than values cached when the panel opened.
- IV panels and delayed launches retain provider/patient context and release captured leases on failure. Invalid selection rows and mismatched field/dial selection are rejected.
- Fresh-blood labels/logs use immutable bag facts; a configured base class without a donor suffix is formatted safely. Manufacturer capacity and donor metadata survive the canonical per-bag flow tick.
- Treatment supply receipts, owner-private return decisions and public IV supply bindings fence checkpoints. Global journal checks also cover pending products whose original actors were deleted. Active grant indexes and bounded unproven requests keep terminal history out of recurring work.

## Recorded validation

An initial frozen combined B285–B288 selection passed **951 cases across 36 modules**, with no failures, errors or skips. It included 483 B288 cases and retained networking, AI/performance, cooler and build/ownership checks. Further review added fridge handover, unknown-donor preservation, retired UI and owner-log regressions. The complete root-3 allocation passed **254 cases** after its older medication assertions were updated to require refusal before any medicated Pull mutation; no test cases were removed.

Strict HEMTT validation passed **2,045 SQF files and 12 stringtables**. The native-owner audit reported **zero violations**. Exact-commit full-suite and signed-package verification results are recorded in [draft PR #31](https://github.com/hesherson/ACM-Extended/pull/31); these checks are separate from native acceptance.

## Native acceptance

Production SQF execution substitutes native cargo/config/UI/network/disk operations at explicit boundaries. It cannot certify Arma's scheduler, real replication order, rendering, engine profile durability or a particular mission's persistence writer.

Native acceptance must exercise the complete B288 build on all participants, including:

1. The reported VR scenario with increasing unconscious AI and the actual modset, plus a dedicated/HC session; compare frame-time captures rather than infer an FPS gain from unit tests.
2. Packet delay, low server FPS, owner migration, disconnect/reconnect and late acknowledgements during medicine/blood transfers.
3. Inventory-full ground placement, simultaneous draws, identical coolers, repeated packing, source deletion, expired coolant and warmed blood.
4. Restart with prepared mixtures, partial vials, used bags, carried ventilator depletion, removed/nested cargo and fridge stock, using the mission's actual adapter.
5. Busy-save refusal/retry, metadata-only import retries, stale kit/locality callbacks, expired save leases and a deliberately missing component.
6. All medical/infusion/airway/ventilator/assessment/cooler displays at normal and ultrawide resolutions, input cancellation, changed selections, moved clinicians and changed patient/device context.

Neither native acceptance nor public release approval is granted by automated checks.
