# B299 — steady transfusion handoff, Dusk material, and access flags

Candidate 1.2.4.1 / B299, multiplayer protocol 2. Baseline B298 `5a5e484acabbc6c0bf9424328c5807ae962ea6d4`. Existing draft PR #31 remains unmerged.

## What changes

The fluid-card rectangles continue to come from the native list's final layout. The previous browser font conversion assumed Arma sizeEx and a CSS em were interchangeable. Native now exports the estimated advance of a fixed `Hg0123456789` sample in RobotoCondensed, its nominal size, and RscText's documented side margin. After loading the embedded font once, React measures that same fixed sample and calibrates caption/graduation font sizes against the engine advance. This corrects the handoff's font-size assumption without fitting live names or volumes. Browser viewport scaling is included. No browser card is initially admitted until font calibration and the committed render are ready; existing native cards remain visible until acknowledgment, and existing timeout fallback remains intact.

The calibration key uses the font/layout metrics, not clinical values. Volume updates preserve the same DOM nodes, image requests, geometry, focus and font. Later layout/probe changes reuse the loaded face synchronously, retaining card nodes and focus. If measurement fails, a session-bound presentation-only fallback request restores the native pane; late packets cannot reactivate the failed browser session, including after its freshness timer expires or when a native action popup is open. Original native selection, wheel, keyboard, treatment handlers, clinical values and patient/session fencing remain. The documented native text inset and tick-to-track offset are mirrored. Detail, track, normal/selected and piggyback fills now agree with native cards, avoiding a second material change at handoff.

Dusk was previously applied only to the React cards. This pass also changes the existing ACME-authored transfusion nine-slice profiles: lighter slate rows and controls, a lit rim, and one warm reflection baked into the existing window texture. Existing neutral tab palettes stay intact. No new screen, window, frame factory, worker or control-layout owner is introduced. These textures are consumed only by ACME's own transfusion functions. The converter now writes to a fresh temporary PAA before replacing the generated output, so an existing output cannot silently keep its old contents; tests decode shipped center textures to verify current colors.

Selected IV/IO contours keep the original art and threshold, with one solid outer pixel and a 40%-alpha second ring (effective radius 1.4px rather than 2px). The six-pixel click margin remains. Labels reserve their full rail rectangle but hang the box at its outward end, leaving a neck between the diagonal junction and the box. A passive three-pixel dot marks the leader base at the unpadded artwork bounds. Left/right placement mirrors correctly; empty/removed sites hide the label, line, dot and hit target together.

## Scope and material limit

ACE UI, original device textures, clinical logic, existing layout functions and native treatment/input handlers are unchanged. Public version/protocol are unchanged. BATDOK and Tempus Pro remain future interfaces with their own device references.

The window material is an opaque readable Dusk fallback, with opaque inner slate rows. It does not claim live scenery blur. The explicit CSS internal-backdrop capability remains unused in production. No DynamicBlur, camera effect, screenshot/capture loop, PiP, global postprocess or ACE/global control-class styling is added. Keep the experimental React option's existing default OFF.

## Verification

- 269 focused pytest cases pass, including post-handoff failure/session fencing, actual shipped-PAA decoding, both flag directions, dot placement, outline coverage, font admission, native snapshot projection, fallback and scope.
- 690 root cases and 43 Node cases pass. Strict HEMTT validates 2,139 SQFs, 15 stringtables and 22 configs. Native-owner audit: zero violations.
- Compiled-client browser checks pass at 360x227, 272x171, 210x132 and 522x226. A deliberately delayed font keeps cards and paint acknowledgment absent until readiness. An independent engine-advance fixture at 74% of nominal em produces the expected calibrated font instead of the previous nominal value. At each size, 25 updates preserve font size, DOM/image identity, focus, texture caching and fixed card dimensions. Successful post-handoff metric changes preserve mounted controls/focus without another font load; an invalid calibration requests native fallback once and retires browser input. Selection/keyboard routes and empty state pass. This models the contract; the 74% fixture is not a measurement of Arma.
- Hallmark app-scope static/render sweep: zero FAIL/WARN, one existing waived control-height finding for native full-height selectors. Scratch captures show the compiled card UI and a separately labeled native-texture compositor; neither is presented as an in-game capture.
- Fresh-context Hallmark finish review found a post-handoff font reloading/unmount risk. It was fixed by the one-time font load, synchronous remeasurement, mounted-card preservation and explicit session-bound fallback. The reviewer's rejection scenario plus successful geometry changes and invalid measurement are covered in the compiled browser checks. Finding scored resolved; live engine acceptance remains pending.
- Readability tests retain 4.5:1 normal text and 3:1 focus checks. No decorative motion or production backdrop filter is active.

A live Arma check is still required: compare native-only and React-enabled cards on the same patient at each UI scale, hold the menu through volume updates, scroll/change access, test piggyback, missing textures, fallback and multiplayer. The container cannot verify Arma CEF compositing, native font rasterization, physical DPI scaling, game input or runtime performance. Container packages omit Arma Tools model/animation binarization; the Windows helper runs native `hemtt release`.

Use the complete matching build/key on server, clients and headless clients; retain the persistence profile/adapter. Close Arma before deployment. Do not merge the draft PR until native acceptance is complete.
