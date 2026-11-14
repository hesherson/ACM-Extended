/* Fridge stock is issued in lots. An explicit restock replaces the lot and resets its age. */
params ["_fridge",["_now",([] call ACME_fnc_clinicalClock)]];
if (!isServer || {_fridge getVariable ["ACME_persistenceFrozen",false]} || {!(["real"] call ACME_fnc_bloodTiming)} || {!(["spoil"] call ACME_fnc_bloodTiming)}) exitWith {};
private _stock = _fridge getVariable ["ACME_bf_stock",[]];
if (_stock isEqualTo []) exitWith {};
private _age = (_now - (_fridge getVariable ["ACME_bf_lotStart",_now])) max 0;
private _expiry = ["fridge"] call ACME_fnc_bloodTiming;
if (_age >= _expiry) exitWith {_fridge setVariable ["ACME_bf_stock",[],true];};
private _kept = _stock select {
    private _class = _x select 0;
    (_class find "ACM_FreshBloodBag_") != 0
        || {_age < (["fresh"] call ACME_fnc_bloodTiming) && {([_class] call ACME_fnc_bloodWarmLimit) > 0}}
};
if (_kept isNotEqualTo _stock) then {_fridge setVariable ["ACME_bf_stock",_kept,true];};
