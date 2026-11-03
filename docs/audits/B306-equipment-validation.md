# B306 validation

The following checks ran against the B306 candidate source and packaged artifacts:

- HEMTT 1.23.1 `check --error-on-all`: successful; 64 configs/materials rapified, 2,225 SQF files compiled, 15 stringtables checked. The optional online wiki lookup fell back to the bundled command database. The documented CT_WEBBROWSER `JSDialog` name is assigned through a runtime variable because the bundled event table omits that valid event; no general unknown-event lint is disabled.
- HEMTT signed release, `--no-bin --no-archive`: 27 PBOs built. All 27 signatures verified against the generated public key. The journalled deployment artifact validator accepted the complete release set.
- All three packaged HTML files match the current source bytes; no stale hosted/demo copy was substituted.
- All 71 imported PAA textures decoded successfully. The original 18 MLOD models had previously passed complete structural parsing. The two compiled ODOL models are retained byte-for-byte.
- 98 retained B305 inventory/cooler tests passed in SQF-VM: inventory density/navigation, cold-chain backend, box transactions and persistence.
- 32 B306 tests passed in SQF-VM: demand/fixed pacing, insufficient current, off/disconnected/changed patient/epoch/arrest/no-pulse cases, stale/replayed/unauthorized/out-of-range shocks, native state restoration and cancellable physical power holds and forced browser waveform refresh.
- 45 build identity/deployment transaction/HPMK protection checks passed.
- Existing fluid-card browser checks passed at four viewport sizes.
- Embedded Pro/LS browser checks passed: native handshake, host samples, moving sweep cursor, twelve Pro diagnostic lead canvases, power and signal reset, without page errors. BATDOK's encoded ready handshake and native provider-state update passed.
- The retained exact asset-path gate passed: 287 macro references. HPMK's wrapped-object/physics isolation gate passed.

Native object, animation, control and network boundaries are mocked in SQF-VM. Chromium does not replace Arma's embedded browser integration. Windows/Arma/dedicated-server acceptance remains outstanding; see the patch notes for specific limits.

183 retained B300–B304 transfusion, pressure and litter checks passed after fetching their historical Git fixtures. Two historical scope guards now recognize the intentional B306 include/monitor changes; the litter guard compares against B305 so existing B304/B305 flow corrections are preserved. Together with the groups above, 358 targeted pytest checks passed.

Primary interoperability documentation: https://community.bistudio.com/wiki/CT_WEBBROWSER and https://community.bistudio.com/wiki/ctrlWebBrowserAction .
