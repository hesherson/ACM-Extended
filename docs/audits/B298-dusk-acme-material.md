# B298 Dusk material for ACME's existing React cards

Candidate 1.2.4.1 / B298, multiplayer protocol 2. This first Dusk pass changes only the existing ACME React fluid-card presentation and adds reusable scoped design rules. It does not restyle the native ACE menu or claim every ACME screen has been converted.

## Reference and method

The requested [Dusk page](https://www.usehallmark.com/themes/dusk/) uses smoked glass, a lit inner edge, a soft shadow and backdrop filtering. The published [Hallmark skill](https://github.com/Nutlope/hallmark/blob/main/skills/hallmark/SKILL.md) and its Dusk, app-screen, restyle and review guidance informed this pass. A scratch scaffold was generated from the original theme. Shared role tokens are in frontend/medical-ui/tokens.css, with application rules scoped to .acme-medical-surface. The existing Roboto Condensed and physical-pixel metrics are retained for native consistency rather than switching the embedded pane to a web-only face.

The theme is adapted for a working medical UI: denser surface opacity protects clinical labels over bright backing; native state colours remain native; geometry and all copy are preserved; no decorative motion is introduced. All CSS colours/fonts use tokens, including the native colour supplied through a CSS custom property. The theme source is not loaded from a CDN in game. The offline build embeds tokens, stylesheet, code and font with reproducible fingerprints.

## What blur can mean here

The [CSS Filter Effects draft](https://drafts.csswg.org/filter-effects-2/) defines a document backdrop root and filtering before composition. [Arma's browser control](https://community.bistudio.com/wiki/CT_WEBBROWSER) is a local sandboxed browser rendered into the UI; its documented interface does not expose the game's live framebuffer as a CSS backdrop. The practical conclusion for this implementation is that CSS cannot be relied upon to blur scenery or separate native controls behind the browser canvas. That limitation is an inference from the rendering/API boundary, not an Arma engine experiment.

True CSS blur is scoped to an explicit internal-backdrop marker. The current in-game pane does not set it, so its computed backdrop filter is none. It receives Dusk's smoked tint, lit edge, slate palette, restrained shadow and periwinkle focus treatment. Future ACME-owned layers rendered within a common browser may use the internal capability. No world/camera blur, capture loop, PiP camera, global skinning, extra native controls, refresh worker or page-reload path is added.

A browser-model check renders a transparent browser bitmap first and composites a separate striped background afterward. That background stays sharp (range 221, mean adjacent step 54.6), while the equivalent pattern rendered inside the browser is blurred (range 5, mean step about 0.21). This is a separate-surface model, not an engine test. A parent HTML page is deliberately not treated as the game world: Chromium can filter browser-owned parent content across an iframe, which would make that comparison misleading.

## Preserved contracts

App.jsx changes only the root scope class and native label colour plumbing through a CSS variable. Tests normalize those two presentation edits and require exact equality with B297. The store, metric calculation and all handlers are unchanged. All native runtime and original medical artwork remain unchanged except batch identity; no native texture or config styling is altered. B296's rollback and B297's update/first-paint/geometry fixes and IV/IO flag markers remain.

The material applies only when the existing experimental React card option is enabled and admitted. Native fallback retains the previous native appearance and workflow. Existing patient/provider identity, ownership, epoch and replay checks, clinical delivery, inventory custody, networking and persistence remain unchanged.

## Verification and limits

- 260 focused pytest cases, 690 root cases and 41 Node cases pass. Strict HEMTT: 2,139 SQFs / 15 stringtables / 22 configs. The native-state ownership gate reports zero violations.
- The original Hallmark static/render checks report 0 FAIL, 0 WARN and one reported waived Reflex finding: fluid cards retain their original full-card hit targets instead of adopting toolbar-button heights. Native geometry/spacing is also documented as intentional. A separate fresh-context finish review returned ship with no material/readability/focus/scope/regression findings.
- Contrast checks cover all card surfaces over black, mid-grey and white backings, requiring at least 4.5:1 for normal labels and 3:1 for focus. Native clinical colour plumbing is preserved. Default production filtering, animation and transitions compute to none; element opacity stays 1.
- Compiled HTML passes the existing browser harness at 360x227, 272x171, 210x132 and 522x226. Twenty-five updates at each size retain card/image elements, keyboard focus, texture caching, background colour and native dimensions. Selection, native keyboard messages, empty state and bounds pass.
- Hallmark captures render the actual compiled client with sample native-shaped packets, not a re-created product dashboard. Texture/network/Arma services are not running in those fixtures. Screenshots remain internal review material and are not presented as game renders.
- Signed-package, packed-source and exact source-patch tree checks accompany the downloads. Container builds omit Arma Tools model/animation binarization; the Windows helper runs native hemtt release.

Arma acceptance remains necessary for visual compositing, bright/dark terrain, focus/hover, repeated live updates, UI scaling, browser startup/fallback and multiplayer/HC. No claim is made that the model certifies the engine or that actual scenery is blurred. The rules in frontend/medical-ui/design.md apply to future ACME menu migrations; they do not authorize a redesign of third-party/device interfaces.

## Deployment

Close Arma and local servers, then:

```powershell
Set-Location 'F:\ACM-Extended'
git fetch origin
git switch fix/b205-network-continuation-20260930
git pull --ff-only origin fix/b205-network-continuation-20260930
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\Deploy-ACME-B298.ps1
```

Use the same complete 19-addon build/key on server, clients and HCs. Retain the existing server profile/persistence adapter and avoid duplicate standalone DD1380. The branch/PR remain draft and unmerged.
