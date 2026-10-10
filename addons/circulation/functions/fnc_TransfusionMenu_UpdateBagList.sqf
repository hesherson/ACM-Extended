#include "..\script_component.hpp"
#include "..\TransfusionMenu_defines.hpp"
/*
 * Author: Blue
 * Handle updating tranfusion bag list.
 *
 * Arguments:
 * 0: Is Update? <BOOL>
 *
 * Return Value:
 * None
 *
 * Example:
 * [false] call ACM_circulation_fnc_TransfusionMenu_UpdateBagList;
 *
 * Public: No
 */

params [["_update", false]];

private _display = uiNamespace getVariable [QGVAR(TransfusionMenu_DLG), displayNull];

private _ctrlBagPanel = _display displayCtrl IDC_TRANSFUSIONMENU_LEFTLISTPANEL;

private _IVBagsOnBodyPart = (GVAR(TransfusionMenu_Target) getVariable [QGVAR(IV_Bags), createHashMap]) getOrDefault [GVAR(TransfusionMenu_Selected_BodyPart), []];

// The left list represents one selected IV/IO access, not every bag on the limb.
// Keep the native body-part index beside each filtered row so multiple lines on the
// same arm cannot force a full list rebuild every update.
private _selectedBags = [];
{
    _x params ["", "", "", ["_accessSite", -1], ["_iv", false]];
    if (_accessSite == GVAR(TransfusionMenu_Selected_AccessSite) && {_iv isEqualTo GVAR(TransfusionMenu_SelectIV)}) then {
        // Saved/remote state can briefly still contain an old phantom beside its replacement.
        // Keep native indices intact, but never render that spent slot as a second active bag.
        private _type = _x param [0, ""];
        private _replaced = false;
        if (_type in ["ACME_Empty", "ACME_EmptySaline"]) then {
            private _types = if (_type == "ACME_Empty") then {["Blood", "FreshBlood"]} else {["Saline", "ACME_SalineY"]};
            private _minimum = if (_type == "ACME_Empty") then {0.01} else {0.5};
            _replaced = (_IVBagsOnBodyPart findIf {
                (_x param [0, ""]) in _types && {(_x param [1, 0]) > _minimum}
                    && {(_x param [3, -1]) == _accessSite} && {(_x param [4, false]) isEqualTo _iv}
            }) >= 0;
        };
        if (!_replaced) then {_selectedBags pushBack [_x, _forEachIndex];};
    };
} forEach _IVBagsOnBodyPart;

if !(_update) then {
    private _previousRow = lbCurSel _ctrlBagPanel;
    private _wasRebuilding = _display getVariable ["ACME_txRebuilding", false];
    _display setVariable ["ACME_txRebuilding", true];
    lbClear _ctrlBagPanel;
    GVAR(TransfusionMenu_Selection_IVBags) = [];

    if (count _selectedBags < 1) exitWith {_display setVariable ["ACME_txRebuilding", _wasRebuilding];};

    {
        _x params ["_bag", "_trueIndex"];
        _bag params ["_type", "_remainingVolume", "_accessType", "_accessSite", "_iv", "_bloodType", "_volume", ["_id", -1]];

        private _bagIndex = count GVAR(TransfusionMenu_Selection_IVBags);

        GVAR(TransfusionMenu_Selection_IVBags) pushBack [_type, _remainingVolume, _accessType, _accessSite, _iv, _bloodType, _volume, _id, _trueIndex];

        private _itemClassName = [_type, _volume, _bloodType] call FUNC(formatFluidBagName);

        if (_id > -1) then {
            _itemClassName = format ["%1_%2", _itemClassName, _id];
        };

        private _config = (configFile >> "CfgWeapons" >> _itemClassName);
        private _name = "";

        if ((getNumber (_config >> "uniqueBag")) > 0) then {
            ((configName _config) splitString "_") params ["","","_volume","_id"];

            private _freshEntry = [(parseNumber _id)] call FUNC(getFreshBloodEntry);
            if (_freshEntry isEqualType [] && {count _freshEntry >= 3}) then {
                private _bloodType = _freshEntry param [2, -1];
                private _bloodTypeString = [_bloodType, 1] call FUNC(convertBloodType);
                _name = format [C_LLSTRING(FreshBloodBag_Short), (format ["%1 (%2ml) [%3]", _bloodTypeString, _volume, _id])];
            } else {
                private _shortName = getText (_config >> "shortName");
                _name = if (_shortName != "") then {_shortName} else {getText (_config >> "displayName")};
                if (_name == "") then {_name = _itemClassName;};
            };
        } else {
            private _shortName = getText (_config >> "shortName");
            _name = if (_shortName != "") then {_shortName} else {getText (_config >> "displayName")};
            if (_name == "") then {_name = _itemClassName;};
        };
        if !(_type in ["ACME_Empty", "ACME_EmptySaline"]) then {
            _name = [_name, _remainingVolume] call ACME_fnc_fluidLabelVolume;
        };
        private _i = _ctrlBagPanel lbAdd _name;
        _ctrlBagPanel lbSetPicture [_i, getText (_config >> "picture")];
        _ctrlBagPanel lbSetValue [_i, _bagIndex];
        _ctrlBagPanel lbSetTooltip [_i, (format [([(LLSTRING(TransfusionMenu_FluidRemaining)), ("%1ml filled")] select (_type == "FBTK")), round(_remainingVolume)])];
    } forEach _selectedBags;
    // Keep an existing selection across replacement/topology refreshes, but do not auto-select on first open.
    if (_previousRow >= 0) then {_ctrlBagPanel lbSetCurSel (_previousRow min ((count _selectedBags) - 1));};
    _display setVariable ["ACME_txRebuilding", _wasRebuilding];
} else {
    if (count GVAR(TransfusionMenu_Selection_IVBags) != count _selectedBags) exitWith {
        [false] call FUNC(TransfusionMenu_UpdateBagList);
    };

    private _rebuild = false;
    {
        _x params ["_bag", "_trueIndex"];
        _bag params ["_type", "_remainingVolume", "_accessType", "_accessSite", "_iv", "_bloodType", "_volume", ["_id", -1]];
        private _selectionIndex = _forEachIndex;

        if (_selectionIndex >= count GVAR(TransfusionMenu_Selection_IVBags)) exitWith {
            _rebuild = true;
        };

        (GVAR(TransfusionMenu_Selection_IVBags) select _selectionIndex) params ["_cType", "_cRemainingVolume", "_cAccessType", "_cAccessSite", "_cIV", "_cBloodType", "_cVolume", "_cID", "_cIndex"];

        if (_cIndex != _trueIndex || _cType != _type || _cAccessType != _accessType || _cAccessSite != _accessSite || _cIV isNotEqualTo _iv || _cBloodType != _bloodType || _cVolume != _volume || _cID != _id) exitWith {
            _rebuild = true;
        };

        // Overlay-only infusion rows may have been removed from this control. lbValue, not the
        // visible row number, owns the selection tuple. Never relabel a neighbouring fluid.
        private _row = -1;
        for "_r" from 0 to ((lbSize _ctrlBagPanel) - 1) do {
            if ((_ctrlBagPanel lbValue _r) == _selectionIndex) exitWith {_row = _r;};
        };
        // Volume-only ticks update in place: no lbClear, no selection/input churn.
        if (_row >= 0 && {!(_type in ["ACME_Empty", "ACME_EmptySaline"])}) then {
            private _liveLabel = [_ctrlBagPanel lbText _row, _remainingVolume] call ACME_fnc_fluidLabelVolume;
            if (_liveLabel != (_ctrlBagPanel lbText _row)) then {_ctrlBagPanel lbSetText [_row, _liveLabel];};
        };
        if (_cRemainingVolume != _remainingVolume) then {
            GVAR(TransfusionMenu_Selection_IVBags) set [_selectionIndex, [_cType, _remainingVolume, _cAccessType, _cAccessSite, _cIV, _cBloodType, _cVolume, _cID, _trueIndex]];
            if (_row >= 0) then {
                _ctrlBagPanel lbSetTooltip [_row, (format [([(LLSTRING(TransfusionMenu_FluidRemaining)), ("%1ml filled")] select (_type == "FBTK")), round(_remainingVolume)])];
            };
        };
    } forEach _selectedBags;

    if (_rebuild) then {
        [false] call FUNC(TransfusionMenu_UpdateBagList);
    };
};
