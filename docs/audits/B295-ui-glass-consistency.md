# B295: consistent rounded glass surfaces

Candidate **1.2.4.1 / B295**, multiplayer protocol **2**, **19 addons**.
Baseline: `d7949abaed921628b670b41dae988025dca02837` (B294).

## Authorized scope

Keep the existing screens and workflow. Apply the same rounded-corner rule to
ACME menu surfaces, and add a subtle glass appearance with background blur.
No alternative design from the prior concept comparison is implemented.

This is an appearance pass, not another screen migration. Original native
controls retain their class, IDC, rectangle, text, font, size, actions, selection
logic and hit areas. No inventory, clinical, animation, timing, network or
persistence behavior is changed. The public version stays **1.2.4.1**.

## Rendering

The existing native nine-slice renderer remains the single corner owner:
`safeZoneH * 0.007`, quantized to one shared integer pixel radius on both axes,
clamped only where a control is too short/narrow. The PAA surfaces preserve
their existing RGB palette while their fills become translucent. React receives
the same native pixel radius; its existing cards use translucent fills and a
quiet inner highlight. Card geometry and typography remain unchanged.

Static decorative pools cover ordinary buttons and panels in sixteen custom
menus, including the roller clamp, syringe kit, IV/chest-seal/thoracostomy/
laryngoscopy trays, cooler, fridge, training panels and tuners. Native narc-box,
main medical-menu body panels and stethoscope controls use the same renderer.
Existing transfusion surfaces already use it. Dynamic narc-box rows, headings,
list fields, tag selectors, duration input, page-button backings, finishing trays
and main-menu action rows create their decorator **before** their original
control. The original control remains the top input surface.

All decorators and their nine picture children are disabled for input. Original
controls are never recreated during painting. Visibility, enabled state, fade,
semantic background colors and live geometry are read from those controls.
Deleted dynamic rows retire their decorative controls. Only a display-local
visual refresh runs while a registered menu is open; it retires on unload.
Repeated geometry/texture writes use the existing change-only native renderer.

Physical equipment artwork, LCD/front-panel designs, anatomy, pressure gauges,
trace marks and invisible procedure hotspots retain their original shapes.
Native third-party chrome and internal list-row/selection rendering remain
native; this does not globally patch Arma or other mods' base controls. Native
fonts and dimensions are preserved rather than imposing a new layout.

## Blur boundary and lifecycle

Arma's local DynamicBlur post-process supplies a subtle **0.35** scene blur.
This blurs the **3D scene**, including the area outside menu panels; it does not
blur other native UI controls or the text. Chromium CSS cannot sample the Arma
world behind its control. This is not a claim of per-panel masked backdrop blur.

One addon-owned effect is shared across open ACME menus. Closing an older menu
does not release a newer menu's interest. Final close destroys only the owned
handle. Allocation tries at most eight priorities with a two-second retry
throttle. If the existing ACME night-vision focus effect is active, the glass
pass yields to it rather than stacking another blur. It never adjusts or
destroys that effect or another mod's handle. Allocation failure leaves the
controls usable. No global idle display scan, camera replacement or render-to-
texture capture is introduced.

## Validation and remaining engine acceptance

The B295 scope gate compares current config against B294 and requires existing
non-appearance properties, including geometry, IDs, text, fonts and actions, to
match. Existing onLoad work must remain present before the visual registration.
It also compares the affected native UI functions token-for-token after removing
only the decorative constructor/registration calls.

SQF-VM executes nested-menu blur ownership, repeated close, foreign/NV effect
protection, bounded allocation failure, native factory class/IDC/parent/order,
frame geometry, visibility, disabled fade and stale-row cleanup. Existing
transfusion geometry, input, custody, menu renderer and narc-box regressions
remain active. The historical stock-header fixture treats the added decorator
as an engine presentation boundary while retaining its original header/count/
position assertions. Native PAA checks now expect the explicitly translucent
fill instead of the former opaque center; neutral RGB and transparent rounded
corners are still required.

Strict HEMTT, the native-owner audit, browser/store checks and bundle
reproduction are required. `tools/generate_ui_glass_headers.py --check`
reproduces the static frame pools. `tools/generate_transfusion_chrome.py`
reproduces all 81 PAA slices from the committed palette. It converts into a
fresh temporary output before replacing a committed PAA, avoiding stale output
when a destination already exists.

The compiled React HTML was exercised at the same three card-viewport sizes as
B294. Actual embedded/native compositing, panel readability over bright/dark
terrain, NVG, field visibility during procedures, native pointer/focus delivery,
rapid open/close, child dialogs and performance still require Arma testing.
The candidate stays draft and unmerged. Container builds omit native Arma Tools
model/animation binarization.

## Deploy

Close Arma and local servers, preserve local edits, then:

```powershell
Set-Location 'F:\ACM-Extended'
git fetch origin
git switch fix/b205-network-continuation-20260930
git pull --ff-only origin fix/b205-network-continuation-20260930
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\Deploy-ACME-B295.ps1
```

Use the same complete build on server, clients and HCs. Keep the existing server
profile/persistence adapter and avoid a duplicate standalone DD1380. The
existing **React transfusion cards (experimental)** option remains opt-in and
unchanged; native menus also receive the appearance pass.
