params ["_target"];
private _sensors = _target getVariable ["acme_tempus_sensors",[true,false,false,false,false]];
private _actions = [];
{
    private _index = _forEachIndex;
    private _attach = !(_sensors select _index);
    private _label = format ["%1 %2",["Remove","Attach"] select _attach,_x];
    private _action = [format ["ACME_TempusSensor_%1",_index],_label,"",{
        params ["_target","_player","_operation"];
        [_player,_target getVariable ["acme_tempus_pat",objNull],"pro",_operation,true,_target] call ACME_fnc_equipmentMonitorAction;
    },{
        params ["_target","_player","_operation"];
        [_player,_target getVariable ["acme_tempus_pat",objNull],"pro",_operation,false,_target] call ACME_fnc_equipmentMonitorAction
    },{},[_index,_attach]] call ace_interact_menu_fnc_createAction;
    _actions pushBack [_action,[],_target];
} forEach ["ECG leads","SpO2 sensor","NIBP cuff","EtCO2 line","Temperature probe"];
private _bp = ["ACME_TempusMeasureBP","Measure NIBP","",{
    [_player,_target getVariable ["acme_tempus_pat",objNull],"pro","nibp",true,_target] call ACME_fnc_equipmentMonitorAction;
},{
    [_player,_target getVariable ["acme_tempus_pat",objNull],"pro","nibp",false,_target] call ACME_fnc_equipmentMonitorAction
}] call ace_interact_menu_fnc_createAction;
_actions pushBack [_bp,[],_target];
_actions
