/* Put a rejected/unsent dose back into its exact syringe. Validate the whole
 * mixture before writing: a changed component is unresolved custody, not a
 * successful partial refund. The carrier stays reserved until settlement.
 */
params ["_medic","_stableId",["_delta",[],[[]]]];
if (isNull _medic || {!local _medic} || {_stableId == ""} || {count _delta != 3}) exitWith {false};
_delta params ["_drug","_ns","_comp"];
if !(_drug isEqualType 0 && {finite _drug} && {_drug >= 0}
    && {_ns isEqualType 0} && {finite _ns} && {_ns >= 0}
    && {_comp isEqualType []}) exitWith {false};
private _store = +(_medic getVariable ["ACME_narcStore",[]]);
private _idx = _store findIf {(_x param [11,"",[""]]) == _stableId};
if (_idx < 0) exitWith {false};
private _row = +(_store select _idx);
private _size = _row param [1,0];
private _remainingDrug = _row param [2,-1];
private _remainingNs = _row param [4,-1];
if !(_size isEqualType 0 && {finite _size} && {_size in [1,3,5,10]}
    && {_remainingDrug isEqualType 0} && {finite _remainingDrug} && {_remainingDrug >= 0}
    && {_remainingNs isEqualType 0} && {finite _remainingNs} && {_remainingNs >= 0}
    && {_remainingDrug + _remainingNs + _drug + _ns <= _size + 0.001}) exitWith {false};
private _parts = _row param [5,[]];
if !(_parts isEqualType []) exitWith {false};
_parts = +_parts;
private _valid = true;
private _remainingComponentMl = 0;
{
    if !(_x isEqualType [] && {count _x == 2}
        && {(_x select 0) isEqualType ""} && {(_x select 0) != ""}
        && {(_x select 1) isEqualType 0} && {finite (_x select 1)} && {(_x select 1) >= 0}) then {
        _valid = false;
    } else {_remainingComponentMl = _remainingComponentMl + (_x select 1);};
} forEach _parts;
if (!_valid) exitWith {false};
private _seen = [];
private _componentMl = 0;
{
    if !(_x isEqualType [] && {count _x == 3}) then {_valid = false; continue;};
    _x params ["_ci","_source","_ml"];
    if !(_ci isEqualType 0 && {finite _ci} && {_ci == floor _ci}
        && {_ci >= 0} && {_ci < count _parts} && {!(_ci in _seen)}
        && {_source isEqualType ""} && {_source != ""}
        && {_ml isEqualType 0} && {finite _ml} && {_ml >= 0}) then {
        _valid = false;
    } else {
        private _p = +(_parts select _ci);
        if ((_p param [0,""]) != _source) then {_valid = false;} else {
            _seen pushBack _ci;
            _componentMl = _componentMl + _ml;
            _p set [1,(_p select 1) + _ml];
            _parts set [_ci,_p];
        };
    };
} forEach _comp;
if (!_valid || {!(_parts isEqualTo []) && {
    abs (_remainingComponentMl - _remainingDrug) > 0.001 || {abs (_componentMl - _drug) > 0.001}
}}) exitWith {false};
_row set [2,_remainingDrug + _drug];
_row set [4,_remainingNs + _ns];
_row set [5,_parts];
_store set [_idx,_row];
[_medic,_store,false] call ACME_fnc_narcStoreCommit
