#include "..\script_component.hpp"
/*
 * Author: Blue
 * Handle blood transfusion reaction
 *
 * Arguments:
 * 0: Patient <OBJECT>
 *
 * Return Value:
 * None
 *
 * Example:
 * [cursorTarget] call ACM_circulation_fnc_handleHemolyticReaction;
 *
 * Public: No
 */

params ["_patient", ["_started", false], ["_epoch", -1]];
if (isNull _patient) exitWith {};
if (_epoch < 0) then {_epoch = [_patient] call ACME_fnc_clinicalEpoch;};
if (!local _patient) exitWith {
    [QGVAR(handleHemolyticReaction), [_patient, _started, _epoch], _patient] call CBA_fnc_targetEvent;
};
if (_epoch != ([_patient] call ACME_fnc_clinicalEpoch)
    || {!alive _patient} || {_patient getVariable ["ACME_clinicalRestoring", false]}) exitWith {};

// Keep native onset timing. If ownership moves while waiting, deliver the due onset to the current owner.
if (!_started) exitWith {
    [{
        params ["_patient", "_epoch"];
        [_patient, true, _epoch] call FUNC(handleHemolyticReaction);
    }, [_patient, _epoch], ((random 30) + 30)] call CBA_fnc_waitAndExecute;
};

if (_patient getVariable [QGVAR(HemolyticReaction_PFH), -1] != -1) exitWith {};

if !(_patient getVariable ["ACME_nativeHemolysisActive", false]) then {
    _patient setVariable [QGVAR(HemolyticReaction_Severity), 1, true];
};

_patient setVariable ["ACME_nativeHemolysisActive", true, true];

private _PFH = [{
    params ["_args", "_idPFH"];
    _args params ["_patient", "_epoch"];
    if (isNull _patient || {!local _patient}
        || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}
        || {_patient getVariable ["ACME_clinicalRestoring", false]}
        || {(_patient getVariable [QGVAR(HemolyticReaction_PFH), -1]) != _idPFH}) exitWith {
        [_idPFH] call CBA_fnc_removePerFrameHandler;
        if (!isNull _patient && {(_patient getVariable [QGVAR(HemolyticReaction_PFH), -1]) == _idPFH}) then {
            _patient setVariable [QGVAR(HemolyticReaction_PFH), -1];
        };
    };

    // ace_medical_vitals_fnc_handleUnitVitals
    private _lastTimeValuesSynced = _patient getVariable [QACEGVAR(medical_vitals,lastMomentValuesSynced), 0];
    private _syncValues = (CBA_missionTime - _lastTimeValuesSynced) >= (10 + floor(random 10));

    private _reactionVolume = _patient getVariable [QGVAR(HemolyticReaction_Volume), 0];

    if (!(alive _patient) || ((_reactionVolume <= 0) && {count (_patient getVariable [QGVAR(IV_Bags), createHashMap]) == 0})) exitWith {
        _patient setVariable [QGVAR(HemolyticReaction_PFH), -1];
        _patient setVariable [QGVAR(HemolyticReaction_Severity), 0, true];
        _patient setVariable ["ACME_nativeHemolysisActive", false, true];
        [_idPFH] call CBA_fnc_removePerFrameHandler;
    };

    if (_reactionVolume > 0.1) then {
        private _severity = linearConversion [0.1, 1, _reactionVolume, 1, 10];

        if (GET_PAIN(_patient) < (_severity * 0.07)) then {
            [_patient, ((_severity * 0.07) min 1)] call ACEFUNC(medical,adjustPainLevel);
        };

        _patient setVariable [QGVAR(HemolyticReaction_Severity), _severity, _syncValues];
    } else {
        _patient setVariable [QGVAR(HemolyticReaction_Severity), 0, _syncValues];
    };

}, 1, [_patient, _epoch]] call CBA_fnc_addPerFrameHandler;

_patient setVariable [QGVAR(HemolyticReaction_PFH), _PFH];
