/* B121: put a rejected incremental dose back into the exact stable syringe row. The active syringe has no
   physical magazine while flow is running, so this is a store-only correction until final settlement. */
params ["_medic","_stableId",["_delta",[],[[]]]];
if (isNull _medic || {!local _medic} || {_stableId == ""} || {count _delta < 3}) exitWith {false};
_delta params [["_drug",0,[0]],["_ns",0,[0]],["_comp",[],[[]]]];
private _store = +(_medic getVariable ["ACME_narcStore",[]]);
private _idx = _store findIf {(_x param [11,"",[""]]) == _stableId};
if (_idx < 0) exitWith {false};
private _row = +(_store select _idx);
_row set [2,((_row param [2,0,[0]]) + _drug) max 0];
_row set [4,((_row param [4,0,[0]]) + _ns) max 0];
private _parts = +(_row param [5,[],[[]]]);
{
    _x params [["_ci",-1,[0]],["_source","",[""]],["_ml",0,[0]]];
    if (_ci >= 0 && {_ci < count _parts}) then {
        private _p = +(_parts select _ci);
        if ((_p param [0,"",[""]]) == _source) then {_p set [1,(_p param [1,0,[0]]) + _ml]; _parts set [_ci,_p];};
    };
} forEach _comp;
_row set [5,_parts];
_store set [_idx,_row];
[_medic,_store,false] call ACME_fnc_narcStoreCommit;
true
