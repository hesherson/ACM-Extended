params ["_target"];
private _actions = [];
{
    _x params ["_key","_label","_index"];
    private _attach = !(_target getVariable [_key,_index==5]);
    private _action = ["ACME_LS_"+_key,format ["%1 %2",["Remove","Attach"] select _attach,_label],"",{
        params ["_target","_player","_operation"];
        [_player,_target getVariable ["acme_tempusls_pat",objNull],"ls",_operation,true,_target] call ACME_fnc_equipmentMonitorAction;
    },{
        params ["_target","_player","_operation"];
        [_player,_target getVariable ["acme_tempusls_pat",objNull],"ls",_operation,false,_target] call ACME_fnc_equipmentMonitorAction
    },{},[_index,_attach]] call ace_interact_menu_fnc_createAction;
    _actions pushBack [_action,[],_target];
} forEach [["acme_tempusls_pads","defibrillator pads",5],["acme_tempusls_ecg","ECG monitoring leads",0]];
_actions
