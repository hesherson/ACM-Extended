# B311 Tempus printed-panel artwork

Version 1.2.4.1 / B311 / network protocol 5. Based on B310. The world-equipment persistence contract and existing mission-adapter requirements remain unchanged.

## Findings and change

Both supplied colour atlases were 4096×2048 DXT1 textures with ten mip levels. Front-panel labels were already blurred in the highest source mip, and several key marks had very low contrast against their cap. The face shares its atlas with the rest of the case. Scaling the existing raster alone cannot reconstruct its lettering.

B311 adds editable, clipped UV-space vector marks for the main Tempus branding, selected power/key legends and numbered controls, with additional LS energy, charge and shock marks. The Pro's original RDT maker mark is retained. Lettering is converted to paths so the texture build does not depend on installed fonts; the outline source license is included. This is a targeted printed-detail pass, not a complete redraw of every surface or icon.

The colour atlas becomes 4096×4096 DXT1 with eleven square mip levels. Its source artwork still spans exactly the original normalized UV range. Increasing the vertical pixel count adds detail along that atlas axis; it does not increase both axes or recreate the original case's lost surface detail. Fully resident colour-texture memory including mip levels increases by approximately 5⅓ MiB per monitor (10⅔ MiB for the pair). The original author-supplied average-colour tag is preserved.

4096×4096 stays within the supported size described in Bohemia's [ImageToPAA documentation](https://community.bistudio.com/wiki/ImageToPAA). Texture visibility in-game still depends on engine streaming, texture settings, distance and lighting. No global graphics setting is forced.

The supplied Tempus models are ODOL version 75. The available HEMTT model-to-JSON reader accepts MLOD and rejects these ODOL inputs. This build preserves the supplied model bytes, normalized UV locations, materials, auxiliary normal/specular/ambient textures, screen/browser code, camera code and control hit areas. It does not claim a new UV layout or a native 3D-render acceptance result. Repacking the front into its own atlas would require suitable editable model sources and a separate model pass.

## Rebuild and evidence

The developer asset sources live under `tools/assets/tempus_panels`:

- `pro_base.paa` / `ls_base.paa`: exact original B310 colour textures.
- `pro_labels.svg` / `ls_labels.svg`: path-only artwork, each change clipped to its declared original-atlas rectangle.
- `FONT-LICENSE.txt`: DejaVu outline licensing.

To regenerate the committed runtime textures:

```text
python tools/build_tempus_panel_art.py --hemtt <hemtt-executable> --inkscape <inkscape-executable> --evidence <evidence-directory>
```

Ordinary HEMTT/Windows installation uses the committed PAAs and does not require Inkscape or fonts. The optional evidence directory contains full-size before/after control renders and a hash/UV-region report. Rendered comparisons use the identical base image and sampling geometry; changes outside the declared print rectangles must be exactly zero before DXT conversion. The native PAA roundtrip then checks opacity, dimensions, mip chain and bounded colour error.

Run the texture gates with `HEMTT` set to the converter path and `ACME_PANEL_EVIDENCE` set to that evidence directory. Existing Tempus clinical, charging/pacing, waveform, equipment transfer, world restore and deployment tests remain separate from the asset checks.

## Native acceptance

Inspect both monitors in Arma at close range and normal treatment distance, on terrain and a raised surface, with power off/on and different lighting. Verify branding, cap symbols, alignment, screen, tooltips and absence of interaction boxes; test texture-quality settings and streaming after moving away/returning. Confirm LS charge/armed indicators still use the existing materials. No Arma/dedicated-server or Windows session was available for this build, so those checks remain outstanding.
