/* Called AFTER native success/failure cleanup. A stale timer cannot stop or finish a newer dressing.
 * Success alone blends work -> one chest-seal placement -> clean empty-hands exit. */
params ["_args", ["_success", false, [false]]];
_args params ["_medic", "_patient", "_part", "_class"];
if (isNull _medic || {!local _medic}) exitWith {false};
private _token = _args param [7, -1];
private _record = _medic getVariable ["ACME_torsoBandage", []];
if (_token < 0 || {(_record param [0, -2]) != _token}
    || {(_record param [1, objNull]) isNotEqualTo _patient}
    || {(_record param [2, ""]) != _part} || {(_record param [3, ""]) != _class}) exitWith {false};
_medic setVariable ["ACME_torsoBandage", [], false];
private _epoch = _record param [4, -1];
private _pose = _medic getVariable ["ACME_treatmentPoseState", []];
if (_epoch < 0 || {(_pose param [0, -2]) != _epoch} || {(_pose param [1, ""]) != "torsoBandage"}) exitWith {false};
private _canFinish = _success && {alive _medic} && {!(_medic getVariable ["ACE_isUnconscious", false])}
    && {!([_medic] call ACME_fnc_animBlocked)} && {!isNull _patient}
    && {(_medic distance _patient) <= ace_medical_gui_maxDistance};
[_medic, "torsoBandage", _epoch, _canFinish] call ACME_fnc_treatmentPoseStop;
if (!_canFinish) exitWith {true};
// No neutral/armed pose between work and placement. No repeat-loop for this finishing motion.
if (currentWeapon _medic != "") then {_medic selectWeapon "";};
private _window = missionNamespace getVariable ["ACME_CS_applyAnimSeconds", 2.65];
if !(_window isEqualType 0 && {finite _window} && {_window > 0.1} && {_window < 10}) then {_window = 2.65;};
private _finishEpoch = [_medic, "chestSeal", _window, _patient, true] call ACME_fnc_treatmentPoseStart;
if (_finishEpoch >= 0) then {
    [{
        params ["_medic", "_epoch"];
        if (isNull _medic || {!local _medic}) exitWith {};
        [_medic, "chestSeal", _epoch] call ACME_fnc_treatmentPoseStop;
    }, [_medic, _finishEpoch], _window] call CBA_fnc_waitAndExecute;
};
true
