/* B17: shared dose-driven induction/maintenance for AI and players. ETT presence is never a sedative.
   The same medication state now drives patient physiology regardless of player ownership.
   Release only a state this worker induced. Explicit native stability/forced-state gates protect other clinical causes before WakeUp. */
params ["_patient"];
if (isNull _patient || {!local _patient} || {!alive _patient} || {!(_patient isKindOf "CAManBase")}) exitWith {};
private _owned = _patient getVariable ["ACME_ket_sedated", false];
private _uncon = _patient getVariable ["ACE_isUnconscious", false];
private _active = [_patient] call ACME_fnc_sedationActive;

if (_active) then {
    if (!_owned) then {
        [_patient, "ACME_ket_sedated", true] call ACME_fnc_setVarNet;
        _owned = true;
    };

    if (_uncon) then {
        [_patient, [["lastWakeUpCheck", CBA_missionTime, false]]] call ACM_core_fnc_setAceMedicalState;
    } else {
        if !(_patient getVariable ["ACME_roc_paralyzed", false]) then {
            [_patient, true, 0, false] call ace_medical_fnc_setUnconscious;
        };
    };
} else {
    if (_owned) then {
        [_patient, "ACME_ket_sedated", false] call ACME_fnc_setVarNet;
        if (_uncon) then {
            [_patient, false, "sedation-washout"] call ACM_core_fnc_requestWake;
        };
    };
};
