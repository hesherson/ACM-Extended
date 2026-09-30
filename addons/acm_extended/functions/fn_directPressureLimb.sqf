// Limb and head direct pressure is a non-exclusive one-handed hold. The provider can continue medical care while
// pressure remains clinically active. Movement yields the pose and pressure effect, and the hold reapplies once the
// provider settles again. Ordinary treatment animations may replace the pose without blocking their actions.
params ["_medic", "_patient", "_bodyPart"];

_medic setVariable ["ACME_DP_Active", true, true];
_medic setVariable ["ACME_DP_Patient", _patient, true];
_medic setVariable ["ACME_DP_Part", _bodyPart, true];
_medic setVariable ["ACME_DP_Mode", "limb"];
_medic setVariable ["ACME_DP_Start", CBA_missionTime];
_medic setVariable ["ACME_DP_NextClot", CBA_missionTime + 15];
_medic setVariable ["ACME_DP_Paused", false];
_medic setVariable ["ACME_DP_InPose", false];
_medic setVariable ["ACME_DP_IdleStart", CBA_missionTime];
_medic setVariable ["ACME_DP_LastPos", getPosASL _medic];
_medic setVariable ["ACME_DP_LastPoseAssert", 0];
_medic setVariable ["ACME_DP_ClinicalYield", false];
_medic setVariable ["ACME_DP_ClinicalYieldStart", 0];
_medic setVariable ["ACME_DP_OwnsContinuous", false];

// Direct pressure over a fractured limb is a severe pain stimulus. Run it on the patient owner so ACE pain and
// wake-state changes remain local-authoritative. The handler itself is edge-triggered and cooldown-gated.
if ([_patient, _bodyPart] call ACME_fnc_directPressureHasFracture) then {
    ["ACME_DP_fracturePain", [_patient, _bodyPart, _medic], _patient] call CBA_fnc_targetEvent;
};

// Enter the held pressure pose directly. Direct Pressure deliberately does not call medicAnimationPrep or issue
// weapon-selection commands; another treatment or movement may supersede this pose normally.
if (isNull objectParent _medic) then {
    _medic setUnitPos "MIDDLE";
    _medic setVariable ["ACME_DP_PoseToken", (_medic getVariable ["ACME_DP_PoseToken", 0]) + 1];
    _medic setVariable ["ACME_DP_PoseGraceUntil", CBA_missionTime + 0.15];
    [_medic, "ACME_DirectPressureHold", 1.1, 1] call ACME_fnc_doAnimHeld;
    _medic setVariable ["ACME_DP_InPose", true];
    _medic setVariable ["ACME_DP_LastPoseAssert", CBA_missionTime];
};

// Direct Pressure has no keyboard cancellation binding. MMB is handled by the mission-display guard; the explicit
// Stop Direct Pressure menu action is the deliberate UI fallback. Escape/H remain available to the player.
_medic setVariable ["ACME_DP_KeyIDs", []];
["", "Stop Direct Pressure", ""] call ace_interaction_fnc_showMouseHint;

private _partShort = [_bodyPart, "abbr"] call ACME_fnc_bodyPartName;
[_patient, "activity",
 "%1 started Direct pressure on %2",
 "%1 started Direct pressure on %2",
 [[_medic, false, true] call ace_common_fnc_getName, _partShort]] call ACME_fnc_medLog;

// Publish the clinical pressure marker only after provider-local episode state is fully initialized.
[_patient, "directPressureMarker", [_medic, _bodyPart, true, _medic getVariable ["ACME_DP_ClaimToken", ""], _medic getVariable ["ACME_DP_ClaimEpoch", -1]]] call ACME_fnc_ownerDispatch;

private _pfh = [ACME_fnc_directPressureTick, 0, [_medic, _patient, _bodyPart, "limb"]] call CBA_fnc_addPerFrameHandler;
_medic setVariable ["ACME_DP_PFH", _pfh];
