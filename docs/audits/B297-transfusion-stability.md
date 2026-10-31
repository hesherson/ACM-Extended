# B297 transfusion stability and access markers

Version 1.2.4.1, multiplayer protocol 2, draft candidate. B296's glass rollback and steady ACME button colors remain. ACE's medical menu, clinical state, fluid delivery, inventory custody and treatment actions are unchanged.

## Report and correction

The supplied screenshots show incomplete live fluid cards and the desired native card appearance after patient death. Death invalidates the captured React context, restoring the native pool. That identifies the two rendering paths; it is not proof of one particular engine failure.

The browser path compared authored floating-point rectangles with engine-returned control positions, allowing repeated commits if the engine rounded them. B297 caches the requested rectangle and writes it only on a real layout change. The initial browser rectangle is set to its final dimensions before loading the HTML. Live snapshots are bounded to 10 Hz; unchanged state retains its two-second heartbeat. Clinical delivery timing is untouched.

The initial ready message no longer hides native cards. A separate, session-bound `painted` message follows a committed React tree. Native cards retain the pane until this acknowledgment arrives. Startup or missing paint times out to the native pool in the same display, without reopening, adding workers or retrying loads. A new page resets the paint acknowledgment, and close retires it. Input remains fenced by the existing provider, patient, clinical/kit/locality epochs, owner, route token and replay checks.

The snapshot exports six bounded native pixel metrics: viewport width/height, safe-zone height, row height, row gap and quantized corner radius. React uses those metrics for card geometry, the same opaque colors, font sizes, artwork size, caption alignment, progress tracks and graduations. This replaces independent vh-based guesses that made the browser content larger than its native counterpart. The offline bundle also avoids requiring the newer `structuredClone` API.

## Access selection and flags

The IV/IO hit targets remain independently selectable, including EJ. Their rectangular hover/selection fills are removed. Nineteen passive white/green contours are derived from the original icon alpha masks, displayed on the same square KeepAspect canvas. Original artwork and hit bounds are preserved. The contours do not intercept input. They are rebuilt by `tools/generate_transfusion_access_outlines.py`; original/source and output hashes are recorded with the assets. EJ source artwork is reduced to the common 512px contour canvas for consistent stroke thickness.

Leaders originate at the upper outward corner of the icon's hit rectangle and meet the label's upper inner corner. Tags sit farther outward. Their top edge extends beyond the opposite corner to form a flag. The entire extended flag rectangle is reserved during collision placement, including the overhang, and remains within the body-map workspace. Bag/infusion labels, per-access selection and piggyback/Y identity remain native-owned.

## Verification

- 466 focused recovery, React bridge, native-card geometry, presentation, input, selector and infusion cases pass, plus four new full-flag placement cases across screen aspects (470 total).
- 690 root pytest cases and 41 Node cases pass. Strict HEMTT compiles 2,139 SQFs, checks 15 stringtables and rapifies 22 configs. Native-owner audit: zero violations.
- SQF-VM executes 100 rapid ticks: one browser rectangle write and bounded snapshot delivery, followed by a real layout change that produces exactly one additional rectangle write. Tests cover first-paint handoff, absent/invalid paint, timeout and context fences. Engine control drawing is an explicit test boundary.
- The committed Chromium harness exercises the compiled HTML in opaque-origin iframes at 360x227, 272x171, 210x132 and 522x226. At each size, 25 volume/heartbeat updates retain the same card/image elements, focus, cached texture and background, with no CSS transitions/animations. Native font/icon/radius/gap/row geometry is checked numerically. Only one paint acknowledgment is sent per session. Selection, keyboard delegation, empty-state rendering and bounds pass.
- The flag tests place all 19 sites at four screen aspects, retain the extended bounds and require the leader to start at the upper icon corner. Asset provenance and contour transparency are checked. Native ACE files and original medical artwork have no B297 diff; the only ACME config change registers the local geometry helper.
- Signed package validation and source-patch tree checks are recorded with the downloads. Container builds omit Arma Tools model/animation binarization; the Windows helper runs native `hemtt release`.

These checks do not certify Arma's CEF compositor. In-game acceptance remains necessary for continuous live updates, paused/dead patients, UI scales, hover/focus, slow HTML/texture startup, device icons, dense flags and multiplayer/HC. No claim is made that a container browser reproduces the engine's rendering failure.

## Deployment

Close Arma and local servers, then:

```powershell
Set-Location 'F:\ACM-Extended'
git fetch origin
git switch fix/b205-network-continuation-20260930
git pull --ff-only origin fix/b205-network-continuation-20260930
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\Deploy-ACME-B297.ps1
```

Deploy the same complete 19-addon build/key to server, clients and HCs. Retain the existing persistence adapter and server profile. Do not load duplicate standalone DD1380. React remains the existing opt-in transfusion-card setting, not an additional screen or full-menu rewrite. BATDOK/Tempus Pro remain future interfaces.
