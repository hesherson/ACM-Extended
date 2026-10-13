// air that keeps getting in, because somebody kept making holes.
// call it as [_patient] call ACME_fnc_ncdAirLeakTick, from the circulation tick.
//
// why this exists.
// a needle decompression is not a procedure with a cost of nothing. every one of them puts a 14 gauge cannula
// through the chest wall into the pleural space, and every one of them leaves a track behind when the cannula
// kinks, clots or falls out. one or two is the price of doing the job. a chest that has been needled four or five
// times has a wall that leaks.
// so needles stay unlimited, because a medic should never be told they may not decompress a chest. what changes
// is that past bilateral the chest starts taking in air on its own, and it keeps doing it.
//
// how it differs from a real pneumothorax, deliberately.
// a traumatic pneumothorax fills fast and it tensions. this does neither. it accumulates at a fraction of the
// rate and it never tensions on its own, so it will not kill anybody on the ground. what it does is make the
// casualty steadily worse over a long time, which is a soft evacuation requirement rather than an emergency: they
// need a chest drain and somebody who can place one, and they are not getting either in the field.
// that is the honest consequence of a needle. it relieves the pressure and it does not close the hole, and the
// only thing that closes the hole is a tube.
//
// the sound is the tell.
// the breath sounds already in the mod, the ones used after ROSC, are played on a steady rhythm rather than the
// random clustering used elsewhere. a regular, quiet, wrong-sounding breath is what a medic notices when nothing
// on the monitor has changed yet.
params ["_patient"];
if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {};
// Keep the five-second clinical cadence without replaying time spent with a
// patent drain, disabled physiology or a different patient owner. Clock-prefixed
// local bookkeeping is cleared by the existing locality/reset lifecycle.
private _sameOwner = (_patient getVariable ["ACME_clock_ncdLeak_owner", -1]) == clientOwner;
private _elapsed = [_patient, "ncdLeak", 0.25, 5] call ACME_fnc_clinicalTickDelta;
private _pending = if (_sameOwner) then {_patient getVariable ["ACME_clock_ncdLeakPending", 0]} else {0};
if !(missionNamespace getVariable ["ACME_sys_ncdLeak", true]) exitWith {
    _patient setVariable ["ACME_clock_ncdLeakPending", 0, false];
};

// bilateral is free. it is the third needle onward that starts this, because at that point either the diagnosis
// was wrong or the first two did not hold, and both of those mean more holes than the chest can close.
private _n = _patient getVariable ["ACME_ncd_total", 0];
private _free = missionNamespace getVariable ["ACME_ncd_freeCount", 2];
if (_n <= _free) exitWith {
    _patient setVariable ["ACME_clock_ncdLeakPending", 0, false];
};

// a tube fixes it, which is the entire point of the mechanic. a chest with a drain in it is not accumulating air,
// because the air has somewhere to go.
if ((_patient getVariable ["ACM_breathing_Thoracostomy_State", 0]) >= 2) exitWith {
    _patient setVariable ["ACME_clock_ncdLeakPending", 0, false];
    _patient setVariable ["ACME_ncd_leak", 0, true];
};

_pending = (_pending + _elapsed) max 0;
_patient setVariable ["ACME_clock_ncdLeakPending", _pending, false];
if (_pending < 5) exitWith {};
private _dt = _pending min 5;
_patient setVariable ["ACME_clock_ncdLeakPending", 0, false];

// the rate. each needle past the free allowance adds its own slow contribution, so a chest that has been needled
// five times fills three times faster than one needled three times. it is still slow: the default puts a single
// extra needle at about twenty minutes to become a real problem.
private _perNeedle = missionNamespace getVariable ["ACME_ncd_leakPerNeedle", 0.00035];
private _leak = (_patient getVariable ["ACME_ncd_leak", 0]) + (_perNeedle * (_n - _free) * _dt);
_leak = _leak min 1;
[_patient, "ACME_ncd_leak", _leak, 0.005, 5] call ACME_fnc_setVarNetApprox;

// the soft evacuation requirement. it is set once, well before the casualty is in trouble, because the point is
// that somebody decides to move them rather than discovers they should have.
if (_leak > (missionNamespace getVariable ["ACME_ncd_evacAt", 0.25])
    && {!(_patient getVariable ["ACME_ncd_evacFlagged", false])}) then {
    _patient setVariable ["ACME_ncd_evacFlagged", true, true];
    _patient setVariable ["ACME_evacSoft", true, true];
    // the steady breath sounds start here and run until it is drained. this is the finding that arrives before
    // the numbers do.
    if (isNil {_patient getVariable "ACME_bs_pfh"}) then {
        [_patient, "steady"] call ACME_fnc_breathSoundsStart;
    };
};

// the effect itself. it is a breathing penalty rather than a pneumothorax state, so it stacks under whatever else
// is wrong with the chest and it cannot be mistaken for a fresh traumatic pneumo by anything downstream.
// it never tensions. the ceiling is a casualty who is short of breath and hypoxic on exertion, not one who is
// about to arrest.
private _pen = _leak * (missionNamespace getVariable ["ACME_ncd_leakMaxPenalty", 0.45]);
[_patient, "ACME_ncd_breathPenalty", _pen, 0.005, 5] call ACME_fnc_setVarNetApprox;
