/* B156: derive the lethal-triad base from authoritative physiology, never from the
 * combined bleeding multiplier. Optional values let circulation reuse its current calculation.
 * Recomputing from replicated inputs also makes a new owner independent of local caches.
 * Returns [combined base, calcium factor, hypothermia factor, acidosis factor].
 */
params ["_patient", ["_ionizedCa", -1], ["_acidosis", -1]];
if !(missionNamespace getVariable ["ACME_sys_circ", true]) exitWith {[1,1,1,1]};
private _caFloor = missionNamespace getVariable ["ACME_ca_floor", 0.55];
if (_ionizedCa < 0) then {
    private _transfused = _patient getVariable ["ACM_circulation_TransfusedBlood_Volume", 0];
    private _given = _patient getVariable ["ACME_ca_caCl2Given", 0];
    private _threshold = missionNamespace getVariable ["ACME_ca_citrateThreshold", 1.0];
    private _deficit = ((_transfused - _threshold) max 0) * (missionNamespace getVariable ["ACME_ca_citratePerLiter", 0.18]);
    _ionizedCa = (1 - _deficit + (_given * (missionNamespace getVariable ["ACME_ca_creditPerGram", 0.12]))) min 1 max _caFloor;
};
if (_acidosis < 0) then {
    private _state = _patient getVariable ["ACME_circ_State", createHashMap];
    _acidosis = _state getOrDefault ["acidosis", 0];
};
private _calcium = linearConversion [1, _caFloor, _ionizedCa, 1, (missionNamespace getVariable ["ACME_ca_coagMaxMult", 1.4]), true];
private _hypothermia = linearConversion [
    (missionNamespace getVariable ["ACME_hypo_coagStartTemp", 35]),
    (missionNamespace getVariable ["ACME_hypo_coagFullTemp", 32]),
    (_patient getVariable ["ACME_hypo_temp", 37]),
    1, (missionNamespace getVariable ["ACME_hypo_coagMaxMult", 1.6]), true];
private _acid = linearConversion [
    (missionNamespace getVariable ["ACME_acidosis_coagThreshold", 0.3]), 1, _acidosis,
    1, (missionNamespace getVariable ["ACME_acidosis_coagMaxMult", 1.3]), true];
[(_calcium * _hypothermia * _acid) max 1, _calcium, _hypothermia, _acid]
