/*
 * SKED action: package the nearest casualty in this SKED.
 * Arguments: 0: player, 1: SKED.
 */
params ["_player", "_litter"];
private _patient = [_litter, _player] call acme_sked_fnc_findCasualty;
if (isNull _patient) exitWith {};
[15, [_player, _patient, _litter], {
    (_this select 0) params ["_player", "_patient", "_litter"];
    [_player, "strap", _patient, _litter] call acme_sked_fnc_request;
}, {}, "Packaging casualty in litter...", {
    (_this select 0) params ["_player", "_patient", "_litter"];
    !isNull _litter && {[_patient] call acme_sked_fnc_validCasualty} && {_patient distance _litter < 3.5}
}] call ace_common_fnc_progressBar;
