/* Total usable source solution: invisible partial-vial remainder plus unopened physical vials. */
params [["_holder", objNull, [objNull]], ["_med", "", [""]]];
if (isNull _holder || {_med == ""}) exitWith {0};
private _cap = [_med] call ACME_fnc_vialCapacity;
if (_cap <= 0) exitWith {0};
private _open = (_holder getVariable ["ACME_infusion_openVials", createHashMap]) getOrDefault [_med, 0];
if (_open > 0 && {_open <= (missionNamespace getVariable ["ACME_vialDiscardResidualMl",0.0105])}) then {_open = 0;};
private _vial = [_med] call ACME_fnc_vialClass;
private _sealed = [_holder, _vial] call ACME_fnc_vialItemCount;
(_open max 0) + _cap * _sealed
