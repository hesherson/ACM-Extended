/* A rejected menu or treatment handoff can leave the provider in a looping ACME idle.
 * Called by the owner reconciler for the locally controlled provider. */
params ["_medic"];
private _animation = toLowerANSI animationState _medic;
private _record = _medic getVariable ["ACME_unownedContinuousPose", []];
if (!(_animation in ["acm_genericcontinuous", "acm_pronecontinuous"])
    || {!alive _medic} || {_medic getVariable ["ACE_isUnconscious", false]}
    || {[_medic] call ACME_fnc_animBlocked}
    || {[_medic, true] call ACME_fnc_providerStanceOwned}
    || {[_medic] call ACME_fnc_providerAnimSpeedOwned}
    || {!isNull (uiNamespace getVariable ["ace_common_dlgProgress", displayNull])}
    || {(_medic getVariable ["ACME_assessmentReturn", []]) isNotEqualTo []}) exitWith {
    if (_record isNotEqualTo []) then {_medic setVariable ["ACME_unownedContinuousPose", []];};
    false
};

private _identity = [_animation, _medic getVariable ["ACME_providerLocalityEpoch", 0],
    _medic getVariable ["ACME_menuPoseEpoch", 0], _medic getVariable ["ACME_treatmentPoseEpoch", 0]];
private _now = diag_tickTime;
if ((_record param [0, []]) isNotEqualTo _identity) exitWith {
    // Give the pending frame handoff time to publish its owner or leave the pose.
    _medic setVariable ["ACME_unownedContinuousPose", [_identity, _now, 0]];
    false
};
_record params ["", "_seenAt", "_attempts"];
if (_now - _seenAt < 0.75 || {_attempts >= 2}) exitWith {false};

_medic setVariable ["ACME_unownedContinuousPose", [_identity, _now, _attempts + 1]];
_medic setUnitPos "AUTO";
_medic setAnimSpeedCoef 1;
["ace_common_setAnimSpeedCoef", [_medic, 1]] call CBA_fnc_globalEvent;
private _idle = ["AmovPknlMstpSnonWnonDnon", "AmovPpneMstpSnonWnonDnon"] select (_animation == "acm_pronecontinuous");
// An exact, ownerless loop that survives interpolation qualifies for ACE's forced recovery.
// Call ACE directly so an already-acquired pose can also be released with choreography disabled.
[_medic, _idle, 1 + _attempts] call ace_common_fnc_doAnimation;
if (call ACME_fnc_debugEnabled) then {diag_log format ["[ACME STATE RECONCILE] Recovering unowned provider pose %1, attempt %2", _animation, _attempts + 1];};
true
