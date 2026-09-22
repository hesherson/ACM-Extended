// Gameplay backstop for an excessively long true-KO stretch.
//
// The budget never manufactures wake eligibility. It does not edit SpO2, pain, blood pressure,
// sedation, paralysis, seizure state or traumatic knockout. Time only accumulates while the
// patient is already eligible to wake according to ACM_core_fnc_canWake. When the cap is reached,
// it asks the same canonical requestWake path used everywhere else, then applies awake obtundation
// only after the ACE unconscious flag has actually cleared.
if !(missionNamespace getVariable ["ACME_sys_obtunded", false]) exitWith {};
if !(missionNamespace getVariable ["ACME_ko_systemEnable", true]) exitWith {};

private _mercy = missionNamespace getVariable ["ACME_ko_mercySeconds", 300];
private _hold  = missionNamespace getVariable ["ACME_ko_mercyHoldSeconds", 45];
private _now = CBA_missionTime;

private _applyMercyObtunded = {
    params ["_u"];
    [{
        params ["_p"];
        if (!isNull _p && {alive _p} && {local _p}
            && {!(_p getVariable ["ACE_isUnconscious", false])}) then {
            [_p, true, false, "free", "mercy"] call ACME_fnc_obtundedSet;
        };
    }, [_u], 0.20] call CBA_fnc_waitAndExecute;
};

{
    private _u = _x;
    private _ko = _u getVariable ["ACE_isUnconscious", false];
    private _holdUntil = _u getVariable ["ACME_ko_holdUntil", 0];
    private _wakeEligible = [_u, false] call ACM_core_fnc_canWake;

    if (!_wakeEligible) then {
        if (_holdUntil > 0) then {[_u, "ACME_ko_holdUntil", 0] call ACME_fnc_setVarNet;};
        if ((_u getVariable ["ACME_ko_since", -1]) >= 0) then {[_u, "ACME_ko_since", -1] call ACME_fnc_setVarNet;};
        continue;
    };

    if (_now < _holdUntil) then {
        if (_ko && {[_u, false, "mercy-hold"] call ACM_core_fnc_requestWake}) then {[_u] call _applyMercyObtunded;};
        continue;
    };

    if (_ko) then {
        private _since = _u getVariable ["ACME_ko_since", -1];
        if (_since < 0) then {_since = _now; [_u, "ACME_ko_since", _now] call ACME_fnc_setVarNet;};

        if ((_now - _since) >= _mercy) then {
            if ([_u, false, "mercy-cap"] call ACM_core_fnc_requestWake) then {
                [_u, "ACME_ko_holdUntil", _now + _hold] call ACME_fnc_setVarNet;
                [_u, "ACME_ko_since", -1] call ACME_fnc_setVarNet;
                [_u] call _applyMercyObtunded;
            };
        };
    } else {
        if ((_u getVariable ["ACME_ko_since", -1]) >= 0) then {[_u, "ACME_ko_since", -1] call ACME_fnc_setVarNet;};
    };
} forEach (allUnits select {local _x && {alive _x} && {isPlayer _x}});
