/* Equipment metadata follows CBA extended loadouts. Raw native loadouts cannot carry virtual contents. */
if (missionNamespace getVariable ["ACME_coolerPersistenceInstalled",false]) exitWith {};
missionNamespace setVariable ["ACME_coolerPersistenceInstalled",true];
["CBA_loadoutGet",{
    params ["_unit","","_extendedInfo"];
    _extendedInfo set ["ACME_coolers_v1",[_unit,"holder"] call ACME_fnc_coolerSnapshot];
}] call CBA_fnc_addEventHandler;
["CBA_loadoutSet",{
    params ["_unit","","_extendedInfo"];
    if !("ACME_coolers_v1" in _extendedInfo) exitWith {};
    private _snapshot = _extendedInfo get "ACME_coolers_v1";
    private _ok = [_unit,_snapshot,0] call ACME_fnc_coolerRestore;
    _unit setVariable ["ACME_coolerLastRestoreOK",_ok,false];
}] call CBA_fnc_addEventHandler;
