# ACM Extended patch notes

The [cumulative 1.2.2 notes](../../CHANGELOG.md) combine all subsequent patches from 18–19 September 2026 through commit [8fd12c0](https://github.com/hesherson/ACM-Extended/commit/8fd12c016f17504b05781925f095d75f0fbe9424).

Version 1.2.2 includes the release check corrections and the complete RC1 patch series and updates the public, debug and build versions. Public releases use `main`, which excludes the experimental drag handle. The handle remains on `dev` for further work. Use the cumulative notes for current behavior. The dated records below retain the implementation history and validation details; later corrections supersede earlier descriptions, particularly seizure speed/startup and the subsequent removal of the drag handle from the public release.

`hemtt release` and `hemtt build` omit drag handle options on both branches. Experimental actions require `hemtt dev` or `hemtt launch` on the dev branch. Replace the installed mod with the newly generated release before restarting Arma.

## Discord copy

Each file below is one complete post under 4,000 characters. Copy the contents of each file as a separate message, in order. The @everyone mention appears in the first post.

- [Post 1 of 3](1.2.2-discord-1.txt) (3,942 characters)
- [Post 2 of 3](1.2.2-discord-2.txt) (3,888 characters)
- [Post 3 of 3](1.2.2-discord-3.txt) (3,932 characters)

The latest medication duration followup passed 25 focused checks on this branch. See the [input patch record](2026-09-19-push-duration-input.md) for scope and the remaining in-game checks.

The earlier [BVM startup followup](2026-09-20-bvm-startup.md) passed 95 focused checks on each branch and built 14 release PBOs per branch without binarization, signing or archiving. Live Arma multiplayer verification remains necessary.

The latest [native BVM restoration](2026-09-20-bvm-native-flow.md) passed 108 focused checks on each branch. Both branches built 14 release PBOs without binarization, signing or archiving. Live Arma multiplayer verification remains necessary.

The [stethoscope audio correction](2026-09-20-stethoscope-audio.md) passed 37 focused checks on each branch and restored all 21 original diagnostic gains. Both branches built 14 release PBOs without binarization, signing or archiving. In-game listening remains unverified.

## Discord format

Use this announcement format for release notes. Do not use em dashes or unnecessary hyphenation. Preserve exact version strings, technical identifiers, URLs and Markdown list markers. Keep section headings uppercase, include the repair reminder and documentation footer, and split long announcements into posts below 4,000 characters. Use the release's actual version in the title. Place @everyone in the first post of a multipart announcement.

```text
@everyone

# ACM Extended v{version} - Hotfix

:exclamation~1:Remember to repair your mod:exclamation~1:

## GENERAL FIXES

- {Change}

-# **[See documentation here](https://hesherson.github.io/ACM-Extended-Wiki/index.html)**
```

## Individual patch records

- [B275 connected transfusion menu](2026-10-11-b275-connected-transfusion-menu.md)
- [B274 transfusion menu corrections](2026-10-11-b274-transfusion-menu.md)
- [B273 transfusion menu and propofol bottles](2026-10-10-b273-transfusion-menu.md)
- [Stethoscope audio correction](2026-09-20-stethoscope-audio.md)
- [Restore ACM BVM flow](2026-09-20-bvm-native-flow.md)
- [BVM startup cancellation](2026-09-20-bvm-startup.md)
- [Chest seal burping without a timer](2026-09-20-burp-no-timer.md)
- [Repeat seal burping and Carry Assist release](2026-09-19-burp-carry-release.md)
- [Shared menus and death cleanup](2026-09-19-shared-menus-death-cleanup.md)
- [Bag visibility and CPR stop followup](2026-09-19-bag-visibility-cpr-stop.md)
- [Server bag visibility and BVM recovery](2026-09-19-server-bag-bvm.md)
- [Provider hold synchronization](2026-09-19-provider-hold-observers.md)
- [Release build drag handle exclusion](2026-09-19-release-drag-build-gate.md)

- [Medication push duration input](2026-09-19-push-duration-input.md)

- [Transfusion and thoracostomy](2026-09-19-transfusion-thoracostomy.md)
- [Patient motion and ketamine](2026-09-19-patient-motion.md)
- [Chest interactions, drag rope and held auscultation](2026-09-19-chest-interactions.md)
- [Final seizure speed correction, posterior auscultation and clinical descriptors](2026-09-19-auscultation-seizures.md)
- [PEA morphology](2026-09-19-pea-morphology.md)
- [Release check corrections](2026-09-19-release-warnings.md)
- [Release drag handle removal](2026-09-19-release-drag-removal.md)

The previous seal burping and Carry Assist patch passed 124 focused tests, including strict HEMTT checks and config compilation; one optional development package test was skipped. Both branches built 14 release PBOs without binarization, signing or archiving. The subsequent removal of the burping timer passed 25 focused checks on each branch, including strict HEMTT checks and config compilation. Pull `main` and rebuild to remove the drag handle, then verify gameplay in Arma. The earlier Windows release predates this removal. See the validation section in the main notes and the detailed checks in each patch record.
