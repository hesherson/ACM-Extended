/* Choose an oxygen donor in ACE's provider/patient treatment order. Loose ACM
   cylinders are ammo-bearing magazines in worn containers; EFAK may also hold
   a usable cylinder inside a kit. Retain its real donor for owner-local debit. */
params ["_medic", "_patient"];
private _source = objNull;
{
    private _unit = _x;
    private _available = false;
    {
        if (((magazinesAmmoCargo _x) findIf {(_x select 0) == "ACM_OxygenTank_425" && {(_x select 1) > 0}}) >= 0) exitWith {_available = true;};
    } forEach [uniformContainer _unit, vestContainer _unit, backpackContainer _unit];
    // Match the EFAK fallback of ACM_breathing_fnc_useOxygenTankReserve:
    // the kit is not visible to magazinesAmmoCargo, but its charge is debited
    // through efak_medical_fnc_drawCharge on the selected donor's owner.
    if (!_available && {!isNil "efak_medical_fnc_drawCharge"}) then {
        _available = ([_unit, "ACM_OxygenTank_425"] call ACME_fnc_itemCount) > 0;
    };
    if (_available) exitWith {_source = _unit;};
} forEach ([_medic, _patient] call ACME_fnc_treatmentSupplyOrder);
_source
