# Bounded V: current tag-line layout and optional-editor contracts

Builds on U from S-T. No runtime, configuration, font or asset change in V.

H241, H375 and H378 retain their original pytest identities. H241 now follows the pending selector and three editor registrations in skPendingTagEnsure rather than demanding the retired Tag: None caption in skInject. H375 and H378 verify the current 0.038-height editor rectangles, 0.031 font scale, native-barrel-relative placement and three 25-character lines. They no longer demand retired 0.030/0.024 or 0.0185 sizing or duplicate old geometry inside skCarouselMove, which delegates to the renderer.

Twenty-four new cases pass on unchanged rendering runtime. The actual pending/stored editor loops run with numeric control-command fixtures at three positive rectangle sizes, tag present/absent, stored edit-mode exclusion, and focused pending fields. Mutation controls reject old height/font/length values and missing third-editor registration despite comment decoys. Existing writer, identity, optional None, dropdown and preservation tests remain in the focused selection. All other historical test bodies and H entries remain unchanged. The original index moves 102 to 99; no skip/xfail is added.

These checks record geometry, text, visibility and input-enable requests, not pixels, glyph fitting, font availability, Unicode graphemes, live focus or whole-dialog lifetimes. Their passing does not prove that every long tag fits visually. No live Arma or stable-release approval.

## Complete-checkout validation

Focused: {'passed': 229}. U original: {'failed': 20, 'passed': 2}; V original: {'passed': 24}. Full addon before: {'passed': 4217, 'failed': 130, 'skipped': 4}; after: {'passed': 4266, 'failed': 127, 'skipped': 4}. Exactly three retained historical identities now pass and all 46 new cases pass. No prior identity is missing or newly failing. Both addon commands still fail overall with four unchanged skips and no collection/setup errors. Root before: {'error': 46, 'passed': 137}; after: {'error': 46, 'passed': 137}, with identical raw identities/outcomes. HEMTT check returns 0. Only the documented cancellation-generation runtime file changes; 4081 other existing tracked files retain their SHA256, including every protected snapshot. No live Arma or stable-release approval.
