/* B121 called once by patient-owner circulation. The total-rate keys preserve the historical API; source-specific
   keys are also published for diagnostics/future tuning. */
params ["_patient","_dt"];
private _rates = createHashMap;
if (isNull _patient || {!local _patient}) exitWith {_rates};
if (!alive _patient) exitWith {
    [_patient] call ACME_fnc_deadPhysiologyFreeze;
    _rates
};
if (_dt <= 0) exitWith {_rates};
private _queue = _patient getVariable ["ACME_medicationDriveQueue",[]];
private _keep = [];
private _bolusCompleted = false;
{
    _x params ["_base","_mass","_remaining",["_source","bolus"]];
    private _step = _dt min (_remaining max 0.000001);
    private _delivered = _mass * (_step / (_remaining max 0.000001));
    private _rate = _delivered*60/_dt;
    _rates set [_base,(_rates getOrDefault [_base,0])+_rate];
    _rates set [format ["%1#%2",_base,_source],(_rates getOrDefault [format ["%1#%2",_base,_source],0])+_rate];
    if (_remaining > _dt+0.000001) then {
        _keep pushBack [_base,(_mass-_delivered) max 0,_remaining-_dt,_source];
    } else {
        if (_source != "infusion") then {_bolusCompleted = true;};
    };
} forEach _queue;

// Exact remaining mass/time is owner-local every circulation tick. Bolus completion is an intervention transition;
// completed infusion samples share the one-second cadence, otherwise a .25-second add/consume pair defeats it.
_patient setVariable ["ACME_medicationDriveQueue", _keep, false];
private _driveNow = diag_tickTime;
private _driveLast = _patient getVariable ["ACME_medicationDriveNetAt", -1];
if (_bolusCompleted || {_driveLast < 0} || {(_driveNow - _driveLast) >= 1}) then {
    _patient setVariable ["ACME_medicationDriveNetAt", _driveNow, false];
    [_patient, "ACME_medicationDriveQueue", _keep] call ACME_fnc_setVarNet;
    _patient setVariable ["ACME_medicationDriveFlushToken", [], false];
} else {
    // A final short sample may retire the circulation worker before its next snapshot. One trailing callback
    // publishes the current queue, never the captured old sample. New publications/locality/reset invalidate it.
    if ((count _keep) != (count _queue) && {(_patient getVariable ["ACME_medicationDriveFlushToken", []]) isEqualTo []}) then {
        private _token = [owner _patient, [_patient] call ACME_fnc_clinicalEpoch, _driveLast];
        _patient setVariable ["ACME_medicationDriveFlushToken", _token, false];
        [{
            params ["_patient", "_token"];
            if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {};
            if !((_patient getVariable ["ACME_medicationDriveFlushToken", []]) isEqualTo _token) exitWith {};
            _patient setVariable ["ACME_medicationDriveFlushToken", [], false];
            if ((_token select 0) != owner _patient || {(_token select 1) != ([_patient] call ACME_fnc_clinicalEpoch)}) exitWith {};
            [_patient, "ACME_medicationDriveQueue", _patient getVariable ["ACME_medicationDriveQueue", []]] call ACME_fnc_setVarNet;
            _patient setVariable ["ACME_medicationDriveNetAt", diag_tickTime, false];
        }, [_patient, _token], (1 - (_driveNow - _driveLast)) max 0] call CBA_fnc_waitAndExecute;
    };
};
[_patient,"ACME_ketRapidLoad",(_patient getVariable ["ACME_ketRapidLoad",0])*(0.5^(_dt/20)),0.005,1] call ACME_fnc_setVarNetApprox;
{
    _x params ["_key","_half"];
    [_patient,_key,(_patient getVariable [_key,0])*(0.5^(_dt/_half)),0.005,1] call ACME_fnc_setVarNetApprox;
} forEach [["ACME_hcMed_rapidPropofol",35],["ACME_hcMed_rapidMidazolam",45],["ACME_hcMed_rapidOpioid",45],["ACME_hcMed_rapidRocuronium",60]];
_rates
