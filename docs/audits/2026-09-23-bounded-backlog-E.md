# Bounded E: three-line syringe-tag contracts

Parent checkpoint: `390820d37fbb477451b720aa2f7c91214d3519f3`. Test-only changes.

H213, H220 and H374 retain their original identities. The legacy final-name field is now a no-op compatibility shim; the active UI uses three tag lines. The later 25-character contract supersedes the 17-character requirement. All twelve tag colors, optional None, stable record identity and the existing commit-on-KeyUp/KillFocus bindings remain enforced. The old Select Color caption is not restored over the current Edit Syringe Tag control.

Nineteen new cases pass on unchanged runtime. They execute the actual pending writer, tag application and selected stored-record writer through the existing SQF-VM harness, covering lengths 0, 17, 24, 25, 26 and 80, case preservation, exact-once truncation writes, record reordering and active-editor repaint avoidance. The shim runs and leaves the store untouched. Five negative source checks reject a reverted 17-character limit or missing third editor even when the required text appears in comments. Existing invalid-metadata and stale-selection execution controls remain in the retained historical tests.

This does not measure Unicode graphemes, simulate IME composition, render fonts or certify live Arma UI behavior. No runtime, asset, config, input binding, medication value or physiology changes. The original index moves 141 to 138, keeping all other entries verbatim. No skip or xfail is introduced.
