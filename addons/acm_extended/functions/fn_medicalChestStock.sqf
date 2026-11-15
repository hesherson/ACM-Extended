/* Seed a new container once from the installed medical catalog. */
params ["_cargo", ["_profile", ""]];
private _catalog = missionNamespace getVariable "ACME_medicalChestCatalog";
if (isNil "_catalog") then {
    private _filter = "isClass _x && {getNumber (_x >> 'scope') > 0}
        && {getNumber (_x >> 'ACE_isMedicalItem') == 1 || {getNumber (_x >> 'ACM_isVial') > 0}
            || {(toLowerANSI configName _x) find 'acm_bloodbag_' == 0}}
        && {getNumber (_x >> 'ace_arsenal_hide') != 1}
        && {getText (_x >> 'ACME_inventoryKind') == ''}
        && {getNumber (_x >> 'uniqueBag') == 0}
        && {(toLowerANSI configName _x) find 'acm_freshbloodbag_' != 0}
        && {if (isNumber (_x >> 'scopeArsenal')) then {getNumber (_x >> 'scopeArsenal') == 2}
            else {getNumber (_x >> 'scope') == 2}}";
    _catalog = ["CfgWeapons", "CfgMagazines", "CfgVehicles"] apply {
        (configProperties [configFile >> _x, _filter, true]) apply {configName _x}
    };
    missionNamespace setVariable ["ACME_medicalChestCatalog", _catalog];
};

private _equipment = [
    "ACM_AED", "ACM_ACCUVAC", "ACM_BVM", "ACM_PocketBVM", "ACM_EMMA", "ACM_HPMK",
    "ACME_TempusPro_Item", "ACME_TempusLS_Item", "ACME_Ventilator", "ACM_OxygenTank_425",
    "ACME_BloodWarmer", "ACME_PressureInfuser", "ACME_BloodCooler_CSWB1U",
    "ACME_BloodCooler_CSWB2U", "ACME_BloodCooler_CSWB4U", "ACE_surgicalKit", "ACE_personalAidKit"
];
private _airway = ["_opa", "_npa", "igel", "ettube", "crickit", "suction", "accuvac", "bvm", "ventilat",
    "ventbattery", "ventcircuit", "oxygen", "nrbmask", "emma", "laryng", "bougie", "pulseoximeter", "stethoscope"];
private _dressings = ["bandage", "dressing", "packing", "gauze", "tourniquet", "splint", "chestseal", "burn", "hpmk",
    "elastic", "woundclot", "quikclot", "fielddressing", "suture", "surgicalkit"];
private _access = ["ivline", "ivextension", "ivstartkit", "salinelock", "salineflush", "_iv_", "_io_", "alcoholwipe",
    "tourniquet", "pressureinfuser", "bloodwarmer"];
private _emptySyringes = ["ACM_Syringe_1", "ACM_Syringe_3", "ACM_Syringe_5", "ACM_Syringe_10"];
private _blood = ["bloodbag", "bloodiv", "bloodcooler", "transfusion", "bloodtype", "bloodtest", "bloodwarmer", "plasmaiv", "plasmabag"];
private _wanted = switch (_profile) do {
    case "airway": {_airway};
    case "dressings": {_dressings};
    case "fluids": {_access + ["saline", "plasmalyte", "dextrose", "ringer", "crystalloid", "fluidbag"]};
    case "blood": {_blood + _access};
    case "surgery": {_airway + _dressings + _access + ["aed", "tempus", "thoracostomy", "chesttube", "ncdkit",
        "propofol", "ketamine", "midazolam", "rocuronium", "fentanyl", "lidocaine", "epinephrine", "atropine", "calcium", "txa"]};
    default {[]};
};

_catalog params ["_medicalItems", "_medicalMagazines", "_medicalVehicles"];
// The equipment roster includes devices that can be supplied by optional model addons.
private _items = +_medicalItems;
{if (getNumber (configFile >> "CfgWeapons" >> _x >> "scope") == 2) then {_items pushBackUnique _x;};} forEach _equipment;
private _magazines = +_medicalMagazines;
{if (getNumber (configFile >> "CfgMagazines" >> _x >> "scope") == 2) then {_magazines pushBackUnique _x;};} forEach _equipment;
private _backpacks = _medicalVehicles select {getNumber (configFile >> "CfgVehicles" >> _x >> "isBackpack") == 1};
private _supplyCount = {
    params ["_item", "_isBackpack"];
    private _name = toLowerANSI _item;
    private _emptySyringe = _item in _emptySyringes;
    if (_wanted isNotEqualTo [] && {_wanted findIf {_name find _x >= 0} < 0}
        && {!(_emptySyringe && {_profile in ["blood", "fluids", "surgery"]})}) exitWith {0};
    if (_isBackpack || {_item in _equipment}) exitWith {4};
    if (_profile != "") exitWith {8};
    [8, 24] select (_emptySyringe || {(_dressings + _access) findIf {_name find _x >= 0} >= 0})
};
{
    private _count = [_x, false] call _supplyCount;
    if (_count > 0) then {_cargo addItemCargoGlobal [_x, _count];};
} forEach _items;
{
    private _count = [_x, false] call _supplyCount;
    if (_count > 0) then {_cargo addMagazineCargoGlobal [_x, _count];};
} forEach _magazines;
{
    private _count = [_x, true] call _supplyCount;
    if (_count > 0) then {_cargo addBackpackCargoGlobal [_x, _count];};
} forEach _backpacks;
