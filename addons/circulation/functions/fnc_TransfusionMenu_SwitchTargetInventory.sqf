#include "..\script_component.hpp"
#include "..\TransfusionMenu_defines.hpp"
/*
 * Author: Blue
 * Handle switching inventory target.
 *
 * Arguments:
 * None
 *
 * Return Value:
 * None
 *
 * Example:
 * [] call ACM_circulation_fnc_TransfusionMenu_SwitchTargetInventory;
 *
 * Public: No
 */

private _targetInventory = GVAR(TransfusionMenu_Selected_Inventory);

_targetInventory = _targetInventory + 1;

private _vehicle = objectParent ACE_player;

switch (_targetInventory) do {
    case 1: {
        if (ACE_player == GVAR(TransfusionMenu_Target)) then {
            if !(isNull _vehicle) then {
                _targetInventory = 2;
            } else {
                _targetInventory = 0;
            };
        };
    };
    case 2: {
        if (isNull _vehicle) then {
            _targetInventory = 0;
        };
    };
    default {
        if (_targetInventory > 2) then {
            _targetInventory = 0;
        };
    };
};

GVAR(TransfusionMenu_Selected_Inventory) = _targetInventory;

private _display = uiNamespace getVariable [QGVAR(TransfusionMenu_DLG), displayNull];

private _ctrlInventorySelectText = _display displayCtrl IDC_TRANSFUSIONMENU_SELECTION_INV_TEXT;

private _text = [LLSTRING(Common_Self), LLSTRING(Common_Patient), LLSTRING(Common_Vehicle)] select GVAR(TransfusionMenu_Selected_Inventory);

private _target = [ACE_player, GVAR(TransfusionMenu_Target), _vehicle] select GVAR(TransfusionMenu_Selected_Inventory);

_ctrlInventorySelectText ctrlSetText (format [LLSTRING(Common_InventoryTarget), _text]);

private _cachedItems = if (GVAR(TransfusionMenu_Selected_Inventory) == 2) then {
    if (isNull _vehicle) then {[]} else {(getItemCargo _vehicle) select 0}
} else {
    [_target, 0] call ACME_fnc_itemList
};

private _fluidsArray = +GVAR(Fluids_Array);
private _fluidsArrayData = +GVAR(Fluids_Array_Data);

// Fork-owned fluid reconciliation at the point of use. Some compatibility addons rebuild ACM's native arrays
// after postInit; that previously made Extended crystalloid bags (notably Plasma-Lyte) vanish from the menu even
// though the item and physiology were valid. Keep item/data pairs aligned every time the inventory list is built.
private _extendedFluids = [
    ["ACM_EsmololBag", "EsmololIV_250"],
    ["ACME_HTSBag", "HTSIV_250"],
    ["ACME_MagnesiumBag", "MagnesiumIV_50"],
    ["ACME_MannitolBag", "MannitolIV_500"],
    ["ACME_PlasmaLyteBag", "PlasmaLyteIV_1000"],
    ["ACME_PlasmaLyteBag_500", "PlasmaLyteIV_500"],
    ["ACME_PlasmaLyteBag_250", "PlasmaLyteIV_250"],
    ["ACME_PlasmaLyteBag_100", "PlasmaLyteIV_100"],
    ["ACME_SalineBag_50", "SalineIV_50"],
    ["ACME_SalineBag_100", "SalineIV_100"]
];
{
    _x params ["_item", "_fluidData"];
    private _i = _fluidsArray find _item;
    if (_i < 0) then {
        _fluidsArray pushBack _item;
        _fluidsArrayData pushBack _fluidData;
    } else {
        while {count _fluidsArrayData <= _i} do { _fluidsArrayData pushBack ""; };
        _fluidsArrayData set [_i, _fluidData];
    };
} forEach _extendedFluids;

private _activeFreshBloodList = missionNamespace getVariable [QGVAR(FreshBloodList), createHashMap];

if (count _activeFreshBloodList > 0) then {
    {
        // HashMap forEach exposes the real key as _x and the value as _y. _forEachIndex is only the iteration
        // counter and is not a donor-bag ID. Using it made multiplayer/JIP registries enumerate the wrong bags.
        private _id = _x;
        private _entryData = _y;
        if !(_id isEqualType 0 && {_id > 0} && {_entryData isEqualType []} && {count _entryData >= 2}) then { continue; };
        private _volume = _entryData param [1, 0];
        if !(_volume in [250, 500]) then { continue; };

        private _item = format ["%1_%2", (["FreshBlood", _volume] call FUNC(formatFluidBagName)), _id];
        private _fluidData = format ["%1_%2", (["FreshBlood", _volume, -1, true] call FUNC(formatFluidBagName)), _id];
        if (isClass (configFile >> "CfgWeapons" >> _item)) then {
            private _i = _fluidsArray find _item;
            if (_i < 0) then {
                _fluidsArray pushBack _item;
                _fluidsArrayData pushBack _fluidData;
            } else {
                while {count _fluidsArrayData <= _i} do { _fluidsArrayData pushBack ""; };
                _fluidsArrayData set [_i, _fluidData];
            };
        };
    } forEach _activeFreshBloodList;
};

// Inventory is authoritative for whether a filled donor bag is physically present. Add any valid unique fresh-blood
// item found there even if its public registry update arrived one frame after this menu was opened. The registry is
// still used for blood-type metadata, but it can no longer make the actual bag disappear from the transfusion list.
{
    private _cfg = configFile >> "CfgWeapons" >> _x;
    if ((getNumber (_cfg >> "uniqueBag")) <= 0) then { continue; };
    private _parts = _x splitString "_";
    if (count _parts < 4 || {(_parts select 0) != "ACM"} || {(_parts select 1) != "FreshBloodBag"}) then { continue; };
    private _volume = parseNumber (_parts select 2);
    private _id = parseNumber (_parts select 3);
    if !(_volume in [250, 500] && {_id > 0}) then { continue; };
    private _fluidData = format ["FreshBloodBag_%1_%2", _volume, _id];
    private _i = _fluidsArray find _x;
    if (_i < 0) then {
        _fluidsArray pushBack _x;
        _fluidsArrayData pushBack _fluidData;
    } else {
        while {count _fluidsArrayData <= _i} do { _fluidsArrayData pushBack ""; };
        _fluidsArrayData set [_i, _fluidData];
    };
} forEach _cachedItems;

private _index = _fluidsArray findIf {_x in _cachedItems};

if (_index < 0) exitWith {};

private _ctrlInventoryPanel = _display displayCtrl IDC_TRANSFUSIONMENU_RIGHTLISTPANEL;

lbClear _ctrlInventoryPanel;

private _fnc_addToInventoryPanel = {
    params ["_ctrlInventoryPanel", "_fluidsArrayData", "_count", "_entry", "_index"];

    private _config = (configFile >> "CfgWeapons" >> _entry);
    private _name = "";

    if ((getNumber (_config >> "uniqueBag")) > 0) then {
        ((configName _config) splitString "_") params ["","","_volume","_id"];

        private _freshEntry = [(parseNumber _id)] call FUNC(getFreshBloodEntry);
        if (_freshEntry isEqualType [] && {count _freshEntry >= 3}) then {
            private _bloodType = _freshEntry param [2, -1];
            private _bloodTypeString = [_bloodType, 1] call FUNC(convertBloodType);
            _name = format [C_LLSTRING(FreshBloodBag_Short), (format ["%1 (%2ml) [%3]", _bloodTypeString, _volume, _id])];
        } else {
            // Registry metadata can trail an inventory transfer on MP/JIP. Keep the real bag visible while it catches up.
            private _shortName = getText (_config >> "shortName");
            _name = if (_shortName != "") then {_shortName} else {getText (_config >> "displayName")};
            if (_name == "") then {_name = _entry;};
        };
    } else {
        private _shortName = getText (_config >> "shortName");
        _name = if (_shortName != "") then {_shortName} else {getText (_config >> "displayName")};
        if (_name == "") then {_name = _entry;};
    };

    private _i = _ctrlInventoryPanel lbAdd _name;
    _ctrlInventoryPanel lbSetPicture [_i, getText (_config >> "picture")];
    _ctrlInventoryPanel lbSetData [_i, (format ["%1|%2",_entry,_fluidsArrayData select _index])];
    _ctrlInventoryPanel lbSetTooltip [_i, (format [LLSTRING(Common_Available), _count])];
};

if (GVAR(TransfusionMenu_Selected_Inventory) == 2) then {
    {
        private _inventory = getItemCargo _vehicle;
        private _classname = _x;
        private _targetIndex = (_inventory select 0) findIf {_x == _classname};
        if (_targetIndex < 0) then {
            continue;
        };
        private _count = (_inventory select 1) select _targetIndex;

        if (_count > 0) then {
            [_ctrlInventoryPanel, _fluidsArrayData, _count, _x, _forEachIndex] call _fnc_addToInventoryPanel;
        };
    } forEach _fluidsArray;
} else {
    {
        private _count = [_target, _x] call ACME_fnc_itemCount;

        if (_count > 0) then {
            [_ctrlInventoryPanel, _fluidsArrayData, _count, _x, _forEachIndex] call _fnc_addToInventoryPanel;
        };
    } forEach _fluidsArray;
};
