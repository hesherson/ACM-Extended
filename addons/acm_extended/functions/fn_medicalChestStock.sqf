/* Seed from the live medical inventory catalog so later ACE/ACM items are picked up automatically. */
params ["_cargo"];
private _catalog = missionNamespace getVariable "ACME_medicalChestCatalog";
if (isNil "_catalog") then {
    private _filter = "isClass _x && {getNumber (_x >> 'ACE_isMedicalItem') == 1}
        && {getNumber (_x >> 'ace_arsenal_hide') != 1}
        && {getText (_x >> 'ACME_inventoryKind') == ''}
        && {if (isNumber (_x >> 'scopeArsenal')) then {
            getNumber (_x >> 'scopeArsenal') == 2 && {getNumber (_x >> 'scope') > 0}
        } else {getNumber (_x >> 'scope') == 2}}";
    _catalog = ["CfgWeapons", "CfgMagazines", "CfgVehicles"] apply {
        (configProperties [configFile >> _x, _filter, true]) apply {configName _x}
    };
    missionNamespace setVariable ["ACME_medicalChestCatalog", _catalog];
};
_catalog params ["_items", "_magazines", "_vehicles"];
{_cargo addItemCargoGlobal [_x, 1];} forEach _items;
{_cargo addMagazineCargoGlobal [_x, 1];} forEach _magazines;
{
    if (getNumber (configFile >> "CfgVehicles" >> _x >> "isBackpack") == 1) then {
        _cargo addBackpackCargoGlobal [_x, 1];
    };
} forEach _vehicles;
