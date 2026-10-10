// Owner-authoritative Pull Bag transaction for ACME's exact-volume used-bag workflow.
params [
    ["_patient", objNull, [objNull]], ["_medic", objNull, [objNull]], ["_part", "", [""]],
    ["_bagUid", "", [""]], ["_expectedIndex", -1, [0]], ["_expectedSig", [], [[]]],
    ["_epoch", -1, [0]], ["_requestId", "", [""]], ["_issued",-1,[0]]
];
if (isNull _patient || {!local _patient} || {_requestId == ""}) exitWith {false};
if (count _requestId > 128 || {!finite _issued} || {_issued < 0}
    || {serverTime - _issued > 10} || {_issued > serverTime + 2}) exitWith {false};
private _receipts = _patient getVariable ["ACME_txPullReceipts", createHashMap];
private _prior = _receipts getOrDefault [_requestId, []];
if !(_prior isEqualTo []) exitWith {
    if (!isNull _medic) then {["ACME_transfusionPullResult", _prior, _medic] call CBA_fnc_targetEvent;};
    _prior param [2, false]
};
private _times=_patient getVariable ["ACME_txPullReceiptsTimes",createHashMap];
{if (serverTime - (_times get _x) > 12) then {_receipts deleteAt _x;_times deleteAt _x;};} forEach keys _times;
if (count _receipts >= 512) exitWith {false};
private _reply = {
    params ["_accepted", ["_bag", []], ["_mode", ""], ["_onY", false], ["_reason", ""]];
    private _payload = [_patient, _requestId, _accepted, _bag, _part, _mode, _onY, _reason];
    _receipts set [_requestId, _payload];
    _times set [_requestId,serverTime]; [_patient,"ACME_txPullReceipts",_receipts] call ACME_fnc_setVarNet; [_patient,"ACME_txPullReceiptsTimes",_times] call ACME_fnc_setVarNet;
    if (!isNull _medic) then {["ACME_transfusionPullResult", _payload, _medic] call CBA_fnc_targetEvent;};
    _accepted
};
if (_epoch != ([_patient] call ACME_fnc_clinicalEpoch)) exitWith {[false, [], "", false, "Patient state changed. Reopen the transfusion menu."] call _reply};
if (isNull _medic || {!alive _medic} || {!([_medic] call ace_common_fnc_isAwake)} || {(_medic distance _patient) > ace_medical_gui_maxDistance}) exitWith {
    [false, [], "", false, "Provider can no longer pull that bag."] call _reply
};
private _map = _patient getVariable ["ACM_circulation_IV_Bags", createHashMap];
private _arr = +(_map getOrDefault [_part, []]);
private _idx = -1;
if (_bagUid != "") then {_idx = _arr findIf {(_x param [8, "", [""]]) == _bagUid};}
else {
    if (_expectedIndex >= 0 && {_expectedIndex < count _arr}) then {
        private _candidate = _arr select _expectedIndex;
        if ((_candidate select [0,8]) isEqualTo _expectedSig) then {_idx = _expectedIndex;};
    };
};
if (_idx < 0) exitWith {[false, [], "", false, "That bag changed or was already pulled."] call _reply};
private _bag = +(_arr select _idx);
private _type = _bag param [0, ""];
if (_type == "FBTK") exitWith {[false, [], "", false, "Use native Remove Bag for an FBTK collection bag."] call _reply};
private _site = _bag param [3, -1];
private _iv = _bag param [4, true];
private _onY = [_patient, _part, _iv, _site] call ACME_fnc_isYLineAccess;

// Empty markers are just structural cleanup and never create salvage.
if (_type in ["ACME_Empty", "ACME_EmptySaline"]) exitWith {
    _arr deleteAt _idx; _map set [_part, _arr];
    [_patient, _map, true] call ACME_fnc_ivBagsCommit;
    [_patient, _part] call ACM_circulation_fnc_updateActiveFluidBags;
    [true, _bag, "empty", _onY, ""] call _reply
};

private _uid = _bag param [8, "", [""]];
private _entries = +(_patient getVariable ["ACME_infusion_BagMedications", []]);
private _wasInfusion = false;
private _kept = _entries select {
    private _same = if (_uid != "") then {(_x param [23, ""]) == _uid} else {
        ((_x param [1, ""]) == _part) && {(_x param [2, -1]) == _idx}
            && {(_x param [4, -1]) == _site} && {(_x param [5, true]) == _iv}
    };
    if (_same) then {_wasInfusion = true;};
    !_same
};
if (_wasInfusion) then {[_patient, _kept] call ACME_fnc_infusionMedicationStateCommit;};

if (_onY) then {
    private _marker = +_bag;
    _marker set [0, ["ACME_EmptySaline", "ACME_Empty"] select (_type in ["Blood", "FreshBlood", "FBTK"])];
    _marker set [1, 0];
    _arr set [_idx, _marker];
} else {
    _arr deleteAt _idx;
};
_map set [_part, _arr];
[_patient, _map, true] call ACME_fnc_ivBagsCommit;
[_patient, _part] call ACM_circulation_fnc_updateActiveFluidBags;
if (_wasInfusion) then {
    private _pi = ACME_infusion_bodyParts find (toLowerANSI _part);
    if (_pi >= 0 && {_site >= 0}) then {_patient setVariable [format ["ACME_clampRate_%1_%2_%3", _pi, _iv, _site], -1, false];};
};
if (!isNil "ace_medical_treatment_fnc_addToLog") then {
    private _verb = ["pulled a fluid bag", "removed and discarded a spent infusion"] select _wasInfusion;
    [_patient, "activity", "%1 %2", [[_medic, false, true] call ace_common_fnc_getName, _verb]] call ace_medical_treatment_fnc_addToLog;
};
[true, _bag, ["used", "discard"] select _wasInfusion, _onY, ""] call _reply
