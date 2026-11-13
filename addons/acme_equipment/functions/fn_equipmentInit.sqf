if (isServer) then {
    [{call ACME_fnc_equipmentTick;},0.5,[]] call CBA_fnc_addPerFrameHandler;
};
if (!hasInterface) exitWith {};
[{call ACME_fnc_equipmentCableVisualTick;},0.1,[]] call CBA_fnc_addPerFrameHandler;
[{call ACME_fnc_equipmentCoolerVisualTick;},0.5,[]] call CBA_fnc_addPerFrameHandler;
[{
    private _mount=["ACME_MountEquipment","Mount Monitor","",{},{isNull (_target getVariable ["ACME_eq_device",objNull])},{_this call ACME_fnc_equipmentMountMenu;}] call ace_interact_menu_fnc_createAction;
    private _unmount=["ACME_ReleaseEquipment","Release Monitor","",{[_player,_target,_target getVariable ["ACME_eq_device",objNull],false,_target getVariable ["ACME_eq_mountEpoch",0]] remoteExecCall ["ACME_fnc_equipmentMountRequest",2];},{!isNull (_target getVariable ["ACME_eq_device",objNull])}] call ace_interact_menu_fnc_createAction;
    {[_x,0,[],_mount,true] call ace_interact_menu_fnc_addActionToClass;[_x,0,[],_unmount,true] call ace_interact_menu_fnc_addActionToClass;} forEach ["ACME_TempusPro_Mount","ACME_TempusLS_Mount"];
    private _releaseMount=["ACME_ReleaseMonitorMount","Release from Mount","",{[_player,_target getVariable ["ACME_eq_mount",objNull],_target,false,_target getVariable ["ACME_eq_mountEpoch",0]] remoteExecCall ["ACME_fnc_equipmentMountRequest",2];},{_target getVariable ["ACME_eq_mounted",false]}] call ace_interact_menu_fnc_createAction;
    {[_x select 0,0,[_x select 1],_releaseMount,true] call ace_interact_menu_fnc_addActionToClass;} forEach [["ACME_TempusPro","ACME_tempus_root"],["ACME_TempusLS","ACME_tempusls_root"]];
    private _accuRoot = ["ACME_AccuvacRoot","ACCUVAC Rescue","",{},{true},{},[],[0,0,0.08],3.5] call ace_interact_menu_fnc_createAction;
    ["ACME_AccuvacRescue",0,[],_accuRoot,true] call ace_interact_menu_fnc_addActionToClass;

    private _pickup=["ACME_PickAccuvac","Pick Up ACCUVAC","",{
        [_player,_target getVariable ["ACME_eq_patient",objNull],"accu","pickup",false,[],_target] remoteExecCall ["ACME_fnc_equipmentRequest",2];
    },{(_target getVariable ["ACME_eq_kind",""])=="accu" && {!(_target getVariable ["ACME_eq_busy",false])}}] call ace_interact_menu_fnc_createAction;
    ["ACME_AccuvacRescue",0,["ACME_AccuvacRoot"],_pickup,true] call ace_interact_menu_fnc_addActionToClass;
    private _open=["ACME_OpenWorldCooler","Open Blood Cooler","",{[_target] call ACME_fnc_equipmentCoolerOpen;},{!(_target getVariable ["ACME_coolerRetired",false]) && {!(_target getVariable ["ACME_coolerPacking",false])}}] call ace_interact_menu_fnc_createAction;
    {[_x,0,["ACE_MainActions"],_open,true] call ace_interact_menu_fnc_addActionToClass;} forEach ["ACME_BloodCoolerBox_CSWB1U","ACME_BloodCoolerBox_CSWB2U","ACME_BloodCoolerBox_CSWB4U"];
    private _rotate = ["ACME_RotateEquipment","Rotate towards me","",{
        [_player,_target] remoteExecCall ["ACME_fnc_equipmentRotate",2];
    },{[_player,_target] call ACME_fnc_equipmentRotateReady;}] call ace_interact_menu_fnc_createAction;
    {
        _x params ["_class","_parent"];
        [_class,0,_parent,_rotate,true] call ace_interact_menu_fnc_addActionToClass;
    } forEach [
        ["ACME_TempusPro",["ACME_tempus_root"]],
        ["ACME_TempusLS",["ACME_tempusls_root"]],
        ["ACME_AccuvacRescue",["ACME_AccuvacRoot"]],
        ["ACME_VentwaySparrow_Bare",[]],
        ["ACME_TempusPro_Mount",[]],["ACME_HPMK_Pouch",[]],
        ["ACME_BloodCoolerBox_CSWB1U",["ACE_MainActions"]],
        ["ACME_BloodCoolerBox_CSWB2U",["ACE_MainActions"]],
        ["ACME_BloodCoolerBox_CSWB4U",["ACE_MainActions"]],
        ["Land_HelipadEmpty_F",[]]
    ];
}] call CBA_fnc_execNextFrame;

["CAManBase","InventoryOpened",{
    params ["_actor","_container"];
    if ((typeOf _container) in ["ACME_BloodCoolerBox_CSWB1U","ACME_BloodCoolerBox_CSWB2U","ACME_BloodCoolerBox_CSWB4U"]) then {
        uiNamespace setVariable ["ACME_eqCargoBox",_container];
        [_actor,_container,true] remoteExecCall ["ACME_fnc_equipmentCoolerLease",2];
    };
    false
}] call CBA_fnc_addClassEventHandler;
["CAManBase","InventoryClosed",{
    params ["_actor","_container"];
    private _box=uiNamespace getVariable ["ACME_eqCargoBox",objNull];
    if (!isNull _box) then {[_actor,_box,false] remoteExecCall ["ACME_fnc_equipmentCoolerLease",2];};
    uiNamespace setVariable ["ACME_eqCargoBox",objNull];
}] call CBA_fnc_addClassEventHandler;
