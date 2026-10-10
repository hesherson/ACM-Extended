#include "..\script_component.hpp"
/*
 * Author: Glowbal, mharis001
 * Collect treatment actions for medical menu from config.
 * Adds dragging actions if it exists.
 *
 * Arguments:
 * None
 *
 * Return Value:
 * None
 *
 * Example:
 * [] call ace_medical_gui_fnc_collectActions
 *
 * Public: No
 */

ACEGVAR(medical_gui,actions) = [];

{
    private _configName = configName _x;
    private _displayName = getText (_x >> "displayName");
    private _category = getText (_x >> "category");
    private _condition = compile format [QUOTE([ARR_4(ACE_player,ACEGVAR(medical_gui,target),%1 select ACEGVAR(medical_gui,selectedBodyPart),'%2')] call DACEFUNC(ACE_ADDON(medical_treatment),canTreatCached)), ALL_BODY_PARTS, _configName];
    private _statement = compile format [QUOTE([ARR_4(ACE_player,ACEGVAR(medical_gui,target),%1 select ACEGVAR(medical_gui,selectedBodyPart),'%2')] call DACEFUNC(ACE_ADDON(medical_treatment),treatment)), ALL_BODY_PARTS, _configName];
    private _items = getArray (_x >> "items");
    private _menuIcon = (["",getText (_x >> "ACM_menuIcon")] select GVAR(showActionItemIcons));

    ACEGVAR(medical_gui,actions) pushBack [_displayName, _category, _condition, _statement, _items, _menuIcon];
} forEach configProperties [configFile >> QACEGVAR(medical_treatment,actions), "isClass _x"];


if ("ace_dragging" call ACEFUNC(common,isModLoaded)) then {
    ACEGVAR(medical_gui,actions) pushBack [
        ACELLSTRING(dragging,Drag), "drag",
        {
            ACE_player != ACEGVAR(medical_gui,target) && {[ACE_player, ACEGVAR(medical_gui,target)] call ACEFUNC(dragging,canDrag)}
        },
        {
            ACEGVAR(medical_gui,pendingReopen) = false;
            [ACE_player, ACEGVAR(medical_gui,target)] call ACEFUNC(dragging,startDrag);
        }
    ];

    ACEGVAR(medical_gui,actions) pushBack [
        ACELLSTRING(dragging,Carry), "drag",
        {
            ACE_player != ACEGVAR(medical_gui,target) && {[ACE_player, ACEGVAR(medical_gui,target)] call ACEFUNC(dragging,canCarry)}
        },
        {
            ACEGVAR(medical_gui,pendingReopen) = false;
            [ACE_player, ACEGVAR(medical_gui,target)] call ACEFUNC(dragging,startCarry);
        }
    ];

    ACEGVAR(medical_gui,actions) pushBack [
        LLSTRING(AssistCarry), "drag",
        {
            ACE_player != ACEGVAR(medical_gui,target) && {[ACE_player, ACEGVAR(medical_gui,target)] call ACEFUNC(dragging,canCarry) && {!(ACEGVAR(medical_gui,target) getVariable [QEGVAR(core,CarryAssist_State), false])}}
        },
        {
            ACEGVAR(medical_gui,pendingReopen) = false;
            [ACE_player, ACEGVAR(medical_gui,target)] call EFUNC(core,beginCarryAssist);
        }
    ];

    ACEGVAR(medical_gui,actions) pushBack [
        LELSTRING(evacuation,ConvertCasualty), "drag",
        {
            ACE_player != ACEGVAR(medical_gui,target) && {[ACE_player, ACEGVAR(medical_gui,target)] call EFUNC(evacuation,canConvert)}
        },
        {
            [ACE_player, ACEGVAR(medical_gui,target)] call EFUNC(evacuation,convertCasualtyAction);
        }
    ];

    ACEGVAR(medical_gui,actions) pushBack [
        LELSTRING(core,SupinePosition_Action), "drag",
        {
            [ACEGVAR(medical_gui,target)] call ACEFUNC(common,isAwake) && ACE_player != ACEGVAR(medical_gui,target) && {!(ACEGVAR(medical_gui,target) getVariable [QEGVAR(core,Lying_State), false]) && stance ACEGVAR(medical_gui,target) == "PRONE" && currentWeapon ACEGVAR(medical_gui,target) == ""}
        },
        {
            if (ACEGVAR(medical_gui,target) getVariable [QEGVAR(core,Lying_State), false]) exitWith {};
            [ACEGVAR(medical_gui,target), "AinjPpneMstpSnonWrflDnon_rolltoback", 2] call ACEFUNC(common,doAnimation);

            [{
                ACEGVAR(medical_gui,target) setVariable [QEGVAR(core,Lying_State), true, true];
                [QACEGVAR(common,switchMove), [ACEGVAR(medical_gui,target), "ACM_LyingState"]] call CBA_fnc_globalEvent;
                if (!isNil "ACME_fnc_aiProtectionSync") then {
                    ["ACME_aiProtectionRefresh", [ACEGVAR(medical_gui,target)], ACEGVAR(medical_gui,target)] call CBA_fnc_targetEvent;
                };
                [QEGVAR(core,getUpPrompt), [ACEGVAR(medical_gui,target)], ACEGVAR(medical_gui,target)] call CBA_fnc_targetEvent;
                [QACEGVAR(common,displayTextStructured), [LELSTRING(core,SupinePosition_Hint), 2, ACEGVAR(medical_gui,target)], ACEGVAR(medical_gui,target)] call CBA_fnc_targetEvent;
                [LELSTRING(core,SupinePosition_Complete), 2, ACE_player] call ACEFUNC(common,displayTextStructured);
            }, [], 1.85] call CBA_fnc_waitAndExecute;
        }
    ];
};

// testing code for multi-line
// for "_i" from 0 to 12 do {
//     GVAR(actions) pushBack [format ["Example %1", _i], "medication", {true}, compile format ['systemChat "%1"', _i]]
// };

private _actions = missionNamespace getVariable ["ace_medical_gui_actions", []];
private _configs = configProperties [configFile >> "ace_medical_treatment_actions", "isClass _x"];
private _prefixValid = count _actions >= count _configs;
if (_prefixValid) then {
    {
        private _row = _actions select _forEachIndex;
        if ((_row param [0, ""]) != getText (_x >> "displayName") || {
            (_row param [1, ""]) != getText (_x >> "category")
        }) exitWith {_prefixValid = false;};
    } forEach _configs;
};
if (!_prefixValid) exitWith {

};
private _mapped = [];
ACME_menuExamineGroups = [] call ACME_fnc_menuExamineGroups;
{
    private _row = +(_actions select _forEachIndex);
    ([_x] call ACME_fnc_menuActionInfo) params ["_category", "_bucket", "_hide"];
    if (!_hide) then {
        _row set [1, _category];
        // Slots 6/7 remain reserved for renderer color/header metadata.
        _row set [6, []];
        _row set [7, ""];
        _row set [8, configName _x];
        _row set [9, _bucket];
        // B39: preserve ACE's native dog-tag icon even after Examine regrouping.
        if (toLower (configName _x) == "checkdogtags") then {
            _row set [5, "\z\ace\addons\dogtags\data\dogtag_icon_ca.paa"];
        };
        _mapped pushBack _row;
    };
} forEach _configs;
// Keep all native drag, carry, evacuation and position rows in their original order.
_mapped append (_actions select [count _configs]);
private _iv = _mapped select {(_x param [9, ""]) == "iv_access"};
private _narc = _mapped select {(_x param [9, ""]) == "narc_box"};
// The same class table orders both flat rows and dropdown children. No localized
// name sorting, condition evaluation, or callback rewriting happens here.
private _dogTags = _mapped select {toLower (_x param [8, ""]) == "checkdogtags"};
private _examine = _mapped select {
    (_x param [1, ""]) == "examine" && {toLower (_x param [8, ""]) != "checkdogtags"}
};
private _orderedExamine = [];
{
    {
        private _class = _x;
        _orderedExamine append (_examine select {toLower (_x param [8, ""]) == _class});
    } forEach (_x select 2);
} forEach ACME_menuExamineGroups;
// Unrecognized addon examinations remain visible and retain their original order.
_orderedExamine append (_examine select {(_x param [9, ""]) == ""});
private _rest = _mapped select {
    (_x param [1, ""]) != "examine" && {!((_x param [9, ""]) in ["iv_access", "narc_box"])}
};
// B216: order the actual action rows, so both flat lists and Breathing dropdown children
// place the timed respiratory observation immediately below Check Breathing in any language.
private _measures = _rest select {toLower (_x param [8, ""]) == "acme_measurerespirations"};
if !(_measures isEqualTo []) then {
    private _checkIndex = _rest findIf {toLower (_x param [8, ""]) == "checkbreathing"};
    if (_checkIndex >= 0) then {
        _rest = _rest select {toLower (_x param [8, ""]) != "acme_measurerespirations"};
        _checkIndex = _rest findIf {toLower (_x param [8, ""]) == "checkbreathing"};
        _rest = (_rest select [0, _checkIndex + 1]) + _measures
            + (_rest select [_checkIndex + 1, (count _rest) - _checkIndex - 1]);
    };
};
ace_medical_gui_actions = _iv + _narc + _orderedExamine + _rest + _dogTags;
