params ["_ls"];
private _devices=(nearestObjects [_ls,["ACME_TempusPro"],2.3]) select {(_x getVariable ["ACME_eq_kind",""])=="pro"
    && {!(_x getVariable ["ACME_eq_busy",false])} && {isNull (_x getVariable ["ACME_eq_usbLs",objNull])}};
private _number=0;
_devices apply {
    _number=_number+1;
    private _action=["ACME_USB_"+netId _x,format ["Connect to Tempus Pro (#%1)",_number],"",{
        params ["_ls","_actor","_pro"];
        [_actor,_ls,_pro,true,_ls getVariable ["ACME_eq_usbEpoch",0]] remoteExecCall ["ACME_fnc_equipmentLinkRequest",2];
    },{true},{},_x] call ace_interact_menu_fnc_createAction;
    [_action,[],_ls]
}
