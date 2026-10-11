/* Reconcile pending device custody returns on the patient owner, independently
 * of whether a cuff or bag remains. Shared-clock certificates cannot mint items
 * after their deadline, and public provider receipts stop repeats after locality. */
params ["_patient"];
if (isNull _patient || {!local _patient}) exitWith {};
if (serverTime < (_patient getVariable ["ACME_lineWarmerReturnNext", -1])) exitWith {};
_patient setVariable ["ACME_lineWarmerReturnNext", serverTime + 0.75];
private _returns = _patient getVariable ["ACME_lineWarmerReturns", createHashMap];
if (count _returns > 0) then {
    private _patients = missionNamespace getVariable ["ACME_lineWarmerReturnPatients", []];
    _patients pushBackUnique _patient;
    missionNamespace setVariable ["ACME_lineWarmerReturnPatients", _patients];
};
private _changed = false;
{
    private _record = _returns get _x;
    _record params ["_medic", "_issued"];
    if (!isNull _medic) then {
        if (_x in (_medic getVariable ["ACME_lineWarmerReturned", createHashMap])) then {
            _returns deleteAt _x; _changed = true;
        } else {
            // Keep undelivered custody across disconnect/locality delays. A new
            // short certificate retains the same permanently deduplicated ID.
            if (serverTime - _issued > 25) then {
                _issued = serverTime;
                _returns set [_x, [_medic, _issued]];
                _changed = true;
            };
            ["ACME_lineWarmerReturn", [_patient, _medic, _x, _issued], _medic] call CBA_fnc_targetEvent;
        };
    };
} forEach keys _returns;
if (_changed) then {[_patient, "ACME_lineWarmerReturns", _returns] call ACME_fnc_setVarNet;};
