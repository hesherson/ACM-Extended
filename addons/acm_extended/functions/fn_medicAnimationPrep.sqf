/* v1.1.0 provider-animation weapon preflight.
 * Select empty hands at most once for an animation episode and return the short settle delay the caller should
 * respect before starting its authored RTM. A second ACME owner arriving while that first holster is still
 * entering must wait on it, never issue another put-away animation. Weapons are never automatically restored.
 */
params [["_medic", objNull, [objNull]]];
if (isNull _medic || {!local _medic} || {!alive _medic} || {[_medic] call ACME_fnc_animBlocked}) exitWith {0};

// Empty hands are not ready until BOTH Arma's logical weapon selection and the visible animation agree.
// This matters most for sidearms: selectWeapon "" can clear currentWeapon before the pistol model/hand pose has
// actually finished holstering, which lets a medical RTM play underneath a still-visible handgun.
private _rate = (getAnimSpeedCoef _medic) max 1;
private _state = toLowerANSI animationState _medic;
private _ownedEmptyState = _state in [
    "acme_chestsealworkspace",
    "acme_stethoscopework",
    "acme_directpressurehold",
    "acm_genericcontinuous",
    "acm_pronecontinuous"
];
private _visuallyEmpty = (((_state find "wnon") >= 0) && {((_state find "snon") >= 0)}) || {_ownedEmptyState};
private _weapon = currentWeapon _medic;
if (_weapon == "" && {_visuallyEmpty}) exitWith {
    _medic setVariable ["ACME_medicAnimationPrep", ["empty_hands_ready", CBA_missionTime, ""], false];
    0
};

// One engine holster request per treatment handoff. Never repair a visual/logical mismatch with selectWeapon "";
// that shortcut is what left pistols visibly attached to the hands while the underlying medical animation ran.
// Keep the one-shot reservation longer than the treatment preflight timeout so another controller cannot enqueue
// a second launcher/rifle/pistol put-away chain while the first request is still settling.
private _previous = _medic getVariable ["ACME_medicAnimationPrep", []];
private _elapsed = if (_previous isEqualType [] && {count _previous >= 2}
    && {(_previous param [0, ""]) == "empty_hands_once"}) then {
    CBA_missionTime - (_previous param [1, -99])
} else {-1};
// Return from this function, not an inner block, while the original holster is pending.
if (_elapsed >= 0 && {_elapsed < 3.2}) exitWith {
    private _requested = _previous param [2, ""];
    private _minSettle = if (_requested != "" && {_requested == handgunWeapon _medic}) then {0.95} else {0.70};
    ((_minSettle / _rate) - _elapsed) max 0.05
};

// If the logical weapon is already clear but the holster animation is still finishing, just wait for the visible
// Wnon/Snon state. Issuing another SwitchWeapon here creates the multi-weapon stow carousel seen on treatment exit.
if (_weapon == "") exitWith {0.05};

if (!isNil "ace_weaponselect_fnc_putWeaponAway") then {
    [_medic] call ace_weaponselect_fnc_putWeaponAway;
} else {
    _medic action ["SwitchWeapon", _medic, _medic, 299];
};
_medic setVariable ["ACME_medicAnimationPrep", ["empty_hands_once", CBA_missionTime, _weapon], false];

// Sidearm holsters need a little more minimum settle time than long-gun Wnon transitions. The caller still waits
// for the actual logical+visual empty-hands state, so these are minimum delays rather than guessed completion times.
(if (_weapon == handgunWeapon _medic) then {0.95} else {0.70}) / _rate
