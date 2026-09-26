/*
 * Resolve the CAManBase currently controlled by this client.
 *
 * ACE's public player resolver follows BI curator remote control through
 * bis_fnc_moduleRemoteControl_unit. Raw ACE_player can lag that transition,
 * which makes medical-menu actions evaluate inventory, distance and treatment
 * eligibility against the curator's original avatar instead of the NPC medic.
 *
 * This function is presentation/provider identity only. It does not change
 * locality or clinical ownership.
 */
if (!hasInterface) exitWith {objNull};

private _provider = objNull;
if (!isNil "ace_common_fnc_player") then {
    _provider = call ace_common_fnc_player;
};

if (isNull _provider && {!isNil "ACE_player"}) then {
    _provider = ACE_player;
};
if (isNull _provider) then {
    _provider = player;
};

_provider
