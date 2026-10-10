/* Start the slower casualty blend during the last 3.5 seconds of the action, never before visible Flip work. */
params ["_args", ["_elapsed", 0], ["_total", 5]];
_args params ["_medic", "_patient", "_part", "_classname"];
if ((toLowerANSI _classname) != "recoveryposition") exitWith {true};
private _record = _medic getVariable ["ACME_recoveryAction", []];
private _token = _args param [7, ""];
if (_token == "" || {(_record param [0, ""]) != _token}) exitWith {false};
_record params ["", "", "_epoch", "_rollToken", "_dispatched"];
if (isNull _medic || {isNull _patient} || {!local _medic} || {!alive _medic} || {!alive _patient}
    || {!([_medic] call ace_common_fnc_isAwake)} || {[_patient] call ace_common_fnc_isAwake}
    || {!isNull objectParent _medic} || {!isNull objectParent _patient}
    || {_patient getVariable ["ACME_vent_driving", false]}
    || {[_patient] call ACM_core_fnc_cprActive}
    || {alive (_patient getVariable ["ACM_breathing_BVM_Medic", objNull])}
    || {([_medic, _patient] call ACME_fnc_patientInteractionDistance) > ace_medical_gui_maxDistance}
    || {(_record param [6, -1]) != (_medic getVariable ["ACME_providerLocalityEpoch", 0])}
) exitWith {false};
if (_epoch < 0 || {(_medic getVariable ["ACME_treatmentPoseEpoch", -1]) != _epoch}) exitWith {false};
private _pose = _medic getVariable ["ACME_treatmentPoseState", []];
private _completed = (_medic getVariable ["ACME_rollProviderCompletedEpoch", -1]) == _epoch;
if (!_completed && {(_medic getVariable ["ACME_rollProviderToken", ""]) != _rollToken}) exitWith {false};
private _work = toLowerANSI (_pose param [2, ""]);
private _atWork = (_pose param [0, -1]) == _epoch && {(_pose param [1, ""]) == "roll"}
    && {(_pose param [3, -1]) >= 1} && {(toLowerANSI animationState _medic) == _work}
    && {_work == "ainvpknlmstpsnonwnondnon_medic4" || {(_pose param [20, false]) && {_work == "acm_pronecontinuous"}}};
if (!_dispatched && {_elapsed >= ((_total - 3.5) max 0)} && {_atWork || {_completed}}) then {
    _record set [4, true];
    [_medic, _patient, true, false, "begin", _token, _epoch, _record param [5, -1]] call ACM_airway_fnc_setRecoveryPosition;
};
true
