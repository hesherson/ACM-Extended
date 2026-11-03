params ["_target"];
private _sensors=_target getVariable ["acme_tempus_sensors",[true,false,false,false,false]];
private _names=["ECG leads","SpO2 sensor","NIBP cuff","Capnography line","Temperature probe"];
private _actions=[];
{
    private _index=_forEachIndex;
    private _label=format ["%1 %2",["Attach","Remove"] select (_sensors select _index),_x];
    private _a=[format ["ACME_TempusSensor_%1",_index],_label,"",{
        params ["_target","_player","_index"];
        private _sensors=+(_target getVariable ["acme_tempus_sensors",[true,false,false,false,false]]);
        _sensors set [_index,!(_sensors select _index)];
        _target setVariable ["acme_tempus_sensors",_sensors,true];
    },{!isNull (_target getVariable ["acme_tempus_pat",objNull])},{},_index] call ace_interact_menu_fnc_createAction;
    _actions pushBack [_a,[],_target];
} forEach _names;
private _bp=["ACME_TempusMeasureBP","Measure NIBP","",{
    params ["_target"];
    _target setVariable ["ACME_eq_nibpRequest",serverTime,true];
},{((_target getVariable ["acme_tempus_sensors",[false,false,false]]) select 2) && {(_target getVariable ["acme_tempus_pw",[false]]) select 0}}] call ace_interact_menu_fnc_createAction;
_actions pushBack [_bp,[],_target];
_actions
