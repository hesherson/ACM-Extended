# B154 UI validation

Base: published B153 `299582f26da76e4eb7115fbb10f0bafeb0a0ccd1`.

## Defects reproduced

- HEMTT 1.22.0 reads B153's generated tray PAA as DXT5 with **0 mipmaps**. Adding only a valid OFFS index to the same compressed pixel blocks changes its result to **8 mipmaps**. All 20 regenerated B154 textures have eight indexed mipmaps and independently decode to visible catheter artwork through HEMTT. The earlier sequential pixel decoder did not test this loader boundary.
- Executing the original hover SQF with recorded UI commit boundaries passes 20 stock/position/exit cases but fails first-reveal checks for all four gauges. Its visible transition starts at UI (0,0) and moves to the tile. B154 passes all 24 cases, with the badge placed before text/reveal and no eased position transition.

## Automated checks

One combined run: **192 tests passed, 10 subtests passed**, zero failures or skips. It includes:

- IV container structure, independent HEMTT loading, source-pixel proportions, fan bounds and runtime hover lifecycle.
- Single debug option/no pages, delegation, transparent control reuse/replacement, cleanup, yellow headings/spacing, escaped full names, row-width fitting and block-height fitting with explicit engine metric substitutes.
- Current 1.2.3 hotfix and CPR/chest-access assertions; debug assessment, seizure and integration contracts; settings authority and version checks.

Reproduction from the repository root, with `HEMTT_BINARY` and `SQFVM` pointing to the installed executables:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest -p no:cacheprovider -q \
  addons/acm_extended/tools/test_iv_tray_hover_runtime.py \
  addons/acm_extended/tools/test_iv_tray_geometry.py \
  addons/acm_extended/tools/test_iv_tray_paa_container.py \
  addons/acm_extended/tools/test_iv_ui_followup_patch.py \
  addons/acm_extended/tools/test_123_player_facing_hotfix.py \
  addons/acm_extended/tools/test_123_cpr_bvm_chest_access.py \
  addons/acm_extended/tools/test_debug_single_overlay.py \
  addons/acm_extended/tools/test_build_version_tag.py \
  addons/acm_extended/tools/test_bug_audit_batch10_integration.py \
  addons/acm_extended/tools/test_bounded_assessment_contracts.py \
  addons/acm_extended/tools/test_seizure_paralysis_suppression.py \
  addons/acm_extended/tools/test_b20_vent_debug_narcbox.py \
  addons/acm_extended/tools/test_settings_authority.py
```

The public-version gate and `git diff --check` also pass. Independent review found all ten clinical and five network sections retained. SQF execution used SQF-VM with explicit substitutes for native UI, inventory and object commands; it does not render Arma UI.

## Release build

HEMTT **1.22.0**, `hemtt release --no-bin --no-archive`: **1,634 SQF files**, **16 configs**, **12 stringtables**, **14 PBOs**. The build succeeds with existing lint suggestions and bundled wiki metadata fallback. All 20 packaged tray assets and six key packaged runtime sources match the patched source byte-for-byte. Generated Python caches are excluded from the final build inputs.

This Linux build does not run the Windows model/animation binarizer. Use ordinary `hemtt release` for the Windows deployment build. In-game confirmation remains required for texture display and debug text on the reported ultrawide/FOV settings.

## Format reference

The [Bohemia PAA format reference](https://community.bistudio.com/wiki/PAA_File_Format) describes the OFFS index as 16 absolute mipmap offsets. This investigation demonstrates the B153 container's incompatibility with the independent loader; it does not claim that every historical PAA reader universally requires that tag.
