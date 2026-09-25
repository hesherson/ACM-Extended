// Immediately cancel the provider side of a front/back roll and return control to the player.
// This is intentionally a hard cancellation path for closing a minigame mid-flip; normal completed rolls still
// leave through treatmentPoseStop's authored move graph.
params [
    ["_medic", objNull, [objNull]],
    ["_expectedSource", "", [""]]
];
if (isNull _medic || {!local _medic}) exitWith {false};

private _source = _medic getVariable ["ACME_rollProviderSource", ""];
if (_expectedSource != "" && {_source != _expectedSource}) exitWith {false};

private _token = _medic getVariable ["ACME_rollProviderToken", ""];
private _pose = _medic getVariable ["ACME_treatmentPoseState", []];
private _isRollPose = (_pose param [1, ""]) == "roll";
if (_token == "" && {!_isRollPose}) exitWith {false};

private _pfh = _medic getVariable ["ACME_rollProviderPFH", -1];
if (_pfh isEqualType 0 && {_pfh >= 0}) then {[_pfh] call CBA_fnc_removePerFrameHandler;};

private _epoch = _pose param [0, -1];
_medic setVariable ["ACME_rollProviderPFH", -1];
_medic setVariable ["ACME_rollProviderToken", ""];
_medic setVariable ["ACME_rollProviderActive", false];
_medic setVariable ["ACME_rollProviderSource", ""];
_medic setVariable ["ACME_rollProviderStarted", -1];

if (_isRollPose && {_epoch >= 0}) then {
    [_medic, "roll", _epoch, true] call ACME_fnc_treatmentPoseStop;
};

// The regular pose stop blends out through the authored graph. A user-requested cancel is different: cancel it
// NOW and let Arma select a neutral base state consistent with whatever weapon/stance is currently authoritative.
if (alive _medic && {!(_medic getVariable ["ACE_isUnconscious", false])} && {isNull objectParent _medic}) then {
    _medic setAnimSpeedCoef 1;
    _medic setUnitPos "AUTO";
    _medic switchMove "";
    ["ace_common_switchMove", [_medic, ""]] call CBA_fnc_globalEvent;
};
true
