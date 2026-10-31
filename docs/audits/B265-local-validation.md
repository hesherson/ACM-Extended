# B265 local validation evidence

Candidate: **1.2.4.1 / B265**. Audited runtime/test tree before this evidence note: `fa998058e264c7cc6dc450ae83f61e8079c88823`.

## Measured results

- All **33 new equipment regression cases pass**, executing current SQF through the pinned SQF-VM with explicit engine boundaries.
- Five selected regression cases fail against the preceding B264 implementation and pass against B265: unresolved Hang Bag custody deleting a newly equipped weapon; three stale carrier-replacement states; and incomplete duplicate cargo being incorrectly accepted. These are five test cases, not five unrelated bugs.
- All twelve local current-suite shards finished: **9,823 passed; 9 failed; 0 skipped; 0 errors**. Every remaining failure is a `git show` exit 128 for a historical commit absent from the source-only archive, before its comparison/assertion can run. This is **not a green full-suite result**. The complete-history GitHub job must independently execute those cases and the historical parity gates.
- `hemtt check --error-on-all` passed with 1,835 SQF files compiled, 12 stringtables checked and zero CI annotations. This was Linux static validation, not Windows asset binarization or an Arma runtime session.
- Build identity contract passed. Strict native-owner audit passed with **zero violations**. `git diff --check` passed.

## Sources and tools

The complete source archive and pinned tools came from the read-only equipment reproducer for development merge `cab4a1b48329b7c31fc96a33be512147d038775f`. The temporary reproducer workflow is removed from B265. The staged Git tree was rebuilt from local file bytes and checked against GitHub's returned tree hash after every upload.

HEMTT 1.22.0 download SHA-256: `58c0f2c1d88041ebce24753e920ac80efb7624d28e8af9b7960c669117695770`.

SQF-VM v2026.04.03-ed9f5f5 download ZIP SHA-256: `bb4e3bb415305d2ef2c4cdb75e98f442baea3a4575887c6570a11435a780615b`.

The local source archive deliberately contains no historical Git object database. No tests were skipped, deleted, marked expected-failure, or replaced with invented historical objects to obtain the reported results.

## Runtime limits

The tests cannot verify third-party model rendering, real network delivery, or engine automatic magazine selection during `addWeapon`. Those require the dedicated-server matrix in `B265-equipment-transactions-acceptance.md`. A mismatching weapon slot remains unresolved rather than being overwritten or falsely marked restored.

Comprehensive settlement of every pending equipment transaction when an external Arsenal/loadout system replaces a kit remains follow-up integration work. CBA metadata hooks support participating addons; they do not guarantee preservation of arbitrary private addon state.

No Windows release package was built and no server/client installation or public release was deployed by this validation.
