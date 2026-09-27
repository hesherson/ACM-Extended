params [["_unit", ACE_player], ["_patient", objNull]];

private _result = -1;

{
    private _class = format ["ACM_Syringe_%1", _x];
    if (([_unit,_patient,_class] call ACME_fnc_treatmentSupplyCount) > 0) exitWith {_result = _x};
} forEach [10, 5, 3, 1];

_result;
