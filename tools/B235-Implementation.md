# ACM Extended 1.2.4.1 / B235

Base: B234 `6b4b10343919b43d4a257112835292f5f2821743`.

## Requested workflow and corrections

The normal field conversion is now: a primary 14g/16g catheter, saline lock,
short Tegaderm, then a second 14g/16g catheter through the covered lock. The
existing manual advance, threading and safety-withdrawal controller remains in
use. A bare primary lock is rejected; a covered primary lock is required.
An accepted second catheter uses real stock and does not create another venous
access, wound, patency roll, or saline credit.

The short primary film persists under the secondary catheter. The original
`dressed` flag becomes available for the final, larger dressing over the
completed assembly; an optional seventh state entry retains the short film.
Older four/six-entry saved states remain readable. Outer-film removal preserves
the primary film; peeling again removes the primary film. Removing the second
catheter preserves the primary catheter, lock and original short dressing.
Removing the primary catheter or lock still removes all dependent hardware.

Mechanical fixation of the primary lock does not require a saline flush and
never implies that a compromised venous access is patent. Final tubing still
requires a successful check and final dressing. Existing direct/extension
routes and single successful 10 mL flush credit are retained.

## Geometry and rendering

Five native seated-hub texture families have calibrated sockets and axes,
separate from legacy floating-line anchors. The old left-15-degree anchor was
about ten source pixels right of the new collar-centered attachment point.
The hub artwork, insertion anchors and gauge-specific textures are not repainted.
The calibration uses the opaque downstream collar band, inset four source
pixels to overlap the male connector beneath the collar. Reproduce it with:

```powershell
python tools\measure_b235_hub_sockets.py --hemtt hemtt --verify
```

Installed lock/extension layers are created below the native hub; the primary
film lies below the secondary catheter and the final film above it. The
redundant topmost lock shell during insertion is removed. The held lock now
uses the same plain, physical-square picture class as the catheter/accessories.

Magnetic attraction uses a smooth distance curve over 5.2% of body-panel height,
with exact seating only within 0.4%. Rotation uses the shortest angular path.
Logical contact points, not arbitrary image centers, remain aligned while the
tool rotates. Cursor coordinates are not warped by hovering. Attachment clicks
use the near radius; a farther lock click is intercepted and cannot puncture the
skin underneath. Native mouse pinning after actual needle insertion is unchanged.

The IV tray uses the existing upright dedicated saline-flush item image. The
Narc Box's in-place size selector now switches to its existing dedicated
needleless flush barrel and restores the correct normal barrel when changing
back. Plunger motion, medication quantities and stock logic are unchanged.

## Validation boundaries

The test suite executes production SQF owner transactions, geometry, layer
selection, creation order, input and receipt guards in SQF-VM. Engine controls,
mouse input, scheduling, inventory transport and network boundaries are mocked.
Offline PAA composites are not screenshots from Arma. Native engine rendering,
Windows binarization and a real dedicated-server session must be checked after
local deployment. Consult the delivered validation report for completed test
counts and package checks; this implementation note is not a test-result claim.

The B234 tests retain their identities and assertions, with accepted field
fixtures explicitly dressed and the former covered-lock rejection changed to
an uncovered-lock rejection. Four existing build-marker tests advance to B235.
No unrelated debug layout, animation or physiology changes are included.

## Deployment

Import the B235 bundle into the existing continuation branch, then run
`tools\Deploy-ACME-B235.ps1` from the same `F:\ACM-Extended` checkout. The helper
runs Windows HEMTT check/release and verifies each copied file in both the repo
installation and existing `.hemttout\build` launcher directory. It refuses
source edits/unrelated untracked files rather than resetting them. It performs
no force push, source deletion, new worktree creation or Workshop publication.
Use matching complete builds on all clients, server and headless clients.
