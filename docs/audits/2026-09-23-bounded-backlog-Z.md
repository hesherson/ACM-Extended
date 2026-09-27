# Bounded Z: frame-free native editor and visibility ownership

Builds on Y from W-X. H267, H268, H281 and H318 retain their original test identities. Test-only changes.

The current editor has ST_NO_RECT style, transparent background/border, zero border size and three 25-character lines at the existing 0.038 height and 0.031 font scale. The stored editor uses its selected syringe's own native barrel rectangle, not an old absolute vertical offset. Current Select Syringe Tag/Edit Syringe Tag captions and tag-face anchor remain. Dynamic layout hides the Body Map while editing but must not force-show its group when editing ends; the body renderer owns child-overlay visibility. The patient header retains its existing edit-mode visibility gate.

Twenty-six new checks pass on unchanged runtime. Actual rectangle selection/validation and group-visibility blocks run with explicit control fixtures. Coverage includes all four stored sizes, edit versus ordinary mode, missing or invalid-length/nonpositive native rectangles, preserving the existing fallback, unchanged syringe data, hide-only body-group requests, and frame/size/caption/visibility mutations with comment decoys. Existing line-layout, selector-geometry, tag-focus, color-focus, writer and preservation tests remain included.

The group fixture intentionally contains no child controls. This does not render child overlays, prove font fitting, test arbitrary malformed numeric types/NaN, create native controls, or certify complete input/display lifetimes. No runtime/configuration/assets/fonts/snapshot changes, no new skip/xfail, and no live Arma or stable-release approval. Index 81 to 77; all unreviewed H entries and historical test bodies remain unchanged.

## Complete-checkout validation

Focused: {'passed': 285}. New cases on unchanged runtime: {'passed': 46}. Full addon before: {'passed': 4361, 'failed': 113, 'skipped': 4}; after: {'passed': 4415, 'failed': 105, 'skipped': 4}. Exactly eight retained historical identities now pass, and all 46 new cases pass. No newly failing or missing previous identity. Both addon commands still return 1 with four unchanged skips and no collection/setup errors. Root before: {'error': 46, 'passed': 137}; after: {'error': 46, 'passed': 137}, with identical raw identities/outcomes. HEMTT check returns 0. All 4087 other existing tracked files retain SHA256, including every runtime/configuration/asset/snapshot file. No live Arma or release-package validation.
