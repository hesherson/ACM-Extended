/* B213: persist real empty-hands selection before showing the decorative pressure hold.
 * Disabling weapons in a move does not holster the selected weapon. Without this preflight the engine redraws
 * that weapon every time movement releases the hold. Never remember or restore the previous weapon.
 */
params ["_medic", "_patient"];
if (isNull _medic || {!local _medic} || {_medic getVariable ["ACE_isUnconscious", false]} || {!([_medic] call ace_common_fnc_isAwake)} || {!(_medic getVariable ["ACME_DP_Active", false])}
    || {[_medic] call ACME_fnc_animBlocked} || {[_medic, _patient] call ACME_fnc_directPressurePoseBusy}) exitWith {false};
private _exit = _medic getVariable ["ACME_DP_Exit", []];
if (_exit isNotEqualTo [] && {(_exit param [2, -1]) != (_medic getVariable ["ACME_providerLocalityEpoch", 0])
    || {(CBA_missionTime - (_exit param [4, -99])) > ((_exit param [6, 0]) + 2)}}) then {
    _medic setVariable ["ACME_DP_Exit", [], false];
    _exit = [];
};
if (_exit isNotEqualTo []) exitWith {false};
private _now = CBA_missionTime;
private _prep = _medic getVariable ["ACME_DP_PosePrep", []];
if (_prep isEqualTo []) then {
    // Retire any old accelerated medical exit before holstering as well as before the hold.
    [_medic, "", -1, true] call ACME_fnc_treatmentPoseStop;
    if !([_medic] call ACME_fnc_providerAnimSpeedOwned) then {_medic setAnimSpeedCoef 1;};
    private _delay = [_medic] call ACME_fnc_medicAnimationPrep;
    _prep = [_now + (_delay max 0), _now];
    _medic setVariable ["ACME_DP_PosePrep", _prep, false];
};
if (_now < (_prep select 0)) exitWith {false};
private _visible = toLowerANSI animationState _medic;
private _empty = ((_visible find "wnon") >= 0 && {(_visible find "snon") >= 0})
    || {_visible in ["acme_directpressurehold", "acm_pronecontinuous", "acme_chestsealworkspace", "acme_stethoscopework", "acm_genericcontinuous"]};
if (currentWeapon _medic != "" || {!_empty}) exitWith {
    // If holstering was interrupted, allow one fresh bounded attempt after the shared one-shot reservation expires.
    if ((_now - (_prep select 1)) >= 3.2) then {_medic setVariable ["ACME_DP_PosePrep", [], false];};
    false
};
private _pose = [_medic, "ACME_DirectPressureHold"] call ACME_fnc_providerAnimation;
private _prone = _pose == "ACM_ProneContinuous";
_medic setVariable ["ACME_DP_Pose", _pose, false];
_medic setVariable ["ACME_DP_PoseProne", _prone, false];
_medic setVariable ["ACME_DP_PosePrep", [], false];
_medic setUnitPos (["MIDDLE", "DOWN"] select _prone);
[_medic, _pose, 1.1, 1, true] call ACME_fnc_doAnimHeld;
_medic setVariable ["ACME_DP_HeldGeneration", _medic getVariable ["ACME_dah_gen", -1], false];
_medic setVariable ["ACME_DP_InPose", true, false];
_medic setVariable ["ACME_DP_LastPoseAssert", _now, false];
true
