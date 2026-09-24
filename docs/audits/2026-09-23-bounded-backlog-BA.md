# Bounded BA: current shared-carousel geometry reconciliation

Parent: `957cf8186ba1d734ff115270bcdbe01dea6dc2c0` (validated AY-AZ).

BA reconciles the remaining historical Body Map / prepared-syringe geometry contracts with the current single-carousel design.

The current implementation deliberately differs from the older B58-B69 snapshots in several ways:

- one adaptive five-slot 84400-series carousel is shared with Body Map; the retired 84500-series three-slot mini-carousel remains hidden/absent;
- compact and promoted geometry is owned by `fn_skInject.sqf` and `fn_skDynamicLayout.sqf` using the current body rectangles, toolbar-relative carousel widths, route row and attached Edit Syringe Tag row;
- carousel navigation is immediate. The retired 220 ms multi-control slide/grow interpolation was removed because committing dozens of controls for every A/D/click step caused client frame hitches;
- hover is opacity-only. It does not change syringe geometry or the active center scale;
- the decorative fading-gray underlay is retired;
- hit regions are clipped between the attached Edit Syringe Tag row and the current Body Map action/duration row, so they cannot cover clinical controls;
- A/D hints move outward on promotion and remain noninteractive;
- patient-name placement is derived from the actual screen-to-head gap;
- saving a prepared syringe stays on Draw Syringe rather than automatically forcing Body Map open;
- the Body Map header is patient-name only. The selected syringe artwork/tooltip owns the medication readout instead of duplicating a summary header.

A new `test_bounded_current_carousel_contract.py` protects the current geometry, render, header, hint, save, visibility and retired-artifact rules.

BA is test/audit-only. No runtime SQF, config or assets change.

Historical identities covered in BA:
H217, H223, H228, H232, H234, H237, H239, H243, H247, H249, H250, H251,
H260, H261, H262, H263, H272, H273, H274, H275, H285, H286, H287, H288,
H289, H300, H301, H302, H305, H317 and H325.
