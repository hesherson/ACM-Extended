/*
 * SKED action: can the strapped casualty go into a vehicle within 10 m with a free seat? Only living
 * casualties go into seats.
 * Arguments: 0: player, 1: SKED. Returns: bool.
 */
params ["_player", "_litter"];
private _patient = _litter getVariable ["acme_sked_patient", objNull];
!isNull _patient
&& {alive _patient}
&& {[_player, _litter] call acme_sked_fnc_canUnstrapLitter}
&& {([_patient, 10] call ace_common_fnc_nearestVehiclesFreeSeat) isNotEqualTo []
    // or a vehicle that takes the litter itself on its cabin floor
    || {([_litter] call acme_sked_fnc_vehicleLitterNear) isNotEqualTo []}}
