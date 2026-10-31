/* Admit by volume; refrigeration retains the server's prior warm exposure. */
if (!hasInterface || {!(missionNamespace getVariable ["ACME_coolerAutoStore",true])} || {missionNamespace getVariable ["ACME_coolerAutoStoreBusy",false]}
    || {diag_tickTime<(missionNamespace getVariable ["ACME_coolerAutoStoreSuppressUntil",0])}) exitWith {};
private _p=ACE_player;
if (isNull _p || {!alive _p} || {!local _p}) exitWith {};
private _loose=((uniformItems _p)+(vestItems _p)+(backpackItems _p)) select {([_x] call ACME_fnc_coolerBagVolume)>0};
private _reserved=(missionNamespace getVariable ["ACME_coolerManualOut",0]) min count _loose;
missionNamespace setVariable ["ACME_coolerManualOut",_reserved];
if (count _loose<=_reserved) exitWith {};
private _choices=_loose select [_reserved];
private _selected=[];
{
    _x params ["_sid","_state"];
    private _used=0;{_used=_used+([_x select 0] call ACME_fnc_coolerBagVolume);} forEach (_state select 2);
    private _room=getNumber(configFile >> "CfgWeapons" >> (_state select 0) >> "ACME_coolerCapacityMl")-_used;
    private _fit=_choices findIf {([_x] call ACME_fnc_coolerBagVolume)<=_room};
    if (_fit>=0) exitWith {_selected=[_sid,_choices select _fit];};
} forEach ([_p] call ACME_fnc_coolerRows);
if (_selected isNotEqualTo []) then {[_p,_selected select 0,_selected select 1] call ACME_fnc_coolerLoadRequest;};
