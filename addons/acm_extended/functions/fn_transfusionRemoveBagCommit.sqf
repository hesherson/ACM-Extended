// Owner-authoritative removal for ACM's native transfusion Remove Bag action.
// The provider sends identity plus a snapshot signature, never a replacement IV_Bags map. This prevents two
// providers from deleting/refunding the same bag or a stale UI index from deleting a different bag after reordering.
if (canSuspend) exitWith {private _ok = false; isNil {_ok = _this call ACME_fnc_transfusionRemoveBagCommit;}; _ok};
params [
    ["_patient", objNull, [objNull]],
    ["_medic", objNull, [objNull]],
    ["_part", "", [""]],
    ["_bagUid", "", [""]],
    ["_expectedIndex", -1, [0]],
    ["_expectedSig", [], [[]]],
    ["_epoch", -1, [0]],
    ["_requestId", "", [""]]
];
if (isNull _patient || {!local _patient} || {_requestId == ""}) exitWith {false};

private _receipts = _patient getVariable ["ACME_txRemoveReceipts", createHashMap];
private _prior = _receipts getOrDefault [_requestId, []];
if !(_prior isEqualTo []) exitWith {
    private _source = (missionNamespace getVariable ["ACME_resourceReturnSources",createHashMap]) getOrDefault [_requestId,[]];
    if (count _source == 3 && {(_source select 1) == "funded"}) then {
        private _fingerprint = _source select 0;
        ["funded",[_fingerprint select 0,_fingerprint select 1,_requestId,_fingerprint select 2]] call ACME_fnc_resourceReturnSource;
    };
    if (!isNull _medic) then {["ACME_transfusionRemoveResult", _prior, _medic] call CBA_fnc_targetEvent;};
    _prior param [2, false]
};

private _reply = {
    params ["_accepted", ["_bag", []], ["_reason", ""]];
    private _payload = [_patient, _requestId, _accepted, _bag, _part, _reason];
    _receipts set [_requestId, _payload];
    // Bounded owner-local replay cache. It is transaction bookkeeping, not patient presentation state.
    private _keys = keys _receipts;
    while {count _keys > 32} do {_receipts deleteAt (_keys deleteAt 0);};
    _patient setVariable ["ACME_txRemoveReceipts", _receipts, false];
    if (!isNull _medic) then {["ACME_transfusionRemoveResult", _payload, _medic] call CBA_fnc_targetEvent;};
    _accepted
};

if (_patient getVariable ["ACME_persistenceFrozen",false] || {_medic getVariable ["ACME_persistenceFrozen",false]}) exitWith {[false, [], "Equipment is being saved. Try again shortly."] call _reply};
if (_epoch != ([_patient] call ACME_fnc_clinicalEpoch)) exitWith {[false, [], "Patient state changed. Reopen the transfusion menu."] call _reply};
if (isNull _medic || {!alive _medic} || {!([_medic] call ace_common_fnc_isAwake)}
    || {(_medic distance _patient) > ace_medical_gui_maxDistance}) exitWith {[false, [], "Provider can no longer remove that bag."] call _reply};

private _originalMap = [_patient getVariable ["ACM_circulation_IV_Bags",createHashMap]] call ACME_fnc_syringeDeliveryCopy;
private _map = [_originalMap] call ACME_fnc_syringeDeliveryCopy;
private _arr = +(_map getOrDefault [_part, []]);
private _idx = -1;
if (_bagUid != "") then {
    _idx = _arr findIf {(_x param [8, "", [""]]) == _bagUid};
} else {
    // Legacy/unidentified bag: only accept the exact displayed slot if its native 0..7 fields still match.
    if (_expectedIndex >= 0 && {_expectedIndex < count _arr}) then {
        private _candidate = _arr select _expectedIndex;
        if ((_candidate select [0, 8]) isEqualTo _expectedSig) then {_idx = _expectedIndex;};
    };
};
if (_idx < 0) exitWith {[false, [], "That bag changed or was already removed."] call _reply};

private _bag = +(_arr select _idx);
private _actualUid = _bag param [8, "", [""]];
// Medication infusions have their own discard transaction; native Remove Bag must not orphan their dose record.
if ((_bag param [0, ""]) == "ACME_Propofol" || {_actualUid != "" && {((_patient getVariable ["ACME_infusion_BagMedications", []]) findIf {(_x param [23, ""]) == _actualUid}) >= 0}}) exitWith {
    [false, [], "Use Remove Infusion for a medicated bag."] call _reply
};

if (count (_medic getVariable ["ACME_resourceReturnPending",createHashMap]) >= 128) exitWith {[false,[],"Finish pending equipment returns before removing another bag."] call _reply};
private _prepared = ["remove",_patient,_requestId,[_bag]] call ACME_fnc_resourceReturnProducts;
if !(_prepared select 0) exitWith {[false,[],"This bag's return data is invalid. It remains attached."] call _reply};
private _returnArgs = [_medic,_patient,_requestId,_prepared select 1];
if !(["stage",_returnArgs] call ACME_fnc_resourceReturnSource) exitWith {[false,[],"Return custody could not be staged. The bag remains attached."] call _reply};
_arr deleteAt _idx;
_map set [_part, _arr];
[_patient, _map, true] call ACME_fnc_ivBagsCommit;
private _actual = _patient getVariable ["ACM_circulation_IV_Bags",createHashMap];
if (_actual isNotEqualTo _map) exitWith {
    [if (_actual isEqualTo _originalMap) then {"cancel"} else {"uncertain"},_returnArgs] call ACME_fnc_resourceReturnSource;
    [false,[],"Source custody could not be confirmed. No return was issued."] call _reply
};
["funded",_returnArgs] call ACME_fnc_resourceReturnSource;
[_patient, _part] call ACM_circulation_fnc_updateActiveFluidBags;

private _pi = ACME_infusion_bodyParts find (toLowerANSI _part);
if (_pi >= 0) then {
    private _iv = _bag param [4, true, [true]];
    private _site = _bag param [3, -1, [0]];
    _patient setVariable [format ["ACME_clampRate_%1_%2_%3", _pi, _iv, _site], -1, false];
};
if (!isNil "ace_medical_treatment_fnc_addToLog") then {
    [_patient,"activity","%1 removed a fluid bag from %2",[[_medic,false,true] call ace_common_fnc_getName,([_part] call ACM_core_fnc_getBodyPartString)]] call ace_medical_treatment_fnc_addToLog;
};
[true, _bag, ""] call _reply
