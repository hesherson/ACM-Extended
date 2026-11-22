/*
 * Where a rescuer is local, every frame while he drags or carries: may he jog? While he holds the sprint key
 * (or has doubled the forward key) his forced walk is lifted. Sprinting itself stays blocked, so what he gets is
 * a jog, and that is held to a fixed share of its speed (setting acme_drag_jogPace), so it is one steady pace
 * whatever he carries. With ACE's fatigue on, jogging with a load costs several times the effort (the duty
 * factor in XEH_postInit.sqf, setting acme_drag_jogDuty), and ACE's own forced walk of an exhausted man stays in
 * force: only this mod's reason for walking is lifted.
 * Arguments: 0: rescuer, 1: the reason his walk is forced under ("acme_drag", "acme_carry"), 2: he has let go
 * <BOOL> (default: false).
 */
params ["_unit", "_reason", ["_end", false]];
private _jog = !_end && {missionNamespace getVariable ["acme_drag_jog", true]}
    && {
        // (acme_drag_jogTest: for the scripted tests, which have no keys)
        (missionNamespace getVariable ["acme_drag_jogTest", false])
        || {hasInterface && {_unit isEqualTo (call ace_common_fnc_player)} && {(inputAction "turbo") > 0 || {(inputAction "MoveFastForward") > 0}}}
    };
if (_jog isEqualTo (_unit getVariable ["acme_drag_jogging", false])) exitWith {};
_unit setVariable ["acme_drag_jogging", [nil, true] select _jog];
if (!_end) then {[_unit, "forceWalk", _reason, !_jog] call ace_common_fnc_statusEffect_set;};
_unit setVariable ["acme_pace_jog", [nil, missionNamespace getVariable ["acme_drag_jogPace", 0.72]] select _jog];
[_unit] call acme_sked_fnc_paceApply;
