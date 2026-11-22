/*
 * Where the casualty is local: put them on a laid out litter when the timer of the strap action starts. They get
 * the pose of the litter and are set down on its bed at once; nobody has to move them there by hand. The place
 * is the one fn_align gives, so nothing moves when the occupied litter takes the place of the laid out one at
 * the end of the timer.
 * Arguments: 0: casualty, 1: laid out litter.
 */
params ["_patient", "_litter"];
if (!local _patient || {isNull _litter}) exitWith {};
if ((_patient getVariable ["acme_sked_placing", objNull]) isNotEqualTo _litter) exitWith {};
private _token = (_patient getVariable ["acme_sked_placeToken", 0]) + 1;
_patient setVariable ["acme_sked_placeToken", _token];
// Lower supported Semi-Fowler first, including its existing carrier custody and collision cleanup.
if (_patient getVariable ["ACME_headElevated", false]) then {
    ["ACME_headElev_transportDown", [_patient]] call CBA_fnc_localEvent;
};
if (alive _patient) then {
    [_patient, [_patient, _litter] call acme_sked_fnc_patientPose, 2, true] call ace_common_fnc_doAnimation;
};
// The place is measured once the pose is on the body: a quarter of a second later.
[{
    params ["_patient", "_litter", "_token"];
    if (!local _patient || {isNull _litter} || {!isNull objectParent _patient}
        || {(_patient getVariable ["acme_sked_placeToken", 0]) != _token}
        || {(_patient getVariable ["acme_sked_placing", objNull]) isNotEqualTo _litter}) exitWith {};
    ([_patient, _litter, false, true] call acme_sked_fnc_align) params ["_off", "_dir", "_up"];
    if (!isNull attachedTo _patient) then {detach _patient;};
    _patient attachTo [_litter, _off];
    _patient setVectorDirAndUp [_dir, _up];
    // every machine turns him so itself: the turn of an attached unit does not reliably reach them
    ["acme_sked_laidTurn", [_patient, _litter, _dir, _up]] call CBA_fnc_globalEvent;
    ["placed", _litter, _patient, [_off]] call acme_sked_fnc_traceTransport;
}, [_patient, _litter, _token], 0.25] call CBA_fnc_waitAndExecute;
