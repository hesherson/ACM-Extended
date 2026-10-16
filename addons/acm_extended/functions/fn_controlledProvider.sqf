/* Resolve this client's current medical provider through ACE's public player API.
 * ACE_player can still name the curator avatar during a remote-control transition.
 * Do not use that stale global as a fallback or change patient/clinical ownership.
 */
if (!hasInterface) exitWith {objNull};
private _provider = if (!isNil "ace_common_fnc_player") then {
    call ace_common_fnc_player
} else {
    missionNamespace getVariable ["bis_fnc_moduleRemoteControl_unit", player]
};
if (isNull _provider) then {_provider = player;};
_provider
