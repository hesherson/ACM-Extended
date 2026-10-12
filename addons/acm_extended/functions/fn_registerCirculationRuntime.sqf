/*
 * Phase 23 runtime ownership: circulation, saline-acidosis and automatic-BP ticks.
 *
 * Registration is idempotent.  Dev reloads/postInit replay must never leave two PFHs
 * integrating the same physiology in parallel; that presents exactly like a vital
 * "doubling" every tick.
 */
private _registrations = [
    ["ACME_PFH_salineAcidosisTrack", {call ACME_fnc_salineAcidosisTrack}, 0.25],
    ["ACME_PFH_flightTick", {call ACME_fnc_flightTick}, 0.25],
    ["ACME_PFH_circHandle", {call ACME_fnc_circHandle}, 0.25],
    ["ACME_PFH_autoBPTick", {call ACME_fnc_autoBPTick}, 1]
];

{
    _x params ["_key", "_code", "_interval"];
    private _old = missionNamespace getVariable [_key, -1];
    if (_old isEqualType 0 && {_old >= 0}) then {
        [_old] call CBA_fnc_removePerFrameHandler;
    };
    private _id = [_code, _interval, []] call CBA_fnc_addPerFrameHandler;
    missionNamespace setVariable [_key, _id];
} forEach _registrations;
