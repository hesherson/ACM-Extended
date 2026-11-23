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
// B393: wrapped in the HPMK, his pose is the shell's (fn_hpmkPose.sqf); the raised head is kept without animation
// until he is unwrapped. Never suspend or resume on the wrap pose: that was a loop of lower, re-pose, lift.
if ((_patient getVariable ["ACME_hpmk_state", ""]) in ["wrapped", "exposed"]
    && {!(_patient getVariable ["ACME_headElev_noAnimation", false])}) then {
    _patient setVariable ["ACME_headElev_noAnimation", true, true];
};
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
    ["acm_genericcontinuous", "acm_pronecontinuous", "acm_lyingstate", "acme_litter_side", "acm_cpr", "acm_cpr_stop", "acme_cpr", "acme_cpr_l", "acme_cpr_in", "acme_cpr_in_l", "acme_cpr_hold", "acme_cpr_out"]];

if (_cancelOn findIf { _anim find _x >= 0 } >= 0) exitWith {
    // their airway is being managed by the position now, so ours steps aside completely.
    // the stop takes [_medic, _patient]. one argument put the casualty in the medic slot and left the patient
    // null, so the stop exited immediately and this guard never tore anything down.
    [objNull, _patient] call ACME_fnc_headElevateStop;
};

if (_yieldOn findIf { _anim find _x >= 0 } >= 0) then {
    if (!(_patient getVariable ["ACME_headElev_Suspended", false])) then {
        [_patient] call ACME_fnc_headElevSuspend;
        // B393: a lowering no treatment holds a lease for (seen in game: Check Breathing on a sitting casualty laid
        // him flat and he stayed flat for good) is temporary. Once nothing has held his body for 4 s (no treatment
        // lease, no animation lease, no CPR), he sits up again; at most three times a minute, so it can never loop.
        private _token = _patient getVariable ["ACME_headElev_poseToken", ""];
        private _free = {
            params ["_p", "_token"];
            !isNull _p && {local _p} && {alive _p}
            && {_p getVariable ["ACME_headElevated", false]} && {_p getVariable ["ACME_headElev_Suspended", false]}
            && {(_p getVariable ["ACME_headElev_poseToken", ""]) == _token}
            && {(count (_p getVariable ["ACME_headElev_treatments", createHashMap])) == 0}
            && {!([_p] call ACME_fnc_patientAnimHeld)}
            && {isNull (_p getVariable ["ACM_circulation_CPR_Medic", objNull])}
            && {!(_p getVariable ["ACM_airway_RecoveryPosition_State", false])}
            && {isNull attachedTo _p} && {isNull objectParent _p}
        };
        [{
            params ["_p", "_token", "_since", "_free"];
            if !([_p, _token] call _free) then {_this set [2, CBA_missionTime];};
            !([_p, _token] call _free) && {isNull _p || {!(_p getVariable ["ACME_headElevated", false])} || {!(_p getVariable ["ACME_headElev_Suspended", false])}}
            || {CBA_missionTime > _since + 4}
        }, {
            params ["_p", "_token", "_since", "_free"];
            if !([_p, _token] call _free) exitWith {};
            private _recent = (_p getVariable ["ACME_headElev_autoResumes", []]) select {_x > CBA_missionTime - 60};
            if (count _recent >= 3) exitWith {};
            _recent pushBack CBA_missionTime;
            _p setVariable ["ACME_headElev_autoResumes", _recent];
            _p setVariable ["ACME_headElev_ResumePending", true, true];
            [_p, _token] call ACME_fnc_headElevTryResume;
        }, [_patient, _token, CBA_missionTime, _free], 120] call CBA_fnc_waitUntilAndExecute;
    };
};
