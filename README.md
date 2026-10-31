# ACM-Extended
A massive overhaul to ACM.

## Branches and release builds

- `main` is the public 1.2.2 release source. The experimental drag handle has been removed; standard ACE dragging and carrying remain available.
- `dev` retains the experimental drag handle for `hemtt dev` or `hemtt launch` testing. Its build/release packages exclude the handle too.

Run these commands in PowerShell from your repository folder:

```powershell
git switch main
if ($LASTEXITCODE -ne 0) { throw 'Could not switch to main.' }
git pull --ff-only origin main
if ($LASTEXITCODE -ne 0) { throw 'Pull failed.' }
hemtt release
if ($LASTEXITCODE -ne 0) { throw 'HEMTT release failed.' }
```

## Release builds and experimental actions

`hemtt release` and `hemtt build` exclude Attach Drag Handle and Release Drag Handle, including when run from `dev`. The build hook removes the patient interactions, self interaction, medical menu rows and startup call before packaging. A release build fails if one of those entry points escapes filtering.

The experimental implementation remains on `dev`. Use `hemtt dev` or `hemtt launch` on that branch to test it. Standard ACE dragging and carrying remain available in release builds.

After rebuilding, replace the installed mod with the new release output and restart Arma. An existing installed 1.2.2 package is not changed by pulling source files.

## Patch notes

- [Cumulative 1.2.2 patch notes](CHANGELOG.md)
- [Discord posts and detailed patch records](docs/patch-notes/README.md)

## UI development

- [Shared React UI architecture for ACME, BATDOK and Tempus Pro](docs/design/react-medical-ui-architecture.md): future presentation contract, device/source associations, waveform rendering and native action boundaries. Preparation only; the game UI remains native.
