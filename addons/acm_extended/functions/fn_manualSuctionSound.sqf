/* B226: finite manual-bulb squeeze sound, isolated from the casualty's speech/breath sound slot.
 * The ACCUVAC motor/trigger path is deliberately unchanged. No loop or global frame worker. */
params [["_medic", objNull, [objNull]], ["_receive", false, [false]]];
if (isNull _medic) exitWith {};
if (!_receive) exitWith {
    private _listeners = allPlayers select {alive _x && {(_x distance _medic) <= 25}};
    // Explicit local listener covers SP and remote-controlled AI providers too.
    if (hasInterface && {!isNil "ACE_player"} && {!isNull ACE_player} && {(ACE_player distance _medic) <= 25}) then {
        _listeners pushBackUnique ACE_player;
    };
    if (_listeners isNotEqualTo []) then {["ACME_manualSuctionSound", [_medic, true], _listeners] call CBA_fnc_targetEvent;};
};
if (!hasInterface || {isNil "ACE_player"} || {isNull ACE_player} || {(ACE_player distance _medic) > 25}) exitWith {};
private _emitter = "#dynamicsound" createVehicleLocal (getPosATL _medic);
_emitter attachTo [_medic, [0, 0.25, 0.9]];
private _sound = _emitter say3D ["ACME_ManualSuction", 25, 1, 2];
[{
    params ["_emitter", "_sound"];
    if (!isNull _sound) then {deleteVehicle _sound;};
    if (!isNull _emitter) then {detach _emitter; deleteVehicle _emitter;};
}, [_emitter, _sound], 1.2] call CBA_fnc_waitAndExecute;
