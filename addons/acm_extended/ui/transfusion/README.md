# Rounded native transfusion surfaces

These code-drawn UI textures provide the neutral panel, card, and button shapes
from the approved transfusion concept. They do not replace ACM's body map,
IV/IO overlays, or medical item icons.

Each profile has nine 64 × 64 power-of-two PAA pieces, in this order:
`tl`, `top`, `tr`, `left`, `center`, `right`, `bl`, `bottom`, `br`.
Use the native path `\acm_extended\ui\transfusion\<profile>_<part>_ca.paa`.

The four corners must use equal physical pixel width and height. Stretch the
edge pieces only parallel to their borders and the center in both directions.
The source corner radius is 64 pixels and the source border width is 8 pixels;
at a rendered radius of 7 pixels, the border is approximately 0.875 pixels.
The alpha corners require ordinary `RscPicture` rather than KeepAspect. Static
picture controls must be disabled so they cannot capture medical input.

Profiles are `window`, `panel`, `button`, `selected`, `popup`, `piggyback`, and
`piggyback_selected`. State changes reuse the same controls and replace their
textures. The four corners carry DXT5 alpha; opaque pieces use DXT1. The complete
63-texture set totals 105,742 bytes before PBO packing.

Regenerate with Pillow and HEMTT:

```sh
python tools/generate_transfusion_chrome.py --hemtt /path/to/hemtt
```

Optional `--png-output /path/to/inspection` writes PNG copies outside the addon.
The JSON manifest records the palette and SHA-256 of every generated PAA.
The generator and checked-in assets were verified to regenerate byte-identically.
