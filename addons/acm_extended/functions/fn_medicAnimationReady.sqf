/* Read-only empty-hands readiness. A cleared logical selection can precede the visible handgun holster.
 * Callers own one stow request, a minimum settle delay and a bounded wait for this predicate.
 */
params [["_medic", objNull, [objNull]]];
if (isNull _medic || {!local _medic} || {!alive _medic}
    || {_medic getVariable ["ACE_isUnconscious", false]}
    || {[_medic] call ACME_fnc_animBlocked}) exitWith {false};
if (currentWeapon _medic != "") exitWith {false};
private _state = toLowerANSI animationState _medic;
if (_state in ["acme_chestsealworkspace", "acme_stethoscopework", "acme_directpressurehold",
    "acm_genericcontinuous", "acme_junctionalwork", "acm_pronecontinuous"]) exitWith {true};
// Holster transition names can contain BOTH the armed source and unarmed target states. The target's Wnon
// substring alone is not evidence that the visible weapon has gone. Exclude every armed family first.
if ((["wpst", "wrfl", "wlnr", "wbin"] findIf {(_state find _x) >= 0}) >= 0) exitWith {false};
((_state find "wnon") >= 0) && {(_state find "snon") >= 0}
