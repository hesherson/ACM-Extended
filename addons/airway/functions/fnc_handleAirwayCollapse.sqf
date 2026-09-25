#include "..\script_component.hpp"
/*
 * Author: Blue / ACM Extended B125
 * Handle airway collapse due to loss of reflexes.
 *
 * B125:airwayCollapseWakeClear
 * A conscious patient cannot retain the unconscious soft-tissue-collapse ladder. Stock ACM stopped the PFH by
 * writing collapse state 3 when the casualty woke, which left a stale severe/mild obstruction flag behind even
 * though getAirwayState correctly returned a patent airway while awake. Wake now retires the worker and clears
 * collapse to zero. True severe collapse still stops the worker at state 3 while the patient remains unconscious.
 */

params ["_patient", ["_epoch", -1]];
if (isNull _patient) exitWith {};
if (_epoch < 0) then {_epoch = [_patient] call ACME_fnc_clinicalEpoch;};
if (!local _patient) exitWith {
    [QGVAR(handleAirwayCollapse), [_patient, _epoch], _patient] call CBA_fnc_targetEvent;
};
if (_epoch != ([_patient] call ACME_fnc_clinicalEpoch)
    || {!alive _patient} || {_patient getVariable ["ACME_clinicalRestoring", false]}) exitWith {};

private _acmeReconcile = "B125:airwayCollapseWakeClear";

if (_patient getVariable [QGVAR(AirwayCollapse_PFH), -1] != -1) exitWith {};

if (!(IS_UNCONSCIOUS(_patient))) exitWith {
    if ((_patient getVariable [QGVAR(AirwayCollapse_State), 0]) != 0) then {
        _patient setVariable [QGVAR(AirwayCollapse_State), 0, true];
    };
    _patient setVariable ["ACME_nativeCollapseActive", false, true];
};
_patient setVariable ["ACME_nativeCollapseActive", true, true];
private _PFH = [{
    params ["_args", "_idPFH"];
    _args params ["_patient", "_epoch"];
    // A departed/reset worker may remove itself, never the new owner's or new episode's handle/evidence.
    if (isNull _patient || {!local _patient}
        || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}
        || {_patient getVariable ["ACME_clinicalRestoring", false]}
        || {(_patient getVariable [QGVAR(AirwayCollapse_PFH), -1]) != _idPFH}) exitWith {
        [_idPFH] call CBA_fnc_removePerFrameHandler;
        if (!isNull _patient && {(_patient getVariable [QGVAR(AirwayCollapse_PFH), -1]) == _idPFH}) then {
            _patient setVariable [QGVAR(AirwayCollapse_PFH), -1];
        };
    };
    if (!alive _patient) exitWith {
        [_idPFH] call CBA_fnc_removePerFrameHandler;
        _patient setVariable [QGVAR(AirwayCollapse_PFH), -1];
        _patient setVariable ["ACME_nativeCollapseActive", false, true];
    };

    private _collapseState = _patient getVariable [QGVAR(AirwayCollapse_State), 0];

    // B125: waking clears the unconscious collapse state instead of promoting it to severe obstruction.
    if (!(IS_UNCONSCIOUS(_patient))) exitWith {
        if (_collapseState != 0) then {
            _patient setVariable [QGVAR(AirwayCollapse_State), 0, true];
        };
        _patient setVariable [QGVAR(AirwayCollapse_PFH), -1];
        _patient setVariable ["ACME_nativeCollapseActive", false, true];
        [_idPFH] call CBA_fnc_removePerFrameHandler;
    };

    if (_collapseState > 2) exitWith {
        _patient setVariable [QGVAR(AirwayCollapse_State), 3, true];
        _patient setVariable [QGVAR(AirwayCollapse_PFH), -1];
        _patient setVariable ["ACME_nativeCollapseActive", false, true];
        [_idPFH] call CBA_fnc_removePerFrameHandler;
    };

    if (_patient getVariable [QGVAR(AirwayReflex_State), false]) then {
        _patient setVariable [QGVAR(AirwayReflex_State), false, true];
    };

    private _keepAirwayIntact = (_patient getVariable [QGVAR(RecoveryPosition_State), false])
        || (_patient getVariable [QGVAR(HeadTilt_State), false])
        || ((_patient getVariable [QGVAR(AirwayItem_Oral), ""]) == "SGA")
        || (_patient getVariable [QGVAR(SurgicalAirway_State), false])
        || (_patient getVariable ["ACME_ETT_Inserted", false]);
    if (_keepAirwayIntact) exitWith {};

    if (random 1 < (0.3 * GVAR(airwayCollapseChance))) then {
        _patient setVariable [QGVAR(AirwayCollapse_State), (_collapseState + 1), true];
    };

}, (30 + (random 15)), [_patient, _epoch]] call CBA_fnc_addPerFrameHandler;

_patient setVariable [QGVAR(AirwayCollapse_PFH), _PFH];
