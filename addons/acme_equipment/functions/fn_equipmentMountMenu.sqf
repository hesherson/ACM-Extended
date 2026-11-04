params ["_mount"];
private _kind=getText(configOf _mount >> "ACME_eq_mountKind");
if !(_kind in ["pro","ls"]) exitWith {[]};
private _class=["ACME_TempusPro","ACME_TempusLS"] select (_kind=="ls");
private _devices=(nearestObjects [_mount,[_class],2.5]) select {(_x getVariable ["ACME_eq_kind",""])==_kind
    && {!(_x getVariable ["ACME_eq_busy",false])} && {isNull attachedTo _x}};
private _number=0;
_devices apply {
    _number=_number+1;
    private _label=format ["Mount %1 (#%2)",["Tempus Pro","Tempus LS"] select (_kind=="ls"),_number];
    private _action=["ACME_Mount_"+netId _x,_label,"",{
        params ["_mount","_actor","_device"];
        [_actor,_mount,_device,true,_mount getVariable ["ACME_eq_mountEpoch",0]] remoteExecCall ["ACME_fnc_equipmentMountRequest",2];
    },{true},{},_x] call ace_interact_menu_fnc_createAction;
    [_action,[],_mount]
}
