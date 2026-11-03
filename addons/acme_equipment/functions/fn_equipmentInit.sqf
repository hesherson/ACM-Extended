if (isServer) then {
    [{call ACME_fnc_equipmentTick;},0.5,[]] call CBA_fnc_addPerFrameHandler;
};
if (!hasInterface) exitWith {};
[{call ACME_fnc_equipmentCoolerVisualTick;},0.5,[]] call CBA_fnc_addPerFrameHandler;
[{
    private _root=["ACME_PatientEquipment","Medical Equipment","",{},{true}] call ace_interact_menu_fnc_createAction;
    ["CAManBase",0,["ACE_MainActions"],_root,true] call ace_interact_menu_fnc_addActionToClass;
    {
        _x params ["_kind","_label","_item"];
        private _a=["ACME_Setup_"+_kind,_label,"",{
            params ["_target","","_data"];[_target,_data select 0] call ACME_fnc_equipmentSetup;
        },{
            params ["_target","_player","_data"];
            alive _player && {([_player,_data select 1] call ACME_fnc_itemCount)>0} && {isNull (_target getVariable ["ACME_eq_"+(_data select 0),objNull])}
        },{},[_kind,_item]] call ace_interact_menu_fnc_createAction;
        ["CAManBase",0,["ACE_MainActions","ACME_PatientEquipment"],_a,true] call ace_interact_menu_fnc_addActionToClass;
    } forEach [["pro","Set Up Tempus Pro","ACME_TempusPro_Item"],["ls","Set Up Tempus LS","ACME_TempusLS_Item"],["accu","Set Up ACCUVAC","ACM_ACCUVAC"]];
    private _cooler=["ACME_PatientCoolers","Set Down Blood Cooler","",{},{count ([_player] call ACME_fnc_coolerRows)>0},{_this call ACME_fnc_equipmentCoolerMenu;}] call ace_interact_menu_fnc_createAction;
    ["CAManBase",0,["ACE_MainActions","ACME_PatientEquipment"],_cooler,true] call ace_interact_menu_fnc_addActionToClass;
    private _vent=["ACME_Setup_Vent","Connect Ventway","",{[_player,_target] call ACME_fnc_ventConnectPatient;},{([_player,"ACME_Ventilator"] call ACME_fnc_itemCount)>0 && {!(_target getVariable ["ACME_vent_onPatient",false])}}] call ace_interact_menu_fnc_createAction;
    ["CAManBase",0,["ACE_MainActions","ACME_PatientEquipment"],_vent,true] call ace_interact_menu_fnc_addActionToClass;
    private _sensors=["ACME_TempusSensors","Patient Connections","",{},{!isNull (_target getVariable ["acme_tempus_pat",objNull])},{_this call ACME_fnc_equipmentSensorMenu;}] call ace_interact_menu_fnc_createAction;
    ["ACME_TempusPro",0,["ACME_tempus_root"],_sensors,true] call ace_interact_menu_fnc_addActionToClass;
    private _lsConnections=["ACME_LSConnections","Patient Connections","",{},{!isNull (_target getVariable ["acme_tempusls_pat",objNull])},{_this call ACME_fnc_equipmentLsConnections;}] call ace_interact_menu_fnc_createAction;
    ["ACME_TempusLS",0,["ACME_tempusls_root"],_lsConnections,true] call ace_interact_menu_fnc_addActionToClass;
    private _pair=["ACME_LSPair","Pair with Tempus Pro","",{[_target] call ACME_fnc_tempusLsPair;},{true}] call ace_interact_menu_fnc_createAction;
    ["ACME_TempusLS",0,["ACME_tempusls_root"],_pair,true] call ace_interact_menu_fnc_addActionToClass;
    private _suction=["ACME_UseAccuvac","Use ACCUVAC","",{[_player,_target getVariable ["ACME_eq_patient",objNull],1] call ACME_fnc_suctionOpen;},{!isNull (_target getVariable ["ACME_eq_patient",objNull])}] call ace_interact_menu_fnc_createAction;
    ["ACME_AccuvacRescue",0,[],_suction,true] call ace_interact_menu_fnc_addActionToClass;
    private _pickup=["ACME_PickAccuvac","Pick Up ACCUVAC","",{
        [_player,_target getVariable ["ACME_eq_patient",objNull],"accu","pickup",false,[],_target] remoteExecCall ["ACME_fnc_equipmentRequest",2];
    },{(_target getVariable ["ACME_eq_kind",""])=="accu" && {!(_target getVariable ["ACME_eq_busy",false])}}] call ace_interact_menu_fnc_createAction;
    ["ACME_AccuvacRescue",0,[],_pickup,true] call ace_interact_menu_fnc_addActionToClass;
    private _panel=["ACME_VentwayPanel","Open Ventway","",{[_target getVariable ["ACME_eq_patient",objNull]] call ACME_fnc_ventPanelOpen;},{!isNull (_target getVariable ["ACME_eq_patient",objNull])}] call ace_interact_menu_fnc_createAction;
    private _disconnect=["ACME_VentwayRecover","Disconnect and Recover Ventway","",{[_player,_target getVariable ["ACME_eq_patient",objNull]] call ACME_fnc_ventDisconnectPatient;},{!isNull (_target getVariable ["ACME_eq_patient",objNull])}] call ace_interact_menu_fnc_createAction;
    ["ACME_VentwaySparrow_Bare",0,[],_panel,true] call ace_interact_menu_fnc_addActionToClass;
    ["ACME_VentwaySparrow_Bare",0,[],_disconnect,true] call ace_interact_menu_fnc_addActionToClass;
    private _open=["ACME_OpenWorldCooler","Open Blood Cooler","",{[_target] call ACME_fnc_equipmentCoolerOpen;},{!(_target getVariable ["ACME_coolerRetired",false]) && {!(_target getVariable ["ACME_coolerPacking",false])}}] call ace_interact_menu_fnc_createAction;
    {[_x,0,["ACE_MainActions"],_open,true] call ace_interact_menu_fnc_addActionToClass;} forEach ["ACME_BloodCoolerBox_CSWB1U","ACME_BloodCoolerBox_CSWB2U","ACME_BloodCoolerBox_CSWB4U"];
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
