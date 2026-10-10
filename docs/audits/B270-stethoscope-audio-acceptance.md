# B270 — Stethoscope playback and contact recovery

Candidate **1.2.4.1 / B270**, protocol **1**, based on B269 `682e1e18420390cc435fd35c18d35c35debe20bc`.

## Report and reproduced source defects

The B201 report describes radio-volume dependence, intermittent missing lung/heart sounds and left-channel-only output on a local server. Its mod list includes both the original ACM and ACME. Controlled execution of production B201 and B269 audio code reproduces the same mixer selection, off-contact cadence advancement, failed-playback delay and resource-retirement defects. Native audio commands and UI delivery are explicitly adapted in these checks; they do not reproduce headphone output or establish that every reported silent interval has the same cause.

The previous backend launches spatial `say3D` sounds with its speech selector enabled. That puts auscultation on the speech/radio volume path. It also launches clips while the bell is lifted, with the emitter outside its declared audible range, and advances heart/breath deadlines even when playback has no audible contact or returns no usable source. Reacquiring contact can therefore wait until the next physiological cycle. The source proves this scheduling behavior; whether a particular native engine culled an out-of-range source at launch remains a listening-test question.

## Playback repair

B270 uses listener-local `playSoundUI` with explicit gain and pitch and the effects selector set to `false`. Its dedicated UI channel removes the dependence on the speech/radio mixer and camera-relative spatial emitters. The user's separate UI audio volume still controls this channel. The playback backend does not write global audio volumes; existing ACE surrounding-audio attenuation and its exit cleanup remain. The command, numeric IDs, offsets, `stopSound` and `soundParams` fit the project's minimum Arma 3 version **2.18**; no 2.22-only looping parameter is used.

The display owns its playback handles and retires them on contact loss, focus loss, flip, close and invalid-session retirement. Heart and lung cadence starts from audible contact rather than consuming hidden playback cycles. Failed playback has a bounded local retry. Front/back selection, anatomical weights, held-bell drag, shallow/dull gains, unilateral findings, basal crackles, heart-rate/breath-rate timing and clinical apnea/arrest/death silence remain the inputs to playback.

Captured display generations prevent a retired callback from clearing a successor's controller. Native numeric sound IDs have no documented generation token: path, clip length and monotonic progress checks reject observable ID reuse before stopping a voice. Indistinguishable reuse of the same recording at matching progress cannot be proven isolated from another addon's playback through this API.

Stable clips finish without per-frame restarts. Changing the gain of a live UI sound requires stopping and replaying at its current sample offset because Arma 2.18 has no documented per-handle gain setter. The implementation bounds these changes and preserves the current sample phase; decoder latency and audible transition clicks require native verification. Normal finite samples can end before the next heart/breath cycle, so an ordinary quiet interval during continuous contact is not itself evidence of a playback failure.

## Recordings and installation

All 18 inherited diagnostic WAVs match the supplied original ACM recordings. They are 44.1 kHz stereo with effectively equal left/right amplitude and positive near-unity channel correlation. The three added crackle OGGs are mono and non-silent. The supplied assets do not explain left-only output; removing the positional backend addresses that routing mechanism, while actual headphone balance remains a native acceptance check. No recordings are rewritten.

The three crackle classes regain `db+16`, matching the documented diagnostic-volume restoration in `dd93a756`. Commit `7407794e`, primarily an ACRE Babel removal, subsequently returned only those classes to `db+10` without accompanying gain-policy documentation. Restoring the established policy removes a 6 dB reduction in crackles; it does not explain all reported lung silence.

Original ACM and this complete fork share `x\\ACM` resource paths, patch identities, function names and sound classes. Load the complete ACME fork with the separate original ACM disabled, as the existing installation guidance requires. Their duplicate namespace makes combined-load resolution dependent on addon/file loading; this is not proof that the combined mod list caused every reported symptom. No fault is attributed to JSRS, EFAK or another listed mod without a reproducing native test.

Primary command references:

- [Bohemia playSoundUI](https://community.bohemia.net/wiki/playSoundUI)
- [Bohemia say3D](https://community.bohemia.net/wiki/say3D)
- [Bohemia getAudioOptionVolumes](https://community.bohemia.net/wiki/getAudioOptionVolumes)
- [Bohemia stopSound](https://community.bohemia.net/wiki/stopSound)
- [Bohemia soundParams](https://community.bohemia.net/wiki/soundParams)
- [Bohemia 2.12 release notes](https://dev.arma3.com/post/spotrep-00110)

## Native acceptance

On matching complete B270 client/server/HC packages, with original ACM disabled, verify:

1. Set radio volume to zero, then effects volume to zero independently, keeping UI volume audible. Listen to heart and both lungs, front and back. Confirm the UI slider controls the diagnostic channel and both headphones receive balanced output.
2. Lift the bell for several slow respiratory cycles, then place it on an audible lung point. Repeat with slow/normal/fast heart and respiratory rates. Confirm contact recovers promptly without reopening the display, while ordinary finite-clip gaps retain physiological timing.
3. Drag between strong and weak anatomical points and between unilateral findings. Listen for gain changes, duplicate beats, restarted inspirations or transition clicks. Check shallow/dull sounds and restored basal crackles separately from normal breathing.
4. Release the bell, alt-tab, flip, close and reopen repeatedly. Delete the patient while the display is open. Confirm old sounds stop, retired callbacks cannot affect a successor display and no diagnostic audio reaches another listener.
5. Verify apnea, cardiac arrest and death remain silent in their respective channels. Regress flip completion/cancellation, owner-refreshed lung state, chest access and provider/patient exit recovery.
6. Run a minimal CBA/ACE/ACME setup first, then the reported optional mods with original ACM still disabled. Record the exact build, UI audio settings, reproduction steps and fresh RPT if a symptom remains.

Automated evidence is reported with the exact candidate tree and immutable CI artifact. Native Windows build/signature verification, live dedicated-server/two-client/HC checks and clean RPT review remain required; this candidate is not certified for public release or universal multiplayer audio behavior.
