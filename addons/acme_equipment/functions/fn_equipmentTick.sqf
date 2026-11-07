if (!isServer) exitWith {};
private _pending=missionNamespace getVariable ["ACME_eqPending",createHashMap];
{
    private _r=_pending get _x;private _actor=_r get "actor";
    if (isNull _actor) then {
        private _device=_r getOrDefault ["device",objNull];
        if (!isNull _device && {(_r get "phase")=="give"}) then {_device setVariable ["ACME_eq_busy",false,true];};
        _pending deleteAt _x;
    } else {if (serverTime-(_r get "sent")>=2) then {
        if ((_r get "phase")=="refund") then {
            _r set ["sent",serverTime];[_actor,_x] call ACME_fnc_equipmentRefundRequest;
        } else {
            _r set ["sent",serverTime];[_actor,_x,_r get "phase",_r get "item",-1,serverTime] remoteExecCall ["ACME_fnc_equipmentInventory",_actor];
            private _stamp=_r getOrDefault ["stamp",[]];
            if (count _stamp==2 && {(_r get "phase") in ["take","give"]}) then {
                private _origin=(_stamp select 1) select 0;
                if (_origin>1 && {_origin!=owner _actor}) then {
                    [_actor,_x,_r get "phase",_r get "item",-1,-1,true] remoteExecCall ["ACME_fnc_equipmentInventory",_origin];
                };
            };
        };
    };};
} forEach keys _pending;
private _devices=missionNamespace getVariable ["ACME_eqDevices",[]];
{
    private _o=_x;if (isNull _o) then {continue;};
    private _patient=_o getVariable ["ACME_eq_patient",objNull];
    if ((_o getVariable ["ACME_eq_kind",""]) in ["pro","ls"]) then {[_o] call ACME_fnc_equipmentMonitorTick;};
    if ((_o getVariable ["ACME_eq_kind",""])=="vent") then {
        if (isNull _patient || {!(_patient getVariable ["ACME_vent_onPatient",false])}) then {deleteVehicle _o;} else {
            private _oxygen=(_patient getVariable ["ACME_vent_o2Session",""])!="";
            if (_oxygen isNotEqualTo (_o getVariable ["ACME_eq_oxygen",false])) then {[_patient,true] call ACME_fnc_equipmentVent;};
            private _mounted=!isNull objectParent _patient;
            _o hideObjectGlobal _mounted;
            if (!_mounted && {_o distance2D _patient>2}) then {
                private _pose=[_patient,"vent"] call ACME_fnc_equipmentPose;
                if (_pose isNotEqualTo []) then {[_o,_pose] call ACME_fnc_equipmentSeat;};
            };
        };
    };
} forEach _devices;
missionNamespace setVariable ["ACME_eqDevices",_devices select {!isNull _x}];

private _boxes=missionNamespace getVariable ["ACME_eqOpenCoolers",[]];
{
    private _box=_x;if (isNull _box) then {continue;};
    private _users=(_box getVariable ["ACME_eqCoolerUsers",[]]) select {!isNull (_x select 0) && {alive (_x select 0)} && {serverTime<(_x select 1)} && {(_x select 0) distance _box<=4.5}};
    _box setVariable ["ACME_eqCoolerUsers",_users];
    private _open=_users isNotEqualTo [];
    if (_open isNotEqualTo (_box getVariable ["ACME_eqCoolerOpen",false])) then {
        _box setVariable ["ACME_eqCoolerOpen",_open,true];
        [_box,["ACME_BloodFridgeDoorClose","ACME_BloodFridgeDoorOpen"] select _open,30] call ACME_fnc_worldSfxNearby;
    };
} forEach _boxes;
missionNamespace setVariable ["ACME_eqOpenCoolers",_boxes select {!isNull _x && {(_x getVariable ["ACME_eqCoolerUsers",[]]) isNotEqualTo []}}];
