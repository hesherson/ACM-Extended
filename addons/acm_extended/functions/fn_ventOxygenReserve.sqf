/* Read actual loose reserve units; packed EFAK cylinders retain their native charge API.
   No inventory mutation. Return [available, units]; -1 means packed charge not exposed. */
params [["_source",objNull,[objNull]]];
if (isNull _source) exitWith {[false,0]};
private _units=0;
{
    {
        if ((_x select 0)=="ACM_OxygenTank_425" && {(_x select 1)>0}) then {_units=_units+(_x select 1);};
    } forEach magazinesAmmoCargo _x;
} forEach [uniformContainer _source,vestContainer _source,backpackContainer _source];
if (_units>0) exitWith {[true,_units]};
if (!isNil "efak_medical_fnc_drawCharge" && {([_source,"ACM_OxygenTank_425"] call ACME_fnc_itemCount)>0}) exitWith {[true,-1]};
[false,0]
