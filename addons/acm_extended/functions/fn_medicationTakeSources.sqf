/* B13: validate the complete draw before taking anything; conserve open vial mL.
   Components are source mL, not mg. No clinical mixing compatibility is implied. */
params ["_medic", "_components", ["_container", ""], ["_consumeContainer", false]];
if (isNull _medic || {!local _medic} || {!alive _medic} || {!(_components isEqualType [])} || {_components isEqualTo []}) exitWith {false};
// Prevent a scheduled caller yielding between complete validation and debit.
private _result = false;
isNil {
private _need = createHashMap;
private _valid = true;
private _taken = [];
{
    if (!(_x isEqualType []) || {count _x != 2}) then {_valid = false;} else {
        _x params ["_source", "_ml"];
        if (!(_source isEqualType "") || {!(_ml isEqualType 0)} || {!finite _ml} || {_ml <= 0}) then {_valid = false;} else {
            private _cfg = configFile >> "ACM_Medication" >> "Concentration" >> _source;
            if (getNumber (_cfg >> "concentration") <= 0 || {getNumber (_cfg >> "volume") <= 0}) then {_valid = false;} else {
                _need set [_source, (_need getOrDefault [_source, 0]) + _ml];
            };
        };
    };
} forEach _components;
if (!_valid || {_container != "" && {([_medic, _container] call ACME_fnc_itemCount) < 1}}) exitWith {false};
{if (([_medic, _x] call ACME_fnc_infusionVialVolume) + 0.000001 < (_need get _x)) then {_valid = false;};} forEach (keys _need);
if (!_valid) exitWith {false};
{
    if !([_medic, _x, _need get _x, _medic] call ACME_fnc_vialTake) exitWith {_valid = false;};
    _taken pushBack [_x, _need get _x];
} forEach (keys _need);
if (!_valid) exitWith {
    // Unexpected late debit failure restores exact solution, including repeated draws.
    {[_medic, _x select 0, _x select 1, _medic] call ACME_fnc_vialRefund;} forEach _taken;
    false
};
if (_consumeContainer && {_container != ""}) then {[_medic, _container] call ACME_fnc_itemTake;};
_result = true;
};
_result
