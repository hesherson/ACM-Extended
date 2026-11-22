/* B20: non-mutating preview of the background vial ledger after reserving solution in the open syringe.
   Returns [vialsRemaining,currentVialMl,vialCapacityMl,totalMlRemaining,sealedPhysical,openLedgerMl].
   An opened partial vial counts as one vial. _reservedMl can span vial boundaries, so the UI automatically
   rolls to the next vial without consuming inventory until the draw/compound is actually committed. */
params [
    ["_holder", objNull, [objNull]],
    ["_med", "", [""]],
    ["_reservedMl", 0, [0]],
    ["_physicalClass", "", [""]]
];
if (isNull _holder || {_med == ""}) exitWith {[0,0,0,0,0,0]};
private _cap = [_med] call ACME_fnc_vialCapacity;
if (_cap <= 0) exitWith {[0,0,0,0,0,0]};
private _map = _holder getVariable ["ACME_infusion_openVials", createHashMap];
private _open = (_map getOrDefault [_med, 0]) max 0;
if (_open > 0 && {_open <= (missionNamespace getVariable ["ACME_vialDiscardResidualMl",0.0105])}) then {_open = 0;};
private _primary = if (_physicalClass != "") then {_physicalClass} else {[_med] call ACME_fnc_vialClass};
private _sealed = [_holder, _primary] call ACME_fnc_vialItemCount;
private _total = _open + ((_sealed max 0) * _cap);
private _left = (_total - (_reservedMl max 0)) max 0;
if (_left <= 0.000001) exitWith {[0,0,_cap,0,_sealed,_open]};
// Work out the currently active vial after the staged draw. The open remainder is always consumed first.
private _r = (_reservedMl max 0) min _total;
private _cur = _open;
private _sealedLeft = _sealed;
if (_cur > 0.000001) then {
    if (_r < _cur) then {
        _cur = _cur - _r;
        _r = 0;
    } else {
        _r = _r - _cur;
        _cur = 0;
    };
};
while {_r > 0.000001 && {_sealedLeft > 0}} do {
    _sealedLeft = _sealedLeft - 1;
    if (_r < _cap) then {
        _cur = _cap - _r;
        _r = 0;
    } else {
        _r = _r - _cap;
        _cur = 0;
    };
};
// If no partially consumed vial is active but unopened stock remains, that next vial is the current vial.
if (_cur <= 0.000001 && {_sealedLeft > 0}) then {
    _sealedLeft = _sealedLeft - 1;
    _cur = _cap;
};
private _vials = _sealedLeft + (if (_cur > 0.000001) then {1} else {0});
[_vials max 0, _cur max 0 min _cap, _cap, _left, _sealed, _open]
