// Self direct pressure stays non-exclusive and never takes ownership of ACM's continuous-action gate. It does not
// issue weapon-selection commands, so the player's selected weapon state is left alone. RMB releases the hold;
// MMB remains accepted for existing users. Movement and keyboard inputs do not cancel pressure.
params ["_medic", "_patient", "_bodyPart"];
if (isNull _medic || {!local _medic}) exitWith {};

_medic setVariable ["ACME_DP_Active", true, true];
_medic setVariable ["ACME_DP_Patient", _medic, true];
_medic setVariable ["ACME_DP_Part", _bodyPart, true];
_medic setVariable ["ACME_DP_Mode", "self"];
_medic setVariable ["ACME_DP_Start", CBA_missionTime];
_medic setVariable ["ACME_DP_NextClot", CBA_missionTime + 15];
_medic setVariable ["ACME_DP_Paused", false];
_medic setVariable ["ACME_DP_LastPos", getPosASL _medic];
_medic setVariable ["ACME_DP_ClinicalYield", false];
_medic setVariable ["ACME_DP_ClinicalYieldStart", 0];
_medic setVariable ["ACME_DP_OwnsContinuous", false];

// Direct Pressure has no keyboard cancellation binding. RMB/MMB use the display guard; the explicit
// Stop Direct Pressure menu action is the deliberate UI fallback. Escape/H remain available to the player.
_medic setVariable ["ACME_DP_KeyIDs", []];
["", "Stop Direct Pressure", ""] call ace_interaction_fnc_showMouseHint;

[_medic, "activity",
 "%1 applied direct pressure to %2",
 "%1 applied direct pressure to %2",
 [[_medic, false, true] call ace_common_fnc_getName, ([_bodyPart, "abbr"] call ACME_fnc_bodyPartName)]] call ACME_fnc_medLog;

// Publish the clinical pressure marker only after provider-local episode state is fully initialized.
[_medic, "directPressureMarker", [_medic, _bodyPart, true, _medic getVariable ["ACME_DP_ClaimToken", ""], _medic getVariable ["ACME_DP_ClaimEpoch", -1]]] call ACME_fnc_ownerDispatch;

private _episode = [_medic getVariable ["ACME_DP_ClaimToken", ""], _medic getVariable ["ACME_DP_ClaimEpoch", -1], clientOwner,
    +(_medic getVariable ["ACME_DP_KeyIDs", []]), _medic getVariable ["ACME_DP_Draw3D", -1],
    _medic getVariable ["ACME_providerLocalityEpoch", 0]];
private _pfh = [ACME_fnc_directPressureTick, 0, [_medic, _medic, _bodyPart, "self", _episode]] call CBA_fnc_addPerFrameHandler;
_medic setVariable ["ACME_DP_PFH", _pfh];
