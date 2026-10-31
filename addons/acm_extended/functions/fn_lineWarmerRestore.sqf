/* Reconcile real warmer custody against a validated medical snapshot before
 * native reset. A retained device stays inline; an omitted device returns once;
 * a previously detached/returned identity can never be recreated by old JSON. */
if (canSuspend) exitWith {
    private _result = [];
    isNil {_result = _this call ACME_fnc_lineWarmerRestore;};
    _result
};
params ["_patient", ["_incoming", createHashMap], ["_incomingCustody", createHashMap], ["_epoch", -1], ["_phase", "prepare"]];
if (isNull _patient || {!local _patient}) exitWith {[]};
if (_phase == "prepare") exitWith {
    private _kept = createHashMap;
    private _custody = createHashMap;
    private _ids = createHashMap;
    private _counts = createHashMap;
    {
        private _record = _incomingCustody get _x;
        if (_incoming getOrDefault [_x, false] && {count _record == 3}) then {
            private _id = _record select 0;
            _counts set [_id, (_counts getOrDefault [_id, 0]) + 1];
        };
    } forEach keys _incomingCustody;
    private _retired = _patient getVariable ["ACME_lineWarmerRetired", createHashMap];
    private _returns = _patient getVariable ["ACME_lineWarmerReturns", createHashMap];
    {
        private _key = _x;
        private _record = _incomingCustody get _key;
        if (_incoming getOrDefault [_key, false] && {count _record == 3}) then {
            _record params ["_id", "_installer"];
            private _returned = !isNull _installer && {_id in (_installer getVariable ["ACME_lineWarmerReturned", createHashMap])};
            if (_id != "" && {(_counts getOrDefault [_id, 0]) == 1} && {!(_id in _retired)} && {!(_id in _returns)} && {!_returned}) then {
                private _restored = +_record;
                _restored set [2, _epoch];
                _kept set [_key, true];
                _custody set [_key, _restored];
                _ids set [_id, true];
            };
        };
    } forEach keys _incomingCustody;
    private _plan = [_kept, _custody];
    _patient setVariable ["ACME_lineWarmerRestorePlan", _plan, false];
    private _liveCustody = _patient getVariable ["ACME_lineWarmerCustody", createHashMap];
    {
        private _key = _x;
        private _record = _liveCustody getOrDefault [_key, []];
        private _id = _record param [0, "", [""]];
        if !(_id in _ids) then {
            private _parts = _key splitString "#";
            if (count _parts == 3) then {[_patient, _parts select 0, (_parts select 1) == "true", parseNumber (_parts select 2)] call ACME_fnc_lineWarmerDetach;};
        };
    } forEach keys (_patient getVariable ["ACME_lineWarmers", createHashMap]);
    _plan
};
private _plan = _patient getVariable ["ACME_lineWarmerRestorePlan", []];
if (count _plan != 2) then {_plan = [_patient, _incoming, _incomingCustody, _epoch, "prepare"] call ACME_fnc_lineWarmerRestore;};
if (count _plan != 2) exitWith {[]};
private _custody = _plan select 1;
{private _record = +(_custody get _x); _record set [2, _epoch]; _custody set [_x, _record];} forEach keys _custody;
[_patient, "ACME_lineWarmerCustody", _custody] call ACME_fnc_setVarNet;
[_patient, "ACME_lineWarmers", _plan select 0] call ACME_fnc_setVarNet;
_patient setVariable ["ACME_lineWarmerRestorePlan", nil, false];
_plan
