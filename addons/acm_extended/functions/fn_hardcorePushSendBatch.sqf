/* B121: submit the volume already moved by the local plunger as one acknowledged medication batch. A long push
   therefore creates only periodic medication records, not one network event per frame. */
params [["_force",false,[false]]];
private _job = missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap];
if !(_job isEqualType createHashMap && {count _job > 0}) exitWith {false};
private _delta = +(_job getOrDefault ["unsentDelta",[0,0,[]]]);
_delta params [["_drugMl",0,[0]],["_nsMl",0,[0]],["_comp",[],[[]]]];
private _batchMl = _drugMl + _nsMl;
if (_batchMl <= 0.000001) exitWith {true};
private _elapsed = (_job getOrDefault ["batchElapsed",0]) max 0.05;
// Long normal pushes must become systemic WHILE the plunger is moving, not
// only after the final frame. One acknowledged 1-second aliquot is the upper
// delay; Hardcore's existing 5-second batch tuning remains unchanged.
private _batchSec = if (_job getOrDefault ["standardTimed",false]) then {1} else {
    missionNamespace getVariable ["ACME_hcMed_pushBatchSec",5]
};
if (!_force && {_elapsed < _batchSec}) exitWith {true};
private _medic = _job getOrDefault ["medic",objNull];
private _patient = _job getOrDefault ["patient",objNull];
if (isNull _medic || {isNull _patient} || {!local _medic}) exitWith {false};
// B123: keep the provider-facing one-handed plunger transaction usable on a corpse, but once the casualty is
// engine-dead there is no physiology to update. Consume the already-moved syringe volume locally and discard the
// physiology delta instead of generating medication requests, receipts, sedation/rate queues and ACK traffic.
if (!alive _patient) exitWith {
    _job set ["unsentDelta", [0,0,[]]];
    _job set ["batchElapsed", 0];
    _job set ["lastSend", diag_tickTime];
    _job set ["postmortemNoPhysiology", true];
    missionNamespace setVariable ["ACME_HCMedPushJob", _job];
    true
};
private _body = _job getOrDefault ["bodyPart","body"];
private _site = _job getOrDefault ["site",-2];
private _virtual = _job getOrDefault ["virtual",false];
private _label = _job getOrDefault ["label",""];
private _kind = _job getOrDefault ["kind",""];
private _doses = [];
private _addDose = {
    params ["_source","_ml"];
    if (_source == "" || {_ml <= 0}) exitWith {};
    private _class = _source + "_IV";
    if (_virtual && {_source in ["Adenosine","Amiodarone","Rocuronium"]}) then {_class = _source + "_IV";};
    if (_virtual && {!isClass (configFile >> "ACM_Medication" >> "Medications" >> _class)}) then {
        _class = if (isClass (configFile >> "ACM_Medication" >> "Medications" >> _source)) then {_source} else {_source + "_IV"};
    };
    private _conc = getNumber (configFile >> "ACM_Medication" >> "Concentration" >> _source >> "concentration");
    if (_conc <= 0 || {!([_class,true,true,_virtual] call ACME_fnc_medicationRouteAllowed)}) exitWith {};
    private _dose = _conc * _ml;
    private _rate = _dose * 60 / (_elapsed max 0.05);
    private _rateMeta = ["hcPush",_job getOrDefault ["duration",3],_job getOrDefault ["session",""],_rate];
    _doses pushBack [_class,_dose,true,if (_kind == "epiMixB12") then {"B13_MEASURED_EPI"} else {_label},_elapsed,_virtual,_rateMeta];
};
if !(_comp isEqualTo []) then {
    {[_x param [1,"",[""]],_x param [2,0,[0]]] call _addDose;} forEach _comp;
} else {
    [_job getOrDefault ["med",""],_drugMl] call _addDose;
};
if (_doses isEqualTo []) exitWith {false};
private _meta = ["hcPush",_job getOrDefault ["session",""],_job getOrDefault ["stableId",""],_delta];
_job set ["unsentDelta",[0,0,[]]];
_job set ["batchElapsed",0];
_job set ["lastSend",diag_tickTime];
_job set ["pendingAcks",(_job getOrDefault ["pendingAcks",0]) + 1];
missionNamespace setVariable ["ACME_HCMedPushJob",_job];
private _ok = [_medic,_patient,_body,_doses,"administer",_site,[],_meta] call ACME_fnc_medicationRequest;
// medicationRequest's local failure path feeds the same ACK helper, so do not restore here.
_ok
