# Bounded W: current pending-selector creation and refresh

Parent: `585949bc1bf9047208119474a63f2d474b49f517` (U-V). Test-only changes.

H253, H297 and H322 retain their pytest identities. Their older expectations required retired captions, inline selector creation in skInject, and an earlier left-of-barrel position. Current skOpenDraw enables PendingTagReady only after injection, then calls the idempotent Ensure and Render paths. Artwork and three editors precede the selector, and the dropdown follows it. The current Select Syringe Tag caption, all thirteen purpose/None choices, click-only controls, deferred first repaint and 0.10-second later repaint cadence remain protected.

Twenty-one new cases execute the complete Ensure function or actual Render readiness/page-gating prefix, plus negative token contracts with comment decoys. Cases cover all four syringe sizes with native or captured rectangles, no duplicate creation/registration on repeated calls, exact event targets, no creation before readiness, missing displays, and preparation versus Body Map visibility independent of a stale infusion return. Registered event bodies are not invoked by the creation fixture; prior dropdown/color tests cover their separate behavior.

These cases pass on unchanged U-V runtime. This is not a gameplay change or a rendered-layout proof. Controls, positions, text metrics and event registration are explicit fixtures; live mouse events, late external callbacks and whole-dialog ownership remain unverified. Partial engine control-creation failures and malformed initial cached rectangles are not certified. No runtime/configuration/assets or snapshots change. Index 99 to 96. No tests are removed or skipped; unrelated historical test bodies and H entries remain intact.
