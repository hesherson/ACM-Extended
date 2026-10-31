# B278 piggyback blank-menu regression

## Confirmed cause

The prepared-infusion picker in `fn_updateTransfusionControls.sqf` checked prepared-record field 16 with `== "propofol"` while a piggyback workflow was active. That field contains numeric carrier volume in ordinary prepared saline infusions. Returning from infusion preparation therefore reached `SCALAR == STRING`, aborting the refresh before the final layout ran. Reopening the same workflow repeated the same failure.

The uploaded blank-menu screenshot retains the native patient name, body map and saline access tag while the ACME controls disappear. This is consistent with the refresh abortion. The supplied B201 RPT concerns the separate chest-seal report and does not establish this UI failure's runtime stack.

The fixed predicate reads the actual optional bottle discriminator at field 17 (`propofol-bottle`) and uses `isEqualTo`, with the native propofol vial classname as a compatibility fallback. It leaves numeric carrier volume, medication component records and physical custody unchanged.

## Initial-layout recovery

The native opener faded managed controls until anchors were ready, but attempted to reveal them only immediately and once on the following frame. A delayed native build or workspace teardown could outlast both attempts; later controller refreshes captured anchors without restoring opacity.

The opener now stores pending fade-control IDs on its exact display. A successful existing controller refresh finishes that reveal and clears the pending IDs. Immediate and next-frame reveal calls remain idempotent. No new UI worker is registered, and revealing opacity preserves each control's existing visibility and enabled state.

## Executable evidence

`addons/acm_extended/tools/test_b278_blank_transfusion_menu.py` executes the production prepared picker and native opener/controller reveal blocks in SQF-VM, using explicit engine boundaries for configuration and control operations.

- The immutable B277 negative control reproduces `Unknown input combination SCALAR == STRING` using a real prepared calcium chloride record with numeric field 16.
- Fixed cases accept ordinary carrier volumes of 0, 100 and 500 mL, including multiple medication components, without mutating the records.
- Direct propofol bottles remain excluded by their actual marker or classname, even if legacy carrier metadata says saline.
- The immutable B277 negative control reproduces permanently faded controls after both initial reveal attempts miss native readiness.
- Fixed cases recover after 2, 4 and 20 missed frames, preserve hidden/disabled control states and avoid repeated fade commits.

The new suite passed all 14 cases. Combined with B278 transfusion input, B278 infusion presentation and B275 exact-return-access checks, 64 cases passed with no failures.

Native Arma layout/input and dedicated-server acceptance remain separate checks; SQF-VM does not render the engine UI.
