params ["_target"];
private _actions=[];
{
    _x params ["_key","_label"];
    private _attached=_target getVariable [_key,_key=="acme_tempusls_pads"];
    private _action=["ACME_LS_"+_key,format ["%1 %2",["Attach","Remove"] select _attached,_label],"",{
        params ["_target","","_key"];
        private _attached=_target getVariable [_key,_key=="acme_tempusls_pads"];
        _target setVariable [_key,!_attached,true];
        if (_key=="acme_tempusls_pads" && {_attached}) then {
            [_target] call ACME_fnc_tempusLsChargeClear;
            _target setVariable ["acme_tempusls_pace",[false,70,0,false],true];
        };
    },{!isNull (_target getVariable ["acme_tempusls_pat",objNull])},{},_key] call ace_interact_menu_fnc_createAction;
    _actions pushBack [_action,[],_target];
} forEach [["acme_tempusls_pads","defibrillator pads"],["acme_tempusls_ecg","ECG monitoring leads"]];
_actions
