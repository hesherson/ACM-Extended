/* Release only this display's continuous crouch. Silent calls hand ownership to another procedure. */
params [["_medic", objNull, [objNull]], ["_silent", false, [false]], ["_epoch", -1, [0]]];
if (isNull _medic) exitWith {};
private _state = _medic getVariable ["ACME_menuPose", []];
// A silent handoff can be rejected after removing the state. Its original display
// still owns the right to release that orphan, but never a later menu generation.
private _currentEpoch = _state param [0, _medic getVariable ["ACME_menuPoseEpoch", -1]];
if (_state isEqualTo [] && {_epoch < 0}) exitWith {};
if ((_medic getVariable ["ACME_menuPoseReleasedEpoch", -2]) == _currentEpoch) exitWith {};
if (_epoch >= 0 && {_currentEpoch != _epoch}) exitWith {};
_medic setVariable ["ACME_menuPose", []];
if (_silent) exitWith {};
if (!local _medic) exitWith {_medic setVariable ["ACME_menuPoseReleasedEpoch", _currentEpoch];};
if ([_medic, true] call ACME_fnc_providerStanceOwned) exitWith {};
_medic setVariable ["ACME_menuPoseReleasedEpoch", _currentEpoch];
_medic setVariable ["ACME_menuPoseAfterTreatment", objNull];
_medic setUnitPos "AUTO";
if (!alive _medic || {_medic getVariable ["ACE_isUnconscious", false]} || {[_medic] call ACME_fnc_animBlocked}) exitWith {
    _medic setAnimSpeedCoef 1;
    ["ace_common_setAnimSpeedCoef", [_medic, 1]] call CBA_fnc_globalEvent;
};
// First-contact menus never acquired empty hands or an animation-speed override.
// Releasing that menu must leave its current weapon stance alone.
if ((_medic getVariable ["ACME_menuPoseGenericEpoch", -1]) != _currentEpoch) exitWith {};
private _rate = [] call ACME_fnc_choreographyRate;
_medic setAnimSpeedCoef _rate;
["ace_common_setAnimSpeedCoef", [_medic, _rate]] call CBA_fnc_globalEvent;
[_medic, "AmovPknlMstpSnonWnonDnon", 1] call ACME_fnc_doAnim;
[{
    params ["_medic", "_epoch", "_poseEpoch", "_continuousEpoch"];
    if (!isNull _medic && {local _medic} && {(_medic getVariable ["ACME_menuPoseEpoch", -1]) == _epoch}
        && {(_medic getVariable ["ACME_treatmentPoseEpoch", 0]) == _poseEpoch}
        && {(missionNamespace getVariable ["ACM_core_ContinuousAction_Epoch", 0]) == _continuousEpoch}
        && {!([_medic, true] call ACME_fnc_providerStanceOwned)}) then {
        _medic setAnimSpeedCoef 1;
        ["ace_common_setAnimSpeedCoef", [_medic, 1]] call CBA_fnc_globalEvent;
    };
}, [_medic, _currentEpoch, _medic getVariable ["ACME_treatmentPoseEpoch", 0], missionNamespace getVariable ["ACM_core_ContinuousAction_Epoch", 0]], 0.85 / _rate] call CBA_fnc_waitAndExecute;
