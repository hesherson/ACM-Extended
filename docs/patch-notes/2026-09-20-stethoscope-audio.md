# ACM Extended 1.2.2: stethoscope audio correction

## Changes

- Restored the original `db+16` gain for all 21 diagnostic sound variants: nine heartbeats, nine normal/shallow/dull breaths and three crackling breaths. This reverses the unintended 6 dB reduction in the September 19 auscultation patch.
- Reduced the existing surrounding audio level from `0.2` to `0.1` while using the stethoscope. Closing or cancelling the scope still restores ACE hearing protection settings through the existing cleanup.
- Routed the local diagnostic emitters through the speech channel so ACE's reduction of surrounding effects does not also turn down the chest sounds. The existing continuous crossfades, front/back views and clinical sound modifiers remain in place.

Version remains 1.2.2. This correction supersedes the diagnostic volume reduction described in the earlier auscultation patch record.

## Implementation references

Original diagnostic gains were checked against the parent of commit `cecb4747ad770769755f334925720fcb081b749b`, which introduced the reduction. The [ACE hearing mixer](https://github.com/acemod/ACE3/blob/master/addons/common/functions/fnc_setHearingCapability.sqf) changes effects, radio and optional music volume. The [command documentation snapshot](https://github.com/acemod/arma3-wiki/blob/dist/commands/fadeSpeech.yml) identifies `say3D` with `isSpeech = true` as using the separate speech channel.

## Validation

The stethoscope audio correction passed 37 focused checks on each branch, including chest interaction contracts, treatment cleanup, strict HEMTT diagnostics and complete config compilation. All 21 diagnostic gains were compared with the original source and match exactly. Both branches built 14 release PBOs without binarization, signing or archiving. In-game listening remains unverified.

In-game listening is still required to judge the final audio balance. Check normal heart and breath sounds, shallow/dull breath findings, crackles and front/back crossfades while nearby environmental sounds are active. Close the scope and confirm the usual outside volume returns.
