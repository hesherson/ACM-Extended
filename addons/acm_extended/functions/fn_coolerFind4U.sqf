/* Find cargo only, never another person's worn equipment. Token 0 is a new public issue item. */
params [["_owner",ACE_player]];
if (isNull _owner) exitWith {[]};
private _found=[];
private _sources=(nearestObjects [_owner,["AllVehicles","ReammoBox_F","WeaponHolderSimulated","GroundWeaponHolder"],6]) select {
    private _parent=objectParent _x;
    _x isNotEqualTo _owner && {!(_x isKindOf "CAManBase")} && {isNull _parent || {!(_parent isKindOf "CAManBase")}}
};
{
    private _source=_x;
    {
        _x params ["_class","_token"];
        if (_class=="ACME_CoolerCarrier_CSWB4U" && {_token>0} && {_token<65535}) then {
            private _record=missionNamespace getVariable [format ["ACME_inventoryToken_%1",_token],[]];
            if (count _record>=9 && {(_record select 0)=="cooler"} && {(_record select 5)=="held"}
                && {(_record select 8)==_class} && {(((_record select 2) select 1) select 0)=="ACME_BloodCooler_CSWB4U"}) exitWith {
                _found=[_source,_class,_token];
            };
        };
    } forEach magazinesAmmoCargo _source;
    if (_found isNotEqualTo []) exitWith {};
    if ("ACME_BloodCooler_CSWB4U" in itemCargo _source) exitWith {_found=[_source,"ACME_BloodCooler_CSWB4U",0];};
} forEach _sources;
_found
