# Bounded Y: current tag-font fallback and display cache

Parent: `40efb4b6871844dd30aea56da96096b336ba9d23` (W-X). Test-only changes. H224, H280, H299 and H349 retain their original test identities.

The live family is QEDaveMergens, with Caveat selected when its optional bitmap-font descriptor is absent. The result is cached per display and shared by pending and stored render paths. Static labels and editable lines receive the same selected family. Retired QEPhillips references, a Caveat-only config requirement, obsolete text dimensions and a removed B72 setup-note path are no longer demanded. The no-outline-font-distribution guard remains and covers case-insensitive TTF/OTF/WOFF families. Existing current line geometry is checked rather than restored to old values.

Twenty new checks pass on unchanged runtime. Actual font-selection and text-control loop blocks execute with file-probe/control fixtures. Coverage includes present/absent descriptors, one probe on repeated repaint, sharing within a display but not across a new display, unchanged pending/stored payloads, all three pending/stored/static text targets, and mutation controls rejecting old family, wrong path, empty fallback, lost cache or wrong target despite comment decoys.

These tests do not render glyphs, test bitmap completeness, verify engine Caveat availability, live font fitting, IME, actual files changing during an open display, or general modal lifetime. No font assets are added or redistributed. No runtime, configuration, layout, medication, input or snapshot changes. Index 85 to 81; all other H entries remain verbatim. No skip/xfail and no live Arma or stable-release approval. Broad results are recorded in bounded Z and the evidence artifact.
