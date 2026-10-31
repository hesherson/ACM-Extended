/* Abandoned move intent does not own a disconnected bag. Clear intent without touching volume or dose. */
params ["_patient"];
if (isNull _patient || {!local _patient}) exitWith {};
private _moves = _patient getVariable ["ACME_bagMoves",createHashMap];
private _updated = false;
{
    private _move = _moves get _x;
    _move params ["_origin","_bag","_medic","_at","_epoch"];
    if (isNull _medic || {!alive _medic} || {CBA_missionTime - _at > 120} || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}) then {
        _moves deleteAt _x; _updated = true;
    };
} forEach keys _moves;
if (_updated) then {[_patient,"ACME_bagMoves",_moves] call ACME_fnc_setVarNet;};
