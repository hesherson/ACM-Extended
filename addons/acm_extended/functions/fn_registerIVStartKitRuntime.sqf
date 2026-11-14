/* Loose items use the native Take event. Arsenal and scripted loadouts
 * write gear directly, so expand their kits once the loadout is committed. */
["CAManBase","Take",{
    params ["_unit","","_item"];
    if (!local _unit || {_item find "ACME_IVStartKit_" != 0}) exitWith {};
    [ACME_fnc_ivStartKitUnpack,[_unit,_item]] call CBA_fnc_execNextFrame;
}] call CBA_fnc_addClassEventHandler;

["CAManBase","InventoryClosed",{
    params ["_unit"];
    if (local _unit) then {[ACME_fnc_ivStartKitUnpack,[_unit]] call CBA_fnc_execNextFrame;};
}] call CBA_fnc_addClassEventHandler;

["CBA_loadoutSet",{
    params ["_unit"];
    if (!local _unit || {is3DEN}) exitWith {};
    [ACME_fnc_ivStartKitUnpack,[_unit]] call CBA_fnc_execNextFrame;
}] call CBA_fnc_addEventHandler;

["CAManBase","Local",{
    params ["_unit","_isLocal"];
    if (_isLocal) then {[ACME_fnc_ivStartKitUnpack,[_unit]] call CBA_fnc_execNextFrame;};
}] call CBA_fnc_addClassEventHandler;

if (!hasInterface) exitWith {};
["unit",{
    params ["_unit"];
    [ACME_fnc_ivStartKitUnpack,[_unit]] call CBA_fnc_execNextFrame;
},true] call CBA_fnc_addPlayerEventHandler;
["ace_arsenal_displayClosed",{
    if (is3DEN || {isNil "ace_arsenal_center"}) exitWith {};
    [ACME_fnc_ivStartKitUnpack,[ace_arsenal_center]] call CBA_fnc_execNextFrame;
}] call CBA_fnc_addEventHandler;
[missionNamespace,"arsenalClosed",{
    [ACME_fnc_ivStartKitUnpack,[ACE_player]] call CBA_fnc_execNextFrame;
}] call BIS_fnc_addScriptedEventHandler;
