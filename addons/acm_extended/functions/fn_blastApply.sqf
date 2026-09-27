// turn one blast dose into consequences. it is called by the Explosion handler, straight after fn_blastsolve.
// call it as [_unit, _res] call ACME_fnc_blastApply, where _res is the hashmap fn_blastsolve returned.
//
// nothing here invents a new injury. every consequence routes into a system that already exists, because the
// medic already knows how to treat those and the aar already reports them. what this adds is that they all now
// come off one number instead of separate rolls.
//
// the thresholds are the published ones, in effective kPa at the body.
//   35   the eardrum rupture threshold. ringing and a threshold shift start here.
//   100  50 percent eardrum rupture. hearing is properly gone for a while.
//   200  the lung injury threshold. blast lung starts, and this is the number that matters most.
//   550  roughly 50 percent lethality from pressure alone.
// a casualty at 60 kPa is deafened, rattled and entirely treatable. one at 250 has a lung injury they may not
// show for twenty minutes. that gap is the whole point of modeling pressure rather than damage.
params ["_unit", ["_res", createHashMap]];
if (isNull _unit) exitWith {};
if !(alive _unit) exitWith {};

private _pr    = _res getOrDefault ["prKpa", 0];
private _dose  = _res getOrDefault ["dose", 0];
private _cum   = _unit getVariable ["ACME_blast_cumulative", 0];
if (_pr <= 0) exitWith {};

// 1. hearing.
// this is the most common blast injury by a wide margin and the one most often waved away. it is handed to ACE's
// own hearing system where that is loaded, so it stacks with every other loud thing in the mission and the player
// gets the deafness they already understand, rather than a second parallel system that fights it.
// note that ear protection reduces this and only this. the standing rule for the rest of the file is that
// hearing protection does nothing whatsoever for brain, lung or whole-body injury: it covers the ears and the
// pressure wave does not care about the ears.
private _earThresh = missionNamespace getVariable ["ACME_blast_earKpa", 35];
if (_pr >= _earThresh) then {
    private _deaf = linearConversion [_earThresh, 200, _pr, 0.1, 1, true];
    if (!isNil "ace_hearing_fnc_earRinging") then {
        [_unit, _deaf * 20] call ace_hearing_fnc_earRinging;
    } else {
        // no ACE hearing on this build, so keep our own record. it is still exposure history and the medical
        // menu can still report it.
        _unit setVariable ["ACME_blast_deaf", ((_unit getVariable ["ACME_blast_deaf", 0]) max _deaf), true];
    };
    // tympanic injury is recorded because it is a finding a medic can examine for. it is deliberately NOT used as
    // a gate on anything below. an intact eardrum does not rule out a lung or brain injury, and treating it as a
    // triage sieve is a known way to miss the casualty who dies four hours later.
    if (_pr >= 100) then { _unit setVariable ["ACME_blast_tympanic", true, true]; };
};

// 2. balance and disorientation.
// it is short, it is not damage, and it is what makes a blast feel like a blast without taking the screen away
// from the player. the visual instability goes through the existing shake, so it reads like the world moving
// rather than like the camera being broken.
if (_dose > 0.05) then {
    private _stun = linearConversion [0.05, 0.6, _dose, 0.3, 1, true];
    _unit setVariable ["ACME_blast_stun", _stun, true];
    _unit setVariable ["ACME_blast_stunUntil", CBA_missionTime + (2 + (_stun * 12)), true];
    // the camera, not the ui. fn_uishakeapply moves the controls inside a minigame dialog and has nothing to do
    // with the world view, so the engine shake is the right primitive here. it is deliberately short and it does
    // not blur: visual instability reads as the world moving, and taking the screen away from the player is the
    // thing that makes concussion effects hated.
    if (local _unit && {_unit isEqualTo ACE_player}) then {
        addCamShake [(_stun * 8) min 10, (1 + (_stun * 4)), 12];
    };
};

// 3. falling and stance.
// past a point the legs simply go. this is the blast knocking someone over rather than an injury, so it is a
// posture change and nothing is recorded against the casualty for it.
if (_dose > (missionNamespace getVariable ["ACME_blast_knockdownDose", 0.18]) && {local _unit}) then {
    if (isNull objectParent _unit && {stance _unit != "PRONE"}) then {
        private _epoch = [_unit] call ACME_fnc_clinicalEpoch;
        private _serial = (_unit getVariable ["ACME_blast_stanceSerial", 0]) + 1;
        private _token = [_epoch, clientOwner, _serial];
        _unit setVariable ["ACME_blast_stanceSerial", _serial, false];
        _unit setVariable ["ACME_blast_stanceToken", _token, true];
        if !([_unit] call ACME_fnc_animBlocked) then { _unit playActionNow "AdvL"; };
        _unit setUnitPos "DOWN";
        [{
            params ["_u", "_epoch", "_token"];
            if (isNull _u || {!local _u} || {!alive _u}) exitWith {};
            if (([_u] call ACME_fnc_clinicalEpoch) != _epoch) exitWith {};
            if !((_u getVariable ["ACME_blast_stanceToken", []]) isEqualTo _token) exitWith {};
            // Only this fall may release its stance; a heal or a newer fall retires the old callback.
            _u setVariable ["ACME_blast_stanceToken", [], true];
            _u setUnitPos "AUTO";
        }, [_unit, _epoch, _token], 3] call CBA_fnc_waitAndExecute;
    };
};

// 4. the brain.
// this is the existing TBI, entered with a severity from the dose rather than from a damage roll. a blast TBI is
// the signature injury of the last twenty years of conflict and it is the reason the cumulative total matters:
// three small exposures do more than one of the same total size, because the brain does not get to start again.
private _tbiDose = missionNamespace getVariable ["ACME_blast_tbiDose", 0.10];
if (_dose >= _tbiDose) then {
    private _sev = linearConversion [_tbiDose, 1.0, _dose, 0.15, 0.85, true];
    // the accumulated history makes each one worse. the second blast of the day starts from where the first left
    // the casualty rather than from healthy.
    _sev = (_sev * (1 + ((_cum - _dose) max 0) * (missionNamespace getVariable ["ACME_blast_cumulativeTbiMul", 0.35]))) min 1;
    if (local _unit) then { [_unit, _sev] call ACME_fnc_tbiBlast; };
};

// 5. the lungs.
// blast lung is the one that makes a ventilator genuinely necessary, and it is the classic delayed presentation:
// the casualty walks away from the blast and deteriorates over the next half hour. so it is seeded here at a
// severity from the dose and fn_blastlunginflict runs it from there.
private _lungKpa = missionNamespace getVariable ["ACME_blast_lungKpa", 200];
if (_pr >= _lungKpa) then {
    private _sev = linearConversion [_lungKpa, 700, _pr, 0.2, 1, true];
    if (local _unit) then { [_unit, _sev] call ACME_fnc_blastLungInflict; };
};

// 6. unconsciousness.
// at the top of the range the casualty is simply out. it goes through the normal ACE state rather than a bespoke
// one, so waking, the consciousness budget and every existing check behave exactly as they do for any other cause.
if (_dose >= (missionNamespace getVariable ["ACME_blast_koDose", 0.45]) && {local _unit}) then {
    if (!(_unit getVariable ["ACE_isUnconscious", false])) then {
        // Use ACE's public setter so the medical state machine and ACE_isUnconscious stay synchronized.
        [_unit, true, (10 + (_dose * 40)), false] call ace_medical_fnc_setUnconscious;
    };
};

// 7. pain.
// a real blast hurts, whether or not it broke anything. it is added rather than set, so it stacks with the wounds
// the fragments caused.
if (_dose > 0.08) then {
    private _p = linearConversion [0.08, 1, _dose, 0.05, 0.6, true];
    if (local _unit) then {
        [_unit, [["pain", (((_unit getVariable ["ace_medical_pain", 0]) + _p) min 1), true]]] call ACM_core_fnc_setAceMedicalState;
    };
};

// the log line is the medic's record that this casualty was in a blast at all, which is the thing most often lost
// between the point of injury and the hospital. it carries the pressure rather than a severity word, because a
// number is what lets a receiving clinician decide what to look for.
if (_pr >= _earThresh) then {
    [_unit, "activity", "Blast exposure: %1 kPa%2", [round _pr, (if ((_res getOrDefault ["encl", 1]) > 1.5) then {" (enclosed)"} else {""})]] call ace_medical_treatment_fnc_addToLog;
};
