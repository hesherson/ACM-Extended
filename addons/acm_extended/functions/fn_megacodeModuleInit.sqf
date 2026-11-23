/* Module entry point for Eden/Zeus Megacode Kelly placement. */
params [["_logic",objNull,[objNull]], ["_synced",[],[[]]], ["_activated",true,[true]]];
if (isNull _logic || {!_activated}) exitWith {};
if (!isServer) exitWith {};
private _pos=getPosATL _logic;
private _dir=getDir _logic;
[{
    params ["_args","_pfh"];
    _args params ["_logic","_pos","_dir"];
    if (isNull _logic) exitWith {[_pfh] call CBA_fnc_removePerFrameHandler;};
    if (time<=0 || {isNil "CBA_missionTime"} || {isNil "ACME_fnc_megacodeSpawn"}) exitWith {};
    [_pfh] call CBA_fnc_removePerFrameHandler;
    private _d=[_pos,_dir] call ACME_fnc_megacodeSpawn;
    if (isNull _d) then {diag_log format ["[ACME][Megacode] Spawn failed at %1",_pos];} else {if (call ACME_fnc_debugEnabled) then {diag_log format ["[ACME][Megacode] Spawned %1 at %2",_d,_pos];};};
    deleteVehicle _logic;
},0.1,[_logic,_pos,_dir]] call CBA_fnc_addPerFrameHandler;
