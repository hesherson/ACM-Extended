params ["_target","_player"];
private _rows=[_player] call ACME_fnc_coolerRows;
private _ordinal=0;
_rows apply {
    _ordinal=_ordinal+1;
    _x params ["_sid","_state"];
    private _name=getText(configFile >> "CfgWeapons" >> (_state select 0) >> "displayName");
    private _action=["ACME_SetDownCooler_"+_sid,format ["Set Down %1 (#%2)",_name,_ordinal],"",{
        params ["","_player","_data"];_data params ["_sid","_patient"];["deploy",_player,_sid,objNull,[],_patient] call ACME_fnc_coolerBoxRequest;
    },{true},{},[_sid,[objNull,_target] select (_target isNotEqualTo _player)]] call ace_interact_menu_fnc_createAction;
    [_action,[],_target]
}
