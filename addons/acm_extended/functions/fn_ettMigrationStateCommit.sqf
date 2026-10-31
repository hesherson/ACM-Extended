/* Phase 80: authoritative writer for durable ETT migration / obstruction state.
 * Operations:
 *   [patient,"placement",[depth, frame, mainstem, optionalAdjustmentEpoch, optionalTubeTime]]
 *   [patient,"obstruction",[active, untilOr"__KEEP__"]]
 *   [patient,"tip",[[u,v]]]
 * Values omitted or "__KEEP__" retain current state. This preserves legacy paths that cleared the
 * obstruction boolean without rewriting the existing obstruction deadline.
 */
params ["_patient", "_op", ["_data", []]];
if (isNull _patient) exitWith {};
if (!local _patient) exitWith {[_patient, "ettMigrationState", [_op, _data]] call ACME_fnc_ownerDispatch;};
private _keep = "__KEEP__";
switch (toLower _op) do {
    case "placement": {
        // A delayed close-flush must not restore placement after a reset or extubation.
        // Other callers (including tube insertion/removal) retain their existing three-value contract.
        private _adjustmentEpoch = _data param [3, -1];
        if (_adjustmentEpoch >= 0 && {
            _adjustmentEpoch != ([_patient] call ACME_fnc_clinicalEpoch)
            || {!(_patient getVariable ["ACME_ETT_Inserted", false])}
            || {count _data > 4 && {(_data select 4) != (_patient getVariable ["ACME_ETT_Time", -1])}}
        }) exitWith {};
        private _depth = _data param [0, _keep];
        private _frame = _data param [1, _keep];
        private _mainstem = _data param [2, _keep];
        if !(_depth isEqualTo _keep) then {[_patient, "ACME_ETT_Depth", _depth] call ACME_fnc_setVarNet;};
        if !(_frame isEqualTo _keep) then {[_patient, "ACME_ETT_Frame", _frame] call ACME_fnc_setVarNet;};
        if !(_mainstem isEqualTo _keep) then {[_patient, "ACME_ETT_Mainstem", _mainstem] call ACME_fnc_setVarNet;};
    };
    case "obstruction": {
        private _active = _data param [0, _keep];
        private _until = _data param [1, _keep];
        if !(_active isEqualTo _keep) then {[_patient, "ACME_ETT_Obstructing", _active] call ACME_fnc_setVarNet;};
        if !(_until isEqualTo _keep) then {[_patient, "ACME_ETT_ObstructUntil", _until] call ACME_fnc_setVarNet;};
    };
    case "tip": {
        private _frac = _data param [0, _keep];
        if !(_frac isEqualTo _keep) then {[_patient, "ACME_ETT_TipFrac", _frac] call ACME_fnc_setVarNet;};
    };
};
