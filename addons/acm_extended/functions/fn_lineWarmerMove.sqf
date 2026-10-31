/* Move one connected assembly atomically at the patient owner. Do not detach or
 * return the warmer while moving either Y/PiB branch to the destination access. */
if (canSuspend) exitWith {
    private _result = false;
    isNil {_result = _this call ACME_fnc_lineWarmerMove;};
    _result
};
params ["_patient", "_fromPart", "_fromIV", "_fromSite", "_toPart", "_toIV", "_toSite"];
if (isNull _patient || {!local _patient}) exitWith {false};
private _from = toLowerANSI format ["%1#%2#%3", _fromPart, _fromIV, _fromSite];
private _to = toLowerANSI format ["%1#%2#%3", _toPart, _toIV, _toSite];
if (_from == _to) exitWith {true};
private _lines = _patient getVariable ["ACME_lineWarmers", createHashMap];
if !(_lines getOrDefault [_from, false]) exitWith {true};
if (_lines getOrDefault [_to, false]) exitWith {false};
private _custody = _patient getVariable ["ACME_lineWarmerCustody", createHashMap];
private _record = _custody getOrDefault [_from, []];
_lines deleteAt _from;
_lines set [_to, true];
_custody deleteAt _from;
if (_record isNotEqualTo []) then {_custody set [_to, _record];};
[_patient, "ACME_lineWarmerCustody", _custody] call ACME_fnc_setVarNet;
[_patient, "ACME_lineWarmers", _lines] call ACME_fnc_setVarNet;
true
