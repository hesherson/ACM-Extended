/*
 * Phase 20 subsystem initialization: Megacode Kelly training-manikin presentation and timing tunables.
 *
 * This is a behavior-preserving extraction from ACME_fnc_postInit. Keep runtime
 * event/PFH ownership in postInit or the owning subsystem; this helper only establishes
 * startup state and tunables in the same order as before.
 */

// megacode kelly tunables, for the zeus training manikin.
ACME_megacode_restAnim   = "ACM_LyingState";  // the pose the manikin is locked into. it never stands, crouches or prones.
ACME_megacode_animInTime = 1.6;  // seconds before the operator's radio-talk in -> loop hand-off
ACME_megacode_animOutTime= 1.4;  // seconds before the radio-talk out releases on panel close
ACME_megacode_sweepSecs  = 3.4;  // monitor sweep duration across one trace lane
ACME_megacode_waveCols   = 400;  // columns per waveform lane. a higher value is smoother with thinner steps. about 176 was blocky.
ACME_megacode_waveColSecs = 0.024;  // seconds per column, the sweep time-base. the window is wavecols times wavecolsecs.
                                             // beats across = window * hr/60. fewer secs or more cols packs in more beats and stretches less.
ACME_megacode_dummyHoseOffset  = [0, 0.32, 0.12];  // cable attach on the manikin (model space: chest)
ACME_megacode_laptopHoseOffset = [0.10, 0.152, -0.143];  // the cable port on the laptop, in its model space: the back face of the base (y 0.157), right of centre, mid height of the base as drawn (z -0.159..-0.128). +y after the 180 deg turn faces the manikin. measured from Land_Laptop_03_olive_F's geometry; see fn_megacodeCableBuild.
ACME_megacode_plugLength       = 0.036;  // how far out of the port, along the plug, the rope is anchored. the plug model ends at 0.042, so the rope starts inside it.
ACME_megacode_ropeClass        = "ACME_MegacodeCable_Rope";  // the thin dark cable. "ace_refuel_fuelHose" is the old thick hose.
ACME_megacode_ropeSlack        = 0.2;  // extra rope length beyond the plug-to-chest distance. this is the cable tuner.
ACME_megacode_ropeSegments     = 0;  // rope segment count (0 = engine default, max 63); cable tuner
ACME_megacode_cableBends       = [[0.34, 0.22], [0.68, -0.18]];  // B395: where the cable bends: [share of the way from the laptop, metres to the side]; [] lays it straight
ACME_megacode_laptopPosOffset  = [0, 0, 0];  // laptop-position offset in its heading frame (cable tuner).
ACME_megacode_laptopPitch      = 0;  // deprecated. the laptop orient was replaced by laptopposoffset and this is kept for back-compat.
ACME_megacode_laptopYaw        = 0;
ACME_megacode_laptopRoll       = 0;
ACME_megacode_deathTime  = 240;  // seconds pulseless, with no ROSC and CPR pausing the clock, before the manikin is declared dead.
ACME_megacode_deathBeat  = 3.0;  // seconds the flatline and unconscious death is held before the auto-reset.
ACME_megacode_scenarioPace = 1.0;  // scenario stage-time multiplier. 0.5 is twice as fast and 2.0 is half speed.
