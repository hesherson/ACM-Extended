// Limb and head direct pressure is a non-exclusive one-handed hold. The provider can continue medical care while
// pressure remains clinically active. Movement yields the pose, which resumes as soon as repositioning ends.
// Ordinary treatment animations may replace the pose without blocking their actions.
params ["_medic", "_patient", "_bodyPart"];
if (isNull _medic || {isNull _patient} || {!local _medic}) exitWith {};

_medic setVariable ["ACME_DP_Active", true, true];
_medic setVariable ["ACME_DP_Patient", _patient, true];
_medic setVariable ["ACME_DP_Part", _bodyPart, true];
_medic setVariable ["ACME_DP_Mode", "limb"];
_medic setVariable ["ACME_DP_Start", CBA_missionTime];
_medic setVariable ["ACME_DP_NextClot", CBA_missionTime + 15];
_medic setVariable ["ACME_DP_Paused", false];
_medic setVariable ["ACME_DP_InPose", false];
_medic setVariable ["ACME_DP_IdleStart", CBA_missionTime - 2];
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

// Capture the episode before the first delayed empty-hands request. Weapons remain holstered after movement.
_medic setVariable ["ACME_DP_PoseToken", (_medic getVariable ["ACME_DP_PoseToken", 0]) + 1];
_medic setVariable ["ACME_DP_PoseGraceUntil", CBA_missionTime + 0.15];
if (isNull objectParent _medic) then {[_medic, _patient] call ACME_fnc_directPressurePose;};

// Direct Pressure has no keyboard cancellation binding. RMB/MMB use the display guard; the explicit
// Stop Direct Pressure menu action is the deliberate UI fallback. Escape/H remain available to the player.
_medic setVariable ["ACME_DP_KeyIDs", []];
["", "Stop Direct Pressure", ""] call ace_interaction_fnc_showMouseHint;

private _partShort = [_bodyPart, "abbr"] call ACME_fnc_bodyPartName;
[_patient, "activity",
 "%1 applied direct pressure to %2",
 "%1 applied direct pressure to %2",
 [[_medic, false, true] call ace_common_fnc_getName, _partShort]] call ACME_fnc_medLog;

// Publish the clinical pressure marker only after provider-local episode state is fully initialized.
[_patient, "directPressureMarker", [_medic, _bodyPart, true, _medic getVariable ["ACME_DP_ClaimToken", ""], _medic getVariable ["ACME_DP_ClaimEpoch", -1]]] call ACME_fnc_ownerDispatch;

private _episode = [_medic getVariable ["ACME_DP_ClaimToken", ""], _medic getVariable ["ACME_DP_ClaimEpoch", -1], clientOwner,
    +(_medic getVariable ["ACME_DP_KeyIDs", []]), _medic getVariable ["ACME_DP_Draw3D", -1],
    _medic getVariable ["ACME_providerLocalityEpoch", 0]];
private _pfh = [ACME_fnc_directPressureTick, 0, [_medic, _patient, _bodyPart, "limb", _episode]] call CBA_fnc_addPerFrameHandler;
_medic setVariable ["ACME_DP_PFH", _pfh];
