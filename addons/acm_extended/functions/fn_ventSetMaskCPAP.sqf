/* B223: select mask CPAP on an already attached ventilator, stopped or running.
   Idempotent owner command bound to the same custody/clinical episode and a short deadline. */
params [["_patient", objNull, [objNull]], ["_medic", objNull, [objNull]],
    ["_custody", "", [""]], ["_epoch", -1, [0]], ["_deadline", -1, [0]], ["_request", [], [[]]]];
if (isNull _patient || {isNull _medic}) exitWith {false};
if (!local _patient) exitWith {
    [_patient, "ventSetMaskCPAP", _this] call ACME_fnc_ownerDispatch;
    true
};
if (!finite _deadline || {serverTime > _deadline} || {_deadline > serverTime + 5}
    || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}
    || {_custody == ""} || {_custody != (_patient getVariable ["ACME_vent_custodyId", ""])}
    || {!(_patient getVariable ["ACME_vent_onPatient", false])}
    || {!(_patient getVariable ["ACME_vent_circuit", false])}
    || {_patient getVariable ["ACME_vent_recovering", false]}
    || {!alive _medic} || {!([_medic] call ace_common_fnc_isAwake)}
    || {!([_medic, "ventilator", true] call ACME_fnc_procedureAllowed)}
    || {!([_medic, _patient] call ACME_fnc_ventRecoveryNear)}) exitWith {
    if (_request isNotEqualTo []) then {[_medic, "ventMaskApplyReply", [_medic, _request, false]] call ACME_fnc_ownerDispatch;};
    false
};
if !([_patient] call ACME_fnc_ventMaskSelected) then {
    [_patient, "ACME_vent_mode", "CPAP PS HF"] call ACME_fnc_setVarNet;
    [_patient, "ACME_vent_iface", "NON INVASIVE"] call ACME_fnc_setVarNet;
    [_patient, "ACME_vent_psup", 0] call ACME_fnc_setVarNet;
};
[_patient] call ACME_fnc_ventSyncMask;
if (_request isNotEqualTo []) then {[_medic, "ventMaskApplyReply", [_medic, _request, true]] call ACME_fnc_ownerDispatch;};
true
