# ACM-Extended
A massive overhaul to ACM.

## Release builds and experimental actions

`hemtt release` and `hemtt build` exclude Attach Drag Handle and Release Drag Handle, including when run from `dev`. The build hook removes the patient interactions, self interaction, medical menu rows and startup call before packaging. A release build fails if one of those entry points escapes filtering.

The experimental implementation remains on `dev`. Use `hemtt dev` or `hemtt launch` on that branch to test it. Standard ACE dragging and carrying remain available in release builds.

After rebuilding, replace the installed mod with the new release output and restart Arma. An existing installed 1.2.2 package is not changed by pulling source files.

## Patch notes

- [Cumulative 1.2.2 patch notes](CHANGELOG.md)
- [Discord posts and detailed patch records](docs/patch-notes/README.md)
