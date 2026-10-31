// ACM wants to move this casualty. get out of the way first, properly.
// call it as [_patient] call ACME_fnc_headElevAnimGuard, from fn_circhandle.
// the existing hook suspends head elevation when a treatment action declares it rolls the patient. that covers
// actions and nothing else: any ACM animation played outside that path, for any reason, lands on top of an
// elevated head and the two systems fight over one body. ours loses silently and the pose sticks.
// this watches the animation itself, so it does not matter how or why ACM decided to move them.
// there are two different answers, because these are two different situations.
// the recovery position cancels the elevation outright. rolling someone onto their side is the airway intervention,
// and propping their head on a plate carrier while they lie on their side is not a position, it is two half-done
// things. it is one or the other.
// everything else suspends. CPR, lying flat and the continuous poses: the medic still wants the head up, they
// simply cannot have it while this is happening. the head goes down with the release animation, the carrier is set
// on the ground superior to the head so nothing clips through it, and it all comes back when the maneuver
// finishes.
// either way our animation goes first. ACM is free to roll and flip afterwards.
params ["_patient"];
if (isNull _patient) exitWith {};
if (!(_patient getVariable ["ACME_headElevated", false])) exitWith {
    _patient setVariable ["ACME_headElev_lastAnim", ""];
};
// With presentation disabled, the patient's ordinary lying animation is expected. Clinical treatment and
// transport events still suspend/cancel the posture through their existing logical leases.
if (!(missionNamespace getVariable ["ACME_interventionAnimations", true])
    || {_patient getVariable ["ACME_headElev_noAnimation", false]}) exitWith {
    _patient setVariable ["ACME_headElev_lastAnim", ""];
};

private _anim = toLower (animationState _patient);
if (_anim isEqualTo (_patient getVariable ["ACME_headElev_lastAnim", ""])) exitWith {};

// B72: do not immediately suspend a just-started elevation merely because ACM_LyingState remains visible for one
// transition frame. That race made the activity log succeed while the casualty never visibly elevated.
private _restAnim = toLower (missionNamespace getVariable ["ACME_headElev_restAnim", "ACM_LyingState"]);
private _graceUntil = _patient getVariable ["ACME_headElev_animGraceUntil", -1];
if (!(_patient getVariable ["ACME_headElev_Suspended", false])
    && {_patient getVariable ["ACME_headElev_visualActive", false]}
    && {CBA_missionTime <= _graceUntil}
    && {_anim == _restAnim}) exitWith {};

_patient setVariable ["ACME_headElev_lastAnim", _anim];
// If a backpack-supported chest-access vest is temporarily out, keep it superior to the head across pose changes.
[_patient] call ACME_fnc_chestAccessVestPark;

// the repositioning set of ACM. it is matched loosely, because these appear with suffixes and variants.
private _cancelOn = missionNamespace getVariable ["ACME_headElev_acmCancelAnims", ["acm_recoveryposition"]];
private _yieldOn  = missionNamespace getVariable ["ACME_headElev_acmYieldAnims",
    ["acm_genericcontinuous", "acm_pronecontinuous", "acm_lyingstate", "acm_cpr", "acm_cpr_stop"]];

if (_cancelOn findIf { _anim find _x >= 0 } >= 0) exitWith {
    // their airway is being managed by the position now, so ours steps aside completely.
    // the stop takes [_medic, _patient]. one argument put the casualty in the medic slot and left the patient
    // null, so the stop exited immediately and this guard never tore anything down.
    [objNull, _patient] call ACME_fnc_headElevateStop;
};

if (_yieldOn findIf { _anim find _x >= 0 } >= 0) then {
    if (!(_patient getVariable ["ACME_headElev_Suspended", false])) then {
        [_patient] call ACME_fnc_headElevSuspend;
    };
};
