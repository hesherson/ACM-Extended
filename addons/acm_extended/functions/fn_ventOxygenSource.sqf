/* Native provider/patient treatment supply order, including supported packed kits. */
params ["_medic","_patient"];
private _source=objNull;
{
    if (([_x] call ACME_fnc_ventOxygenReserve) select 0) exitWith {_source=_x;};
} forEach ([_medic,_patient] call ACME_fnc_treatmentSupplyOrder);
_source
