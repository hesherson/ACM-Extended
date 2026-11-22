/*
 * Where the casualty is local: a living casualty who is wrapped in the HPMK is held in the one pose the shell is
 * made for: arms along the body, legs together. Lying free, on a litter, dragged, with his head raised, treated:
 * always that pose, as any other pulls the shell out of shape ("prevent all animations for making the bag stretch
 * and deform. we must force the patient to be in the single wrapped animation", 2026-11-20). He is put back into
 * it the moment anything changes his animation (a handler on him, here), and this is looked at again with every
 * check of what he wears. Left alone: one in a vehicle seat, and one who is awake and not lying (he is getting
 * up: the shell slips off him, ACME_fnc_hpmkBlanketTick). When the shell is off, he gets back the lying pose he
 * would have without it.
 *
 * A dead casualty who is wrapped is laid straight in the same pose, as the hands that wrap a body would lay it:
 * the shell is made for that pose, and over a body lying as it fell it was pulled out to the limbs, with the legs
 * out at its foot end. A body takes the pose from switchMove, which ends the sprawl it fell in, free or hung on
 * something; whoever dies in the pose stays in it (both measured in game, 2026-11-20). Once laid straight a body
 * stays so, with the shell on or off. On a litter it is then placed anew, as its place there was worked out
 * from how it lay before.
 * Arguments: 0: casualty. Returns: nothing.
 */
params [["_patient", objNull, [objNull]]];
if (isNull _patient || {!local _patient}) exitWith {};
private _pose = "acme_litter_side";
if !(isClass (configFile >> "CfgMovesMaleSdr" >> "States" >> _pose)) exitWith {};
if (!alive _patient) exitWith {
    if !((_patient getVariable ["ACME_hpmk_state", ""]) in ["wrapped", "exposed"]) exitWith {};
    if (!isNull objectParent _patient || {(toLowerANSI animationState _patient) == _pose}) exitWith {};
    ["ace_common_switchMove", [_patient, "ACME_Litter_Side"]] call CBA_fnc_globalEvent;
    private _litter = _patient getVariable ["acme_sked_litter", objNull];
    if (!isNull _litter && {!isNil "acme_sked_fnc_align"}) then {
        [{
            params ["_patient", "_litter"];
            if (local _patient && {!isNull _litter} && {isNull objectParent _patient}
                && {!(_patient getVariable ["acme_sked_loading", false])}
                && {(_patient getVariable ["acme_sked_litter", objNull]) isEqualTo _litter}) then {
                [_patient, _litter, false] call acme_sked_fnc_align;
            };
        }, [_patient, _litter], 0.5] call CBA_fnc_waitAndExecute;
    };
};
private _now = toLowerANSI animationState _patient;
if ((_patient getVariable ["ACME_hpmk_state", ""]) in ["wrapped", "exposed"]) exitWith {
    if ((_patient getVariable ["ACME_hpmk_poseLock", -1]) < 0) then {
        _patient setVariable ["ACME_hpmk_poseLock", _patient addEventHandler ["AnimStateChanged", {
            params ["_unit", "_anim"];
            if ((toLowerANSI _anim) != "acme_litter_side" && {local _unit}) then {
                [ACME_fnc_hpmkPose, [_unit]] call CBA_fnc_execNextFrame;
            };
        }]];
    };
    if (_now == _pose || {!isNull objectParent _patient}) exitWith {};
    private _lying = _patient getVariable ["ACM_core_Lying_State", false];
    if !(_lying isEqualType true) then {_lying = _lying > 0;};
    if (!(_patient getVariable ["ACE_isUnconscious", false]) && {!_lying}) exitWith {};
    // (at most four times a second, whatever sets another pose and however often: each time is one message to
    // every machine. What comes sooner is looked at once more when that time is over.)
    private _wait = (_patient getVariable ["ACME_hpmk_poseAt", -1]) + 0.25 - diag_tickTime;
    if (_wait > 0) exitWith {
        if !(_patient getVariable ["ACME_hpmk_poseAgain", false]) then {
            _patient setVariable ["ACME_hpmk_poseAgain", true];
            [{
                _this setVariable ["ACME_hpmk_poseAgain", false];
                [_this] call ACME_fnc_hpmkPose;
            }, _patient, _wait + 0.02] call CBA_fnc_waitAndExecute;
        };
    };
    _patient setVariable ["ACME_hpmk_poseAt", diag_tickTime];
    [_patient, _pose, 2, true] call ace_common_fnc_doAnimation;
    ACME_hpmk_poseForced = (missionNamespace getVariable ["ACME_hpmk_poseForced", 0]) + 1;      // for the tests
};
private _lock = _patient getVariable ["ACME_hpmk_poseLock", -1];
if (_lock >= 0) then {
    _patient removeEventHandler ["AnimStateChanged", _lock];
    _patient setVariable ["ACME_hpmk_poseLock", nil];
};
if (!isNull objectParent _patient || {!isNull attachedTo _patient}) exitWith {};
if (!isNull (_patient getVariable ["acme_sked_litter", objNull]) || {!isNull (_patient getVariable ["acme_sked_placing", objNull])}) exitWith {};
if (_patient getVariable ["ACME_headElevated", false]) exitWith {};
if (_now != _pose) exitWith {};
private _lying = _patient getVariable ["ACM_core_Lying_State", false];
if !(_lying isEqualType true) then {_lying = _lying > 0;};
private _back = if (_patient getVariable ["ACE_isUnconscious", false]) then {"unconscious"} else {
    ["ainjppnemstpsnonwrfldnon", "ACM_LyingState"] select _lying
};
[_patient, _back, 2, true] call ace_common_fnc_doAnimation;
