// play a run of animations on one unit, in order, each one allowed to finish before the next starts.
// call it as [_unit, _steps, _mode] call ACME_fnc_animQueue.
// _steps is [[animation, seconds], ...] or [[animation, seconds, priority], ...]. an empty animation string is a
// pause of that length, which is how you hold a pose without re-asserting it.
// the priority is ACE's doAnimation priority and B73 DEFAULTS EVERY QUEUED STEP TO 1. Queue entries are visible
// movements between authored states, so they must follow the move graph instead of falling through to switchMove.
// A caller may still provide an explicit priority, but normal ACME treatment sequencing never requests priority 2.
// _mode is "append", the default, which queues behind whatever is already running, or "replace", which drops the
// steps that have not started yet and lets the step now playing finish first.
//
// this exists because fn_doanimheld can only hold one animation at a time. a second call takes the next
// generation and the first one stands down immediately, wherever it had got to. that is correct for a single
// pose and wrong for a sequence: chaining calls on fixed delays meant every animation was cut off by the next
// one, and whichever happened to be last is what the unit was left in.
// so the queue owns the timing. each step is handed to doanimheld with a hold equal to its own length, and the
// next step does not start until that length has elapsed.
params ["_unit", "_steps", ["_mode", "append"]];
if (isNull _unit) exitWith {};
if !(missionNamespace getVariable ["ACME_interventionAnimations", true]) exitWith {
    _unit setVariable ["ACME_animQ", [], false];
};
if !(_steps isEqualType []) exitWith {};
// NOTHING ANIMATES A UNIT IN A VEHICLE. see fn_doAnim for why. the whole run is dropped rather than queued,
// because a queue that survives the ride would fire the moment the casualty is unloaded, several minutes after
// the treatment that asked for it.
if ([_unit] call ACME_fnc_animBlocked) exitWith {};

private _q = _unit getVariable ["ACME_animQ", []];
if !(_q isEqualType []) then { _q = []; };
if (_mode == "replace") then { _q = []; };
{
    if (_x isEqualType [] && {count _x >= 1}) then {
        _q pushBack [_x select 0, (_x param [1, 1.4]), (_x param [2, 1])];
    };
} forEach _steps;
_unit setVariable ["ACME_animQ", _q, false];

// the driver is already running and will pick the new steps up on its next pop.
if (_unit getVariable ["ACME_animQActive", false]) exitWith {};
_unit setVariable ["ACME_animQActive", true];

[{
    params ["_args", "_h"];
    _args params ["_u"];
    if (isNull _u || {!alive _u} || {!(missionNamespace getVariable ["ACME_interventionAnimations", true])}) exitWith {
        [_h] call CBA_fnc_removePerFrameHandler;
        if (!isNull _u) then {
            _u setVariable ["ACME_animQ", [], false];
            _u setVariable ["ACME_animQActive", false, false];
        };
    };

    // the step now playing has not finished, so leave it alone.
    if (CBA_missionTime < (_u getVariable ["ACME_animQEnd", 0])) exitWith {};

    private _q = _u getVariable ["ACME_animQ", []];
    if !(_q isEqualType []) then { _q = []; };
    if (_q isEqualTo []) exitWith {
        [_h] call CBA_fnc_removePerFrameHandler;
        _u setVariable ["ACME_animQActive", false, false];
    };

    private _step = _q deleteAt 0;
    _u setVariable ["ACME_animQ", _q, false];
    _step params [["_a", ""], ["_d", 1.4], ["_p", 1]];
    if (_d <= 0) then { _d = 0.1; };
    if (_a != "") then { [_u, _a, _d, _p] call ACME_fnc_doAnimHeld; };
    _u setVariable ["ACME_animQEnd", CBA_missionTime + _d, false];
}, 0.05, [_unit]] call CBA_fnc_addPerFrameHandler;
