/* Retire only this assessment episode. Completion/failure/preflight abort share this cleanup. */
params [["_medic", objNull, [objNull]], ["_epoch", -1, [0]], ["_reopen", false, [false]]];
if (isNull _medic) exitWith {};
private _record = _medic getVariable ["ACME_assessment", []];
if (_record isEqualTo [] || {_epoch >= 0 && {(_record select 0) != _epoch}}) exitWith {};
_record params ["_ownedEpoch", "_args", "_phase", "_pfh", "_started", "_token", "_keys"];
_args params ["_m", "_patient", "_bodyPart", "_classname"];
_medic setVariable ["ACME_assessment", [], false];
if ((missionNamespace getVariable ["ACME_assessmentInputProvider", objNull]) isEqualTo _medic) then {
    missionNamespace setVariable ["ACME_assessmentInputProvider", objNull];
};
if (_pfh >= 0) then {[_pfh] call CBA_fnc_removePerFrameHandler;};
{[_x, "keydown"] call CBA_fnc_removeKeyHandler;} forEach _keys;
[false, _medic, _patient, _token] call ACME_fnc_chestAccessPreparing;
[_medic, "", _ownedEpoch, _reopen] call ACME_fnc_treatmentPoseStop;
if (_reopen && {local _medic} && {alive _medic} && {!(_medic getVariable ["ACE_isUnconscious", false])}
    && {isNull objectParent _medic} && {stance _medic != "PRONE"}
    && {(_medic getVariable ["ACME_treatmentPoseEpoch", -1]) == _ownedEpoch}
    && {!([_medic] call ACME_fnc_providerStanceOwned)}) then {
    // No native end-move may restore the weapon or stand between the assessment and menu.
    [_medic, [["treatmentEndInAnim"]]] call ACM_core_fnc_setAceMedicalState;
    _medic setUnitPos "MIDDLE";
    [_medic, "ACM_GenericContinuous", 1] call ACME_fnc_doAnim;
};
// An aborted assessment preflight has not emitted ace_treatmentFailed. Release its exact carrier lease here.
if (_phase == 0 && {!(_record param [10, false])} && {local _medic}) then {
    if ((_medic getVariable ["ACME_DP_PauseTreatmentClass", ""]) == toLowerANSI _classname) then {
        _medic setVariable ["ACME_DP_Paused", false, false];
        _medic setVariable ["ACME_DP_PauseTreatmentClass", "", false];
        _medic setVariable ["ACME_DP_IdleStart", CBA_missionTime, false];
    };
    private _lease = _medic getVariable ["ACME_chestAccess_treatment", []];
    if ((_lease param [0, objNull]) isEqualTo _patient
        && {(_lease param [1, ""]) == toLowerANSI _classname}) then {
        _medic setVariable ["ACME_chestAccess_treatment", [], false];
        [_patient, _medic, _lease param [2, ""], false, toLowerANSI _classname] call ACME_fnc_chestAccessVestEvent;
    };
};
if (_reopen) then {[_medic, _patient, _ownedEpoch] call ACME_fnc_assessmentReopen;};
