// play an animation that ACE cannot immediately undo.
// call it as [_unit, _anim, _holdsec, _priority] call ACME_fnc_doAnimHeld.
//
// _priority is ACE's doAnimation priority. B73 changes the DEFAULT to 1 for every ACME-owned request.
//   1  playMoveNow. it interrupts, but the engine walks the authored move graph to get there. This is the project
//      default: entering a treatment/held pose must visibly interpolate instead of teleporting to its first frame.
//   2  playMoveNow plus ACE's switchMove fallback. That fallback can hard-snap and therefore must be opt-in only for
//      a proven engine-state repair, never the normal entry path. No current ACME runtime caller opts into it.
//   0  playMove. it waits for the current move to end first.
// the difference is ACE's own, at common/functions/fnc_doAnimation.sqf:10 to 12.
// ACE's treatment pipeline plays an end animation on the medic at priority 2, the strongest setting there is, in
// fnc_treatmentsuccess. that call happens after callbacksuccess has already run. so any animation started from a
// treatment callback is played and then overwritten a moment later by ACE putting the medic back to their default
// pose.
// it is not a priority problem, which is what it looks like: priority 2 already falls back to switchmove and cannot
// be beaten. it is an ordering problem, and ordering cannot be won by shouting louder.
// so this waits until ACE has finished, then plays. and then it checks, because a single deferred call is still a
// race: if anything else has moved the unit in the meantime it re-asserts, a few times over a short window, and
// stops as soon as the animation has actually taken.
// it gives up quietly if the unit ends up somewhere the animation cannot apply, such as inside a vehicle, rather
// than fighting for it.
params ["_unit", "_anim", ["_hold", 1.2], ["_prio", 1], ["_localOnly", false]];

// only the newest request for this unit is allowed to keep re-asserting.
// every call used to start its own re-assert loop with no knowledge of any other, and a sequence that plays
// several animations in a row on one unit therefore ended up with two or three loops running at once, each
// pushing a different animation back every 0.12 s. they fought, and what came out was an animation flickering
// between states many times a second.
// that is what head elevation looked like: the medic chains four of these 0.8 to 1.8 s apart and the casualty
// gets two more, so the pick-up looped instead of playing once and the casualty's head twitched continuously.
// a generation counter fixes it. each call takes the next number, and any loop whose number is no longer the
// current one retires immediately, so a new animation always wins and the old one stops arguing with it.
//
// THE SECOND HALF OF THE SAME FAULT, found at v0.9.999r-39.
// the loop below stops as soon as the animation has taken. the test for that was
//     (animationState _u) isEqualTo _a
// and it can never be true. the engine reports a move name in LOWER CASE, and isEqualTo compares case, while
// every name handed to this function is mixed case. ACE writes its own comparison set in lower case for this
// reason, at ace dragging/script_component.hpp:22, and ACE fnc_doAnimation:61 uses == rather than isEqualTo.
// so the loop never saw the animation take and pushed it again every 0.12 s for the whole hold. each push is
// older callers used ACE priority 2, which could reach switchMove and restart the animation at its first frame.
// B73 defaults held requests to priority 1 so re-assertion stays on the move graph and never hard-snaps into a pose.
// two changes: the test compares in lower case, and a separate counter caps how many times the animation is
// actually pushed. the cap is the guard for a name the engine never reports back, such as a base move class.
// the knob is ACME_anim_reassertMax and it defaults to 3.
// NOTHING ANIMATES A UNIT IN A VEHICLE. see fn_doAnim for why. this is checked here as well as there, so a
// queued pose does not even start a re-assert loop for a unit who is seated.
if (isNull _unit) exitWith {};
// Provider-owned input loops opt in; remote patient choreography retains the existing default.
if (_localOnly && {!local _unit}) exitWith {};
if ([_unit] call ACME_fnc_animBlocked) exitWith {};

private _gen = (_unit getVariable ["ACME_dah_gen", 0]) + 1;
private _localityEpoch = _unit getVariable ["ACME_providerLocalityEpoch", 0];
_unit setVariable ["ACME_dah_gen", _gen, false];
if (isNull _unit) exitWith {};
if (_anim isEqualTo "") exitWith {};

[{
    params ["_args", "_pfh"];
    _args params ["_u", "_a", "_tEnd", "_tries", "_g", "_asserts", "_p", "_localOnly", "_localityEpoch"];

    if (isNull _u || {_localOnly && {!local _u || {(_u getVariable ["ACME_providerLocalityEpoch", 0]) != _localityEpoch}}}
        || {!alive _u} || {CBA_missionTime > _tEnd} || {_tries > 12}) exitWith {
        [_pfh] call CBA_fnc_removePerFrameHandler;
    };
    // superseded. something newer wants this unit to do something else, so stop pushing.
    if ((_u getVariable ["ACME_dah_gen", 0]) != _g) exitWith {
        [_pfh] call CBA_fnc_removePerFrameHandler;
    };
    // in a vehicle the pose will not hold, and forcing it looks worse than letting it go.
    if (!isNull objectParent _u) exitWith { [_pfh] call CBA_fnc_removePerFrameHandler; };

    // Provider-only retries may run after the provider selected prone during holstering.
    // Resolve before comparing and retain that target; patient choreography uses the
    // default false branch and must never pass through this provider posture resolver.
    if (_localOnly) then {
        _a = [_u, _a] call ACME_fnc_providerAnimation;
        _args set [1, _a];
    };

    // the engine reports the move name in lower case, so both sides are lowered before the comparison.
    if ((toLower animationState _u) isEqualTo (toLower _a)) exitWith {
        // it took. one more frame of grace in case ACE is still mid-restore, then stop watching.
        _args set [3, _tries + 1];
        if (_tries > 2) then { [_pfh] call CBA_fnc_removePerFrameHandler; };
    };

    // the re-assert cap. it is a separate count from _tries, because _tries also counts the grace ticks above.
    if (_asserts >= (missionNamespace getVariable ["ACME_anim_reassertMax", 3])) exitWith {
        [_pfh] call CBA_fnc_removePerFrameHandler;
    };

    [_u, _a, _p] call ACME_fnc_doAnim;
    _args set [3, _tries + 1];
    _args set [5, _asserts + 1];
}, 0.12, [_unit, _anim, CBA_missionTime + _hold, 0, _gen, 0, _prio, _localOnly, _localityEpoch]] call CBA_fnc_addPerFrameHandler;
