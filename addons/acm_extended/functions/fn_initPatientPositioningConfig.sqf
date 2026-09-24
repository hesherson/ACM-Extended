/*
 * Phase 20 subsystem initialization: Head-elevation, patient posture and unconscious-positioning tunables.
 *
 * This is a behavior-preserving extraction from ACME_fnc_postInit. Keep runtime
 * event/PFH ownership in postInit or the owning subsystem; this helper only establishes
 * startup state and tunables in the same order as before.
 */

// head-of-bed elevation treatment, at about 30 degrees.
ACME_headElev_icpDropPerSec = 0.15;  // mmhg/s of ICP eased off while elevated, from venous drainage. it is above icprise, so ICP trends down.
ACME_headElev_mapDrop       = 6;  // mmhg of MAP haircut while elevated, which eases CPP down through gravity. set 0 to let CPP rise as ICP falls.
ACME_headElev_autoReleaseOnAnim = true;  // legacy compatibility knob; B70 uses the authored patient RTMs directly.
ACME_headElev_standTime   = 0.8;  // retained for visual-prop timing only.
ACME_headElev_transTime   = 1.8;  // legacy compatibility.
ACME_headElev_releaseTime = 2.6;  // legacy compatibility.
ACME_headElev_releaseAnimTime = 0.65;  // legacy cleanup compatibility.
// B70 does not geometrically attach/tilt the casualty. These remain defined only so old missions/tuners do not error.
ACME_headElev_tiltDeg     = 0;
ACME_headElev_faceDownTiltDeg = 30;
ACME_headElev_seqReleaseTime = 2.1;
ACME_headElev_pivotOffset = [0, 0, 0];
ACME_headElev_liftZ       = 0;
ACME_headElev_vestPropOffset = [-0.0624309, 0.327775, -0.262297];  // plate-carrier bolster offset in model space, spine3. this default is tuned for the head-elevated plate carrier prop.
ACME_headElev_vestPropPitch = -180;  // plate-carrier bolster orientation (deg). tuned default
ACME_headElev_vestPropYaw   = -9.52483;
ACME_headElev_vestPropRoll  = 0;
ACME_headElev_rollTime    = 0;  // seconds to let the roll-to-back settle before we pose a face-down casualty.
ACME_headElev_resumeDelay = 0.75;  // seconds after a maneuver ends before the casualty pops back up to elevated.
ACME_headElev_liftAnimTime = 1.2;  // measured length of the lift motion. it only sets how long the pin runs.
ACME_headElev_providerAnimSpeed = 1.5;  // how much faster the provider lift plays than its authored speed.
ACME_headElev_providerPinTime = 1.6;  // seconds the provider is held on the spot during the lift. 0 disables it.
ACME_headElev_pinTime     = 2.5;  // seconds the casualty is held on the spot while a grab or release RTM plays.
ACME_headElev_lowerAnimTime = 1.4;  // release-animation window used only for prop grounding; patient RTM is not cut off.
// 1.2.3 chest-access choreography is intentionally faster than Semi-Fowler positioning.
// The complete carrier-off transaction now finishes before medic4 reaches its 2.2 s held frame, eliminating the
// visible hands-on-chest pause before CPR/BVM/assessment launch without changing head-elevation timing.
ACME_chestAccess_vestLiftTime = 0.70;
ACME_chestAccess_vestLowerTime = 0.78;
ACME_chestAccess_vestLiftHold = 0.04;
ACME_chestAccess_vestRemoveAnimSpeed = 1.80;  // actual casualty grab/release RTMs during carrier removal.
ACME_chestAccess_providerAnimSpeed = 1.50;    // access-only provider medic4 theatre; reset before intervention launch.

// Putting the carrier back on is intentionally much faster than the old 1.2/1.4 second sequence. Match callback
// windows to the actual 1.60x patient animation instead of cutting the grab/release RTMs short.
ACME_chestAccess_vestRestoreLiftTime = 0.75;
ACME_chestAccess_vestRestoreLowerTime = 0.88;
ACME_chestAccess_vestRestoreHold = 0.02;
ACME_chestAccess_vestRestoreAnimSpeed = 1.60;
ACME_headElev_faceDownInvert = false;  // set true if face-down detection ever reads backwards in-game
ACME_headElev_restAnim    = "ACM_LyingState";  // on-back default state. the ACM lying pose, lower head and suspend all settle into it.
ACME_uncon_faceUp        = "ACM_LyingState";  // on-back default state, for the chest-seal front and the head-elevate release.
ACME_uncon_faceDown      = "ace_medical_engine_uncon_anim_1";  // real prone  unconscious rtm (chest-seal BACK)
