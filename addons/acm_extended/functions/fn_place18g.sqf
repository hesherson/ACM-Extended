// place an 18g iv on a patient through ACM's own setiv, using gauge type 5, the ACME 18g. ACM ships 1 for 16g, 2
// for 14g, 3 for io-ez and 4 for io-fast.
// setiv stores the type into iv_placement[part][site], so getIVFlowRate and getaccesstype resolve it, and our
// getIVFlowRate wrapper gives type 5 a slower, smaller-bore flow. the 14g and 16g specific complication branches
// of ACM simply do not fire for it, which is graceful.
// ACE treatment actions are per body part rather than per ACM sub-limb site, so the site is bound per action. we
// expose lower and middle, the distal sites the danger model cares about, and full upper, middle and lower parity
// lives in ACM's body-image menu.
// _this is the ACE callback [_medic, _patient, _bodyPart] plus a bound [_accessSite].
params ["_medic", "_patient", "_bodyPart", "_args"];
_args params [["_accessSite", 2]];  // 0 upper, 1 middle, 2 lower.
if (isNull _patient) exitWith {};

if (([_medic, "ACM_IV_18g"] call ACME_fnc_itemCount) < 1) exitWith {
    ["No 18G catheter in inventory.", 2, _medic] call ace_common_fnc_displayTextStructured;
};

// 5 is the ACME 18g gauge type. the args are [medic, patient, part, type, state, isiv, accesssite].
// setiv runs ACM's own vein-finding success chance and shows "Failed to locate vein" on a miss, so we only announce
// success, and only consume the catheter as a confirmed stick, when an 18g actually landed at the site. a failed
// stick lets the message of setiv stand and wastes the catheter, like ACM.
if (!isNil "ACM_circulation_fnc_setIV") then {
    [_medic, _patient, _bodyPart, 5, true, true, _accessSite] call ACM_circulation_fnc_setIV;
    [_medic, "ACM_IV_18g"] call ACME_fnc_itemTake;
    if ([_patient, _bodyPart, 5, _accessSite] call ACM_circulation_fnc_hasIV) then {
        private _siteName = ["upper", "middle", "lower"] select _accessSite;
        [format ["18G IV: %1 %2.", _siteName, ([_bodyPart, "display"] call ACME_fnc_bodyPartName)], 2, _medic] call ace_common_fnc_displayTextStructured;
        [_patient, "activity",
 "%1 placed an 18G IV (%2 %3)",
 "18g IV, %2 %3, %1",
 [[_medic, false, true] call ace_common_fnc_getName, _siteName, [_bodyPart, "short"] call ACME_fnc_bodyPartName]] call ACME_fnc_medLog;
    };
} else {
    ["ACM IV system not found.", 2, _medic] call ace_common_fnc_displayTextStructured;
};
