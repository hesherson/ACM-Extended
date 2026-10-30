# B290 IV and transfusion presentation

Candidate identity: **1.2.4.1 / B290**, network protocol **2**. Based on B289
`aba3f6e61c723ade5456f333b932fe812370c318`. All clients, servers and headless
clients must run the same complete build.

## Behavior

- IV finishing tools use the existing catheter-tray label class, font, size,
  capitalization, stock-count spacing and unavailable-stock tint. Stock comes
  from real inventory for tubing, extensions, Tegaderm and saline locks.
- A line can connect mechanically to an installed bare catheter or downstream
  extension/lock port. Dressing, aspiration and patency do not gate physical
  attachment. Actual fluid delivery retains its existing patency checks.
  The bare-hub view displays tubing without inventing an extension.
- Plain prepared secondary bags are selected by their exact identity even when
  their backing native list is hidden behind cards. A loose saline secondary can
  be spiked and connected directly from piggyback mode, consuming one actual
  branch line. No medication record or admixture is needed.
- Delayed secondary attachment waits for native inventory custody and retains
  provider, access, primary-bag and lifecycle context. A changed workflow leaves
  the prepared secondary carried for a later deliberate connection.
- Transfusion windows, cards, popovers and buttons use the same corner radius.
  Paired actions and tabs have equal widths and consistent gaps; pressed labels
  stay aligned with their frames. The obsolete native remove control stays
  hidden alongside the current pull/return control.
- IV actions have one scripted sound per physical cue. Hang Bag preparation
  respects weapon-settling time, and repeated sound-session starts preserve
  the existing emitter.

React and Rust remain discussion proposals; this candidate adds neither runtime.

## Native acceptance

Automated source/geometry checks and SQF-VM execution do not verify Arma's
rendering, audible mix, animation interpolation or multiplayer transport. Check:

| Scenario | Expected result |
| --- | --- |
| Bare catheter, no extension/flush/dressing | Real tubing attaches; no phantom extension appears. |
| Extension and field-IV downstream catheter | Tubing uses the visible port; primary removal remains blocked until the secondary is out. |
| Compromised catheter | Mechanical connection succeeds; existing compromised-access flow rules remain effective. |
| Installed empty line | Its entry accepts a bag without charging another line. |
| Saline primary, plain prepared saline card | Exact selected bag attaches as secondary without making an infusion. |
| Saline primary, loose saline | Connect Piggyback consumes one bag and one line, then attaches after custody confirmation. |
| Change patient/access or cancel while preparing | No attachment to the replacement context; carried equipment is retained. |
| Duplicate request or delayed acknowledgement | No extra bag, tubing debit, emitter or treatment replay. |
| 4:3, 16:9, 21:9 and UI-scale extremes | Equal paired controls, matching circular corners, legible stock captions, no overlapping hits. |
| Holstered/rifle/pistol, standing/kneeling, start/cancel/restart | Clean treatment entry and exit, one cue per action, no late old-session pose. |

## Deployment

Use the existing persistence adapter and retain the server profile. Close Arma
and local servers, update the candidate branch, then run:

```powershell
Set-Location 'F:\ACM-Extended'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\Deploy-ACME-B290.ps1
```

The helper runs the build identity and HEMTT gates before journalled deployment.
This candidate is not a merged public release.
