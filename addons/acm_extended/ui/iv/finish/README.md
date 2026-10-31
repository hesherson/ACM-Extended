# B232 IV finishing artwork

Runtime textures are converted from the user's `ACME_IV_Extension_Flush_Base_v1.zip`
(version 3 of the Library file, internal manifest revision 4). Exact input hash and
all output hashes are in manifest.json. The original 2048px assets are downsampled
to 1024px for animation; tool icons use transparent 256px crops.

The original gauge-specific native catheter hub is retained under these layers.
The supplied hub is removed from composite animation frames so it does not replace
another gauge/angle. A square physical-pixel canvas rotates around the authored
insertion anchor, not the image center. No font files are embedded.

Sequence filenames use four-digit, zero-based suffixes at 30 fps:

- extension_attach: 24 frames
- iv_line_attach: 30 frames
- blood_return_flush: 180 frames
- resisted_no_return: 120 frames
- post_flush_secure: first 42 frames only (unlock, withdrawal, disappearance)
- tegaderm_apply: 36 dressing-only frames

The good branch plays blood_return_flush then post_flush_secure. The missed
branch plays resisted_no_return then reverses its shared full-syringe connection
frames 47..0. It does not play an empty syringe or inject fluid. Dressing is its
own selected tool, after the syringe is removed.

The last six removal frames multiply opacity across the entire withdrawn syringe;
this corrects the raw renderer's opaque piston during the disappearance phase.
The decoded final PAA is checked against the static extension for ghost remnants.

Native Arma visual blending/texture streaming still needs gameplay validation.
