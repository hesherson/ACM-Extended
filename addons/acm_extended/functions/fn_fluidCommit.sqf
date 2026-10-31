/* NA3 owner-only event ledger, called at the FINAL flow calculation, once per bag per native vitals update.
   drained mL leaves the bag; admitted mL reaches circulation. Their difference is not systemic medication. */
params ["_patient", "_part", "_index", "_bag", "_drained", "_admitted", "_dt", ["_flush", false]];
if (isNull _patient || {!local _patient} || {_drained <= 0}) exitWith {};
_admitted = (_admitted max 0) min _drained;
// Keep a compact, owner-authored visual record of carrier fluid that actually went into tissue.
// The owner updates exact accumulated volume locally and publishes the compact state at most once per second
// unless severity changes. The last published total also survives patient locality transfer.
private _acmeLeakMl = (_drained - _admitted) max 0;
private _acmeLeakSite = if (_bag param [4, false]) then {_bag param [3, -1]} else {-1};
private _acmeLeakPart = toLowerANSI (_part);
if (_acmeLeakMl > 0.001 && {_acmeLeakSite in [0,1,2]}
    && {_acmeLeakPart in ["leftarm","rightarm","leftleg","rightleg"]}) then {
    private _visualKey = format ["ACME_ivInfiltrationVisual_%1_%2", _acmeLeakPart, _acmeLeakSite];
    private _priorVisual = _patient getVariable [_visualKey, [0, -1, 0, -1]];
    private _priorSeverity = _priorVisual param [0, 0];
    private _priorFlowAt = _priorVisual param [1, -1];
    private _totalMl = _priorVisual param [2, 0];
    private _lastPublishedAt = _priorVisual param [3, -1];
    private _life = missionNamespace getVariable ["ACME_iv_bruiseLifeSec", 1200];
    if !(_life isEqualType 0 && {finite _life} && {_life > 1}) then {_life = 1200;};
    if !(_totalMl isEqualType 0 && {finite _totalMl} && {_totalMl >= 0}) then {_totalMl = 0;};
    if (_priorFlowAt >= 0 && {(serverTime - _priorFlowAt) > _life}) then {_totalMl = 0;};
    _totalMl = _totalMl + _acmeLeakMl;
    private _severity = ceil (linearConversion [0.01, 50, _totalMl, 1, 10, true]);
    _severity = (_severity max 1) min 10;
    private _state = [_severity, serverTime, _totalMl, _lastPublishedAt];
    _patient setVariable [_visualKey, _state, false];
    if (_severity != _priorSeverity || {_lastPublishedAt < 0} || {(serverTime - _lastPublishedAt) >= 1}) then {
        _state set [3, serverTime];
        _patient setVariable [_visualKey, _state, true];
    };
};
private _type = _bag param [0, ""];
if (_type == "Saline" || {_flush}) then {
    [_patient, "ACME_circ_salineGivenMl", (_patient getVariable ["ACME_circ_salineGivenMl", 0]) + _admitted, 5, 1] call ACME_fnc_setVarNetApprox;
    // Saline burden now owns explicit circulation membership; the 0.25 s
    // clearing worker never needs to discover healthy units by world/owner scan.
    if (!isNil "ACME_circ_activePatients") then {ACME_circ_activePatients pushBackUnique _patient;};
    _patient setVariable ["ACME_circ_salineTrackLastMl", _admitted, false];
    _patient setVariable ["ACME_circ_salineTrackLastAt", CBA_missionTime, false];
    _patient setVariable ["ACME_circ_salineTrackLastSource", "NA3 admitted-flow ledger", false];
};
if (_flush) exitWith {};
private _id = _bag param [8, ""];
if (_id == "") exitWith {};
private _entries = _patient getVariable ["ACME_infusion_BagMedications", []];
private _changed = false;
{
    private _e = _x;
    if ((_e param [23, ""]) != _id) then {continue;};
    private _conc = _e param [26, (_e param [13, 0]) / ((_e param [9, 1]) max 0.001)];
    private _remainingDose = _e param [14, 0];
    private _leavingDose = (_conc * _drained) min _remainingDose;
    private _systemicDose = _leavingDose * (_admitted / _drained);
    private _oldDriveSource = missionNamespace getVariable ["ACME_driveIsInfusion",false];
    missionNamespace setVariable ["ACME_driveIsInfusion",true];
    [_patient,_e select 12,_systemicDose,_dt] call ACME_fnc_medicationDriveAdd;
    missionNamespace setVariable ["ACME_driveIsInfusion",_oldDriveSource];
    // Exact bag/access identity and the SAME mass split used by patient fluid admission.
    [_patient,_part,if (_bag select 4) then {_bag select 3} else {-1},
        _e select 12,_leavingDose - _systemicDose,true] call ACME_fnc_medicationLeak;
    _e set [1, _part]; _e set [2, _index]; _e set [4, _bag select 3]; _e set [5, _bag select 4];
    _e set [10, ((_bag select 1) - _drained) max 0];
    _e set [14, (_remainingDose - _leavingDose) max 0];
    _e set [17, if (_dt > 0) then {_systemicDose / _dt} else {0}];
    _e set [18, CBA_missionTime];
    _e set [24, (_e param [24, 0]) + (_leavingDose - _systemicDose)];
    _e set [25, (_e param [25, 0]) + _systemicDose];
    if ((_e select 11) in (missionNamespace getVariable ["ACME_infusion_osmoticAgents", []])) then {
        private _stock = getNumber (configFile >> "ACM_Medication" >> "Concentration" >> (_e select 11) >> "concentration");
        if (_stock <= 0) then {_stock = switch (_e select 11) do {case "HTS3": {7500 / 250}; case "Mannitol": {100000 / 500}; default {0};};};
        if (_systemicDose > 0 && {_stock > 0}) then {[_patient, _e select 11, _systemicDose / _stock, true] call ACME_fnc_tbiApplyOsmotherapy;};
    } else {
        _e set [15, (_e param [15, 0]) + _systemicDose];
        [_patient, _e, (_e select 10) <= 0.01] call ACME_fnc_infusionDeliver;
    };
    _changed = true;
} forEach _entries;
if (_changed) then {
    [_patient, _entries] call ACME_fnc_infusionMedicationStateCommit;
    ACME_circ_activePatients pushBackUnique _patient;
};
