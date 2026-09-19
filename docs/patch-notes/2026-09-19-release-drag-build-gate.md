# ACM Extended 1.2.2: release build drag handle exclusion

## Problem

The earlier removal applied to main. The dev branch retained the experimental actions, and running `hemtt release` from dev still packaged them under version 1.2.2. The version label alone did not distinguish those packages.

## Changes

- Added a HEMTT pre_build hook on both branches. Build and release output omit Attach Drag Handle, Release Drag Handle, the self release interaction, the medical menu rows and the drag runtime startup call.
- Made the build stop if one of those entry points remains outside the development blocks.
- Kept development actions available only to `hemtt dev` and `hemtt launch` output on the dev branch. Main still excludes the experimental implementation entirely.
- Added a default-off compiled development flag. Retained dev startup and attachment functions reject nondevelopment builds before registering handlers, dispatching requests or modifying patient/provider state. Mission drag settings cannot bypass this restriction.
- Applied filtering to HEMTT's virtual build files, preserving the checked-out dev source.
- Preserved normal ACE dragging/carrying, Get Up and head elevation transport handling. Version remains 1.2.2 with build metadata 1.2.2.0.

## Validation

HEMTT 1.21.0 produced 14 release PBOs from main and 14 from dev using `hemtt release --no-bin --no-sign --no-archive`. The extracted binary config contains none of the three drag handle action classes and has the development flag set to zero. The extracted GUI renderer contains no Attach or Release Drag Handle rows, and the extracted startup script contains no drag runtime installer call. Get Up and ordinary transport handling remain present.

A separate `hemtt dev` build retained all three action classes, the medical menu rows and installer call, with its compiled development flag set to one. The source config remained zero after all builds.

Main passed 9 checks, with one development-package check skipped because main intentionally lacks that implementation. Dev passed all 21 checks. Both included strict HEMTT diagnostics and full config compilation. The development build reported that Arma was unavailable for creating its local game link; the PBO build completed.

Full Windows asset binarization, signing, archive creation and in-game verification were not performed here. Build the public package with normal `hemtt release`, install the newly generated output and restart Arma. Confirm that the patient, self interaction and medical Drag/Carry menus have no drag handle options.

## Build mechanism

The hook uses HEMTT's [build mode checks](https://hemtt.dev/rhai/library/hemtt.html) and [virtual file system](https://hemtt.dev/rhai/library/filesystem.html). Filtering runs in [pre_build](https://hemtt.dev/rhai/hooks/index.html), before configs and scripts are packed into PBOs.
