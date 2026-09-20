// Idempotent Direct Pressure teardown for an explicit medic. Safe after distance break, death, menu stop, respawn,
// a stale PFH, movement, or a partially-started hold. The function intentionally clears only state owned by this
// Direct Pressure instance. It never owns another maneuver's controller or interface.
params [["_silent", false, [false]], ["_medic", ACE_player, [objNull]]];
if (isNull _medic) exitWith {};

private _wasActive = _medic getVariable ["ACME_DP_Active", false];
private _patient = _medic getVariable ["ACME_DP_Patient", objNull];
private _part = _medic getVariable ["ACME_DP_Part", ""];
private _wasInPose = _medic getVariable ["ACME_DP_InPose", false];
private _stateBefore = toLower animationState _medic;
private _otherManeuver = missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false];
// An already dispatched DP cancel can arrive after BVM has taken over.
if (!_wasActive && {_otherManeuver}) exitWith {};

// Retire every delayed Direct Pressure pose request first. ACME_DP_PoseToken belongs to the DP layer itself;
// ACME_dah_gen owns ACME_fnc_doAnimHeld's short reassert worker.
_medic setVariable ["ACME_DP_PoseToken", (_medic getVariable ["ACME_DP_PoseToken", 0]) + 1];
_medic setVariable ["ACME_dah_gen", (_medic getVariable ["ACME_dah_gen", 0]) + 1, false];

private _pfh = _medic getVariable ["ACME_DP_PFH", -1];
if (_pfh >= 0) then {[_pfh] call CBA_fnc_removePerFrameHandler;};
{[_x, "keydown"] call CBA_fnc_removeKeyHandler;} forEach (_medic getVariable ["ACME_DP_KeyIDs", []]);
private _d3 = _medic getVariable ["ACME_DP_Draw3D", -1];
if (_d3 >= 0) then {removeMissionEventHandler ["Draw3D", _d3];};
if (!_otherManeuver) then {[] call ace_interaction_fnc_hideMouseHint;};

if (!isNull _patient) then {
    if ((_patient getVariable ["ACME_DP_TorsoMedic", objNull]) isEqualTo _medic) then {
        _patient setVariable ["ACME_DP_TorsoMedic", objNull, true];
    };
    if ((_patient getVariable ["ACME_DP_LimbMedic", objNull]) isEqualTo _medic) then {
        _patient setVariable ["ACME_DP_LimbMedic", objNull, true];
    };
    if (_part != "" && {(_patient getVariable [format ["ACME_DP_press_%1", _part], objNull]) isEqualTo _medic}) then {
        _patient setVariable [format ["ACME_DP_press_%1", _part], objNull, true];
        if (_part in ["leftarm", "rightarm", "leftleg", "rightleg"]) then {
            ["ACME_DP_recalcBleed", [_patient], _patient] call CBA_fnc_targetEvent;
        };
    };
};

// Break only our decorative hold. Priority 2 remains a narrow safety fallback when the engine is physically still
// inside ACME_DirectPressureHold, preventing the provider from being stranded in the looping state.
private _ownsHold = _wasInPose || {_stateBefore == "acme_directpressurehold"};
if (!_otherManeuver && {local _medic} && {alive _medic} && {isNull objectParent _medic} && {_ownsHold}) then {
    _medic setUnitPos "AUTO";
    private _exitPriority = [1, 2] select (_stateBefore == "acme_directpressurehold");
    [_medic, "AmovPknlMstpSnonWnonDnon", _exitPriority] call ACME_fnc_doAnim;
};

{
    _x params ["_name", "_value", ["_public", false]];
    _medic setVariable [_name, _value, _public];
} forEach [
    ["ACME_DP_Active", false, true],
    ["ACME_DP_Patient", objNull, true],
    ["ACME_DP_Part", ""],
    ["ACME_DP_Mode", ""],
    ["ACME_DP_Start", 0],
    ["ACME_DP_NextClot", 0],
    ["ACME_DP_Paused", false],
    ["ACME_DP_InPose", false],
    ["ACME_DP_IdleStart", 0],
    ["ACME_DP_LastPos", []],
    ["ACME_DP_PFH", -1],
    ["ACME_DP_KeyIDs", []],
    ["ACME_DP_Draw3D", -1],
    ["ACME_DP_PoseGraceUntil", 0],
    ["ACME_DP_LastPoseAssert", 0],
    ["ACME_DP_ClinicalYield", false],
    ["ACME_DP_ClinicalYieldStart", 0],
    ["ACME_DP_PauseTreatmentClass", ""],
    ["ACME_DP_TreatmentBusy", false],
    ["ACME_DP_OwnsContinuous", false]
];

if (_wasActive) then {
    if (!_silent) then {["Released direct pressure.", 1.5, _medic] call ace_common_fnc_displayTextStructured;};
    if (!isNull _patient) then {
        [_patient, "activity", "%1 stopped Direct pressure on %2", "%1 stopped Direct pressure on %2",
            [[_medic, false, true] call ace_common_fnc_getName, ([_part, "abbr"] call ACME_fnc_bodyPartName)]] call ACME_fnc_medLog;
    };
};
