// thoracostomy mini-game, idd 86600.
["ACME_thoraAftercareAck", {_this call ACME_fnc_thoraAftercareAck;}] call CBA_fnc_addEventHandler;
// canvas scale, measured from the chest art. the areola at about 3 cm and the red zone width both give about
// 60 px/cm on the 2048 canvas. incision lengths are authored in cm and convert through this, so they stay
// correct at any canvas size. an ideal cut of 2 to 3 cm gives full marks. the hard cap is 5.08 cm.
ACME_thora_pxPerCm = 60;
ACME_thora_incisionIdealCm = [0.9, 1.3];
ACME_thora_incisionMaxCm = 2.2;
// 5th ics palpation accept ellipse per side, in body fraction [centeru, centerv, radiusu, radiusv]. these come
// from the red zone reference art. the right center is about 48.2 percent by 44.3 percent and the left is about
// 51.5 percent by 44.3 percent, at about 209x187 px on 2048.
ACME_thora_zoneRight = [0.482, 0.443, 0.055, 0.050];
ACME_thora_zoneLeft  = [0.515, 0.443, 0.055, 0.050];
// 5th ics as a rib curve per side: [centeru, centerv, slope, curvature, halfspanu]. the palpation target is a
// random point along this curve, picked once per patient. the accept strip is narrow across the rib, zoneperp,
// and wider along it, zonealong, so it follows the rib and stays hard to find.
ACME_thora_ribRight = [0.482, 0.443, 0.40, 2.0, 0.05];
ACME_thora_ribLeft  = [0.515, 0.443, -0.40, 2.0, 0.05];
ACME_thora_zoneAlong = 0.045;
ACME_thora_zonePerp  = 0.011;
ACME_thora_prepArmMargin = 0.06;  // chlorhexidine prep is cut off this far below the 5th ics rib curve, which keeps it off the arm.
ACME_thora_fingerPushScale = 0.85;  // the finger sprite shrinks to this while lmb is held, which gives a sense of pushing in.
// passive heimlich drainage. this is the pleural blood drained per minute while a tube sits in, and the
// seconds between ground blood pools.
ACME_thora_passiveDrainPerMin = 0.12;
ACME_thora_bloodStainInterval = 6;
ACME_thora_maxBloodDecals = 16;  // cap on ground blood decals per patient
ACME_thora_bloodGap = 0.2;  // minimum extra spacing between decal footprints. they glitch when they overlap.

// B35 PTX injury and decompression use compile-time breathing overrides.
// One owner-local model governs progression, relief and durable stabilization.
// the 5th ics guide box is for debug only. it renders when the debug menu, ACME_debug_enabled, is on and this
// is true. it stays off in normal play, so the medic palpates by feel.
ACME_thora_showZone = false;
// incision. this is the ideal transverse, rib-following, cut angle per side in body fraction canvas degrees.
// tune it in game once the cut shows against the rib art. the start radius sets how near the marked 5th ics the
// cut must begin.
ACME_thora_ribAngleRight = 25;
ACME_thora_ribAngleLeft  = 155;
ACME_thora_incisionStartRadius = 0.06;
// the minimum prep dots within about 0.12 uv of the incision start that mark the site as prepped. below this
// value an incision seeds infection and the casualty needs antibiotics.
ACME_thora_prepMinPoints = 8;
// kelly clamp opening overlay size, in body fraction. the finger uses the incision length instead.
ACME_thora_kellyOpenW = 0.05;
ACME_thora_kellyOpenH = 0.09;
// clean pre-baked hole frames. set this true after you convert thora_hole_00..11_ca.png to .paa into
// acm_extended\ui. until then the mod uses the procedural dot hole.
ACME_thora_useHoleFrames = true;
// hole frame angle trims. the offset shifts the base vertical mapping. the sign flips it if the diagonals come
// out mirrored.
ACME_thora_holeFrameOffset = -90;
ACME_thora_holeFrameSign = 1;
// set this true after you convert thora_hole_wide_00..11_ca.png to .paa. the finger then widens the hole
// instead of only enlarging it. until then the finger reuses the narrow frames at a larger size.
ACME_thora_useWideFinger = true;
// pink pleura bed, the right-click split open of the incision. convert thora_pleura_00..11_ca.png to .paa in
// acm_extended\ui. pleurascale sizes it against the cut. the kelly and finger holes render smaller so they stay
// inside it.
ACME_thora_usePleura = true;
ACME_thora_pleuraScale = 0.94;
// rotatable opening, a drawicon on a transparent map. set rotateopening false to fall back to the fixed
// vertical RscPicture hole. flip openanglesign if the rotation is mirrored. openangleoffset trims the base
// angle, opendrawscale trims the size, and openaspect is the hole height against width.
ACME_thora_rotateOpening = true;
ACME_thora_openAngleOffset = 90;
ACME_thora_openAngleSign = -1;
ACME_thora_openDrawScale = 1.0;
ACME_thora_openAspect = 1.6;
// chest tube. this holds the snap radius in uv onto the incision center, the seated art size as a body height
// fraction, and the anchor point within the art as a fraction of w and h. the anchor is the tape and entry
// corner, and it seats on the incision, per side. all of it is tunable.
ACME_thora_tubeSnapR = 0.055;
ACME_thora_sealSnapR = 0.085;  // B120 chest seals magnetize more generously to the exact center of the finger-thoracostomy opening.
ACME_thora_tubeSize = 0.34;
ACME_thora_tubeAnchorRight = [0.154, 0.215];
ACME_thora_tubeAnchorLeft  = [0.831, 0.215];
// cursor sprite anchor per tool, [u,v]. this is the point on the art that sits on the cursor, the business end.
// chlorhexidine uses the pad tip at the top, the scalpel uses the blade tip, the kelly uses the clamp tips and
// the finger uses the fingertip. the tube uses the side-specific tube anchor above, the middle of the white
// tape. all of it is tunable.
ACME_thora_toolAnchors = createHashMapFromArray [
    ["chlorhexidine", [0.548, 0.14]],
    ["scalpel",       [0.500, 0.50]],
    ["kelly",         [0.521, 0.30]],
    ["finger",        [0.500, 0.03]]
];
