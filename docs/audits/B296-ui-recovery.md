# B296 UI recovery

B295 changed ACE's medical menu and added glass decoration and scene blur outside the requested ACME scope. B296 reverts B295 in full before applying a narrow correction to ACME's existing visual state cues. Public version stays 1.2.4.1 and multiplayer protocol stays 2. This candidate belongs on the existing draft branch; it is not merged into main.

## Restored scope

The rollback index was exactly B294 tree `c95a9d1a8a4adbfc32ce590d49b0b12e154e09b3` before the B296 corrections. The ACE action renderer, ACME config, React component/store/styles/snapshot, native dialog integration, 81 transfusion PAA slices and generator are restored byte-for-byte to B294. All six B295 glass functions, 16 generated glass headers, registrations, dedicated glass refresh workers and scene-blur ownership are removed. No replacement blur is introduced.

The existing ACME transfusion layout and its in-place React card option remain. React is experimental and off by default: Addon Options > ACM Extended: Systems > Interface > React transfusion cards (experimental). It replaces only the two-card fluid viewport; the existing body map, access, inventory, infusion and Narc Box controls continue to use their existing native implementations. No new screen is added. This recovery does not claim a complete React migration or BATDOK/Tempus Pro integration.

## ACME flashing correction

Five existing ACME UI functions receive cosmetic changes:

- Transfusion and Narc Box navigation use steady accessibility-blue backgrounds.
- Entered tag content keeps a steady green Done button; empty tags retain their resting color and remain valid.
- Selected stock rows retain a steady green highlight.
- The two-press discard warning stays red without pulsing; confirmation logic is preserved.
- Compatible saline inventory stays green during pairing; other inventory colors are unchanged.
- Prime/Flush text and surface colors retain their semantic green/red distinction without oscillating opacity.
- Rejected Narc Box row selections show one continuous 0.36-second red indication instead of two flashes, with the original cleanup time.

Control constructors, IDs, rectangles, click callbacks, keyboard/wheel routes, custody, doses, clinical timing, networking, persistence and device artwork are preserved. Existing non-UI physiology and minigame motion are not changed. Original rounded, opaque ACME transfusion surfaces remain.

## Validation

The recovery manifest pins every B295-modified runtime surface to its B294 SHA-256 or requires its deletion, except the explicitly reviewed ACME corrections and build stamp. SQF-VM executes cue expressions across multiple times and Prime/Flush states, including the rejection interval, while engine drawing calls remain test boundaries.

The compiled offline React HTML was exercised in Chromium 143 in opaque-origin sandbox iframes at 360x227, 272x171 and 210x132. At each size, 25 consecutive volume/heartbeat snapshots preserve card DOM identity, the focused button, the image element, one cached texture request, stable background color and zero CSS animation/transition. Selection, native keyboard messages, font loading, empty access and viewport bounds pass. Existing bridge tests cover stale snapshots, pending acknowledgments, route tokens, changed contexts and native fallback. No browser screenshot is represented as an Arma render. The reproducible browser harness is `tools/verify_b296_browser.cjs` (run from the repository root with Playwright/Chromium installed; optional `ACME_PLAYWRIGHT_MODULE` and `ACME_CHROMIUM_EXECUTABLE` select the installed tools).

Local validation: 401 focused recovery/transfusion/selector pytest cases, 86 additional carousel/editor/staged-push/ACE-renderer/infusion-selection cases, 690 root pytest cases and 30 Node cases pass. Another 242 service and historical-carousel pytest cases pass with the updated steady cues (729 focused cases in total). Strict HEMTT compiles 2,138 SQFs, checks 15 stringtables and rapifies 22 configs. The native-state ownership audit reports zero violations. The downloadable signed build omits Arma Tools model/animation binarization; the Windows deployment helper runs native `hemtt release`.

## Installation and native acceptance

Fully exit Arma and local servers before installing B296, then restart. This clears an already-running B295 postprocess handle; replacing files while the old mission is running cannot unload its already-compiled scripts. Deploy the same complete 19-addon build and key on server, clients and HCs. Retain the existing server profile/persistence adapter and avoid duplicate standalone DD1380. B291 clinical additions and B292 fixes remain included; legacy FAK addons stay excluded.

```powershell
Set-Location 'F:\ACM-Extended'
git fetch origin
git switch fix/b205-network-continuation-20260930
git pull --ff-only origin fix/b205-network-continuation-20260930
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\Deploy-ACME-B296.ps1
```

Native Arma acceptance is still required. Check restored world visibility and ACE menu appearance, rapid hover/press and repeated opening of ACME menus, Prime/Flush and invalid selections, focus and held input, React startup/fallback, patient changes and multiplayer/HC. No claim is made that browser or VM tests certify the engine's rendering.
