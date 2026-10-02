/* Choose a carried cylinder using ACE's patient/provider order. ACM's reserve API
   operates on worn containers, so capture the actual unit whose bottle it can drain.
   A cylinder packed in an inventory mod's kit counts too (ACME_fnc_itemCount):
   useOxygenTankReserve draws from it through efak_medical_fnc_drawCharge. */
params ["_medic", "_patient"];
private _source = objNull;
{
    private _unit = _x;
    private _available = false;
    {
        if (((magazinesAmmoCargo _x) findIf {(_x select 0) == "ACM_OxygenTank_425" && {(_x select 1) > 0}}) >= 0) exitWith {_available = true;};
    } forEach [uniformContainer _unit, vestContainer _unit, backpackContainer _unit];
    if (!_available && {!isNil "efak_medical_fnc_drawCharge"}) then {
        _available = ([_unit, "ACM_OxygenTank_425"] call ACME_fnc_itemCount) > 0;
    };
    if (_available) exitWith {_source = _unit;};
} forEach ([_medic, _patient] call ACME_fnc_treatmentSupplyOrder);
_source
