// A scheduled compatibility caller must not allow a vitals tick during carrier staging.
if (canSuspend) exitWith {isNil {_this call ACME_fnc_preparedAttachLocal;};};
params ["_args", "_id", "_epoch"];
_args params ["_medic", "_patient", "_target", "_item", "_action", "_vehicle", "_part", "_iv", "_site", "_volume", "_prepared", "_index", "_label", ["_staged", []]];
if (!local _patient) exitWith {[_patient, "preparedAttach", _this] call ACME_fnc_ownerDispatch;};
if (isNull _patient || {isNull _medic} || {_id == ""}) exitWith {};
private _fingerprint = [_medic, _epoch, +_prepared, _part, _iv, _site, _action];
private _reason = "access-or-prepared-set-changed";
private _results = _patient getVariable ["ACME_preparedResults", createHashMap];
private _previous = _results getOrDefault [_id, []];
if !(_previous isEqualTo []) exitWith {
    if ((_previous param [3, []]) isEqualTo _fingerprint) then {
        ["ACME_preparedAck", [_id, _previous select 0, _previous select 1, _previous param [2, ""]], _medic] call CBA_fnc_targetEvent;
    } else {
        ["ACME_preparedAck", [_id, false, "", "request-mismatch"], _medic] call CBA_fnc_targetEvent;
    };
};
private _ok = !isNull _medic && {alive _medic} && {!(_medic getVariable ["ACE_isUnconscious", false])} && {_medic distance _patient <= 5 || {!isNull objectParent _medic && {objectParent _medic == objectParent _patient}}} && {_epoch == ([_patient] call ACME_fnc_clinicalEpoch)} && {!([_patient, _part, _iv, _site] call ACME_fnc_isYLineAccess)};
private _pi = ACME_infusion_bodyParts find toLowerANSI _part;
private _access = if (_pi >= 0) then {[_patient, _iv, _pi, _site] call ACM_circulation_fnc_getAccessType} else {0};
_ok = _ok && {_access > 0} && {[_patient, _part, _iv, _site] call ACME_fnc_transfusionAccessValid};
private _cfg = configFile >> "ace_medical_treatment" >> "IV" >> _action;
private _carrierType = getText (_cfg >> "type");
private _carrierVolume = getNumber (_cfg >> "volume");
_ok = _ok && {isClass _cfg} && {_action isEqualTo (_prepared param [2, ""])}
    && {finite _carrierVolume} && {_carrierVolume > 1};
private _components = [_prepared] call ACME_fnc_preparedComponents;
private _customStaged = (_prepared param [15, ""]) != "";
_ok = _ok && {!(_components isEqualTo [])};
if (_customStaged) then {
    private _sets = _medic getVariable ["ACME_preparedIVSets", []];
    private _preparedLive = _medic getVariable ["ACME_infusion_PreparedBags", []];
    private _hasPreparedSet = (_sets findIf {(_x select 0) == (_prepared select 0)}) >= 0 &&
        {(_preparedLive findIf {_x isEqualTo _prepared}) >= 0};
    _ok = _ok && {_hasPreparedSet};
    if (!_hasPreparedSet) then {_reason = "prepared-set-missing";};
};
if !(_staged isEqualTo []) then {
    private _sets = _medic getVariable ["ACME_preparedIVSets", []];
    _ok = _ok && {(toLowerANSI (getText (configFile >> "ace_medical_treatment" >> "IV" >> _action >> "type"))) in keys (missionNamespace getVariable ["ACME_infusion_premixedByType", createHashMap])} && {(_sets findIf {(_x select 0) == (_staged select 0)}) >= 0};
};
// Recheck occupancy on the owner, including a clamped/stopped or empty real bag.
private _blocked = [_patient, _part, _iv, _site] call ACME_fnc_preparedAttachBlockReason;
if (_blocked != "") then {_ok = false; _reason = _blocked;};
_ok = _ok && {
    (_components findIf {
        private _class = (missionNamespace getVariable ["ACME_infusion_deliveryClassOverride", createHashMap]) getOrDefault [_x select 0, format ["%1_IV", _x select 0]];
        !((_x select 1) > 0) || {!finite (_x select 1)} || {!(isClass (configFile >> "ACM_Medication" >> "Medications" >> _class) || {(_x select 0) in (missionNamespace getVariable ["ACME_infusion_osmoticAgents", []])})}
    }) < 0
};
if (_epoch != ([_patient] call ACME_fnc_clinicalEpoch)) then {_reason = "patient-changed";};
if (_medic distance _patient > 5 && {isNull objectParent _medic || {objectParent _medic != objectParent _patient}}) then {_reason = "out-of-range";};
if (!alive _medic || {_medic getVariable ["ACE_isUnconscious", false]}) then {_reason = "provider-unavailable";};
// A new request ID cannot duplicate an already accepted set while its ACK is in flight.
private _alreadyAttached = (values _results) findIf {
    private _f = _x param [3, []];
    (_x param [0, false]) && {count _f >= 3}
        && {(_f select 0) isEqualTo _medic} && {(_f select 1) == _epoch}
        && {((_f select 2) param [0, ""]) == (_prepared param [0, ""])}
};
if (_alreadyAttached >= 0) then {_ok = false; _reason = "set-already-attached";};
private _exactVolume = if (_customStaged) then {_prepared param [10, 0]} else {_staged param [9, 0]};
if (!_customStaged && {_exactVolume <= 0}) then {_exactVolume = _carrierVolume;};
private _carrierContext = [_patient, _part, -1, _carrierType, _access, _site, _iv, -1, _exactVolume, -1, _exactVolume];
_ok = _ok && {_exactVolume isEqualType 0} && {finite _exactVolume} && {_exactVolume > 1}
    && {[_carrierContext] call ACME_fnc_canMedicateBagContext};
private _doseId = "";
if (_ok) then {
    // Snapshot this owner-local transaction before any carrier creation. No scheduler
    // suspension or asynchronous drug registration is permitted inside this block.
    private _beforeMap = _patient getVariable ["ACM_circulation_IV_Bags", createHashMap];
    private _hadPart = _part in _beforeMap;
    private _beforeBags = +(_beforeMap getOrDefault [_part, []]);
    private _beforeMeds = +(_patient getVariable ["ACME_infusion_BagMedications", []]);
    private _beforeActive = _patient getVariable ["ACM_circulation_IV_Bags_Active", false];
    // Do not trust the callback's return value as the only proof of bag creation.
    [_patient, _part, _action, _access, _iv, _site, false, true] call ace_medical_treatment_fnc_ivBagLocal;
    private _created = [_patient, _part, _beforeBags, _carrierType, _carrierVolume, _site, _iv, _access] call ACME_fnc_preparedCarrierResolve;
    private _bagId = "";
    _reason = "carrier-identity";
    if !(_created isEqualTo []) then {
        _created params ["_bi", "_resolvedUid"];
        _bagId = _resolvedUid;
        private _map = _patient getVariable ["ACM_circulation_IV_Bags", createHashMap];
        private _bags = _map getOrDefault [_part, []];
        private _b = +(_bags select _bi);
        _b set [1, _exactVolume];
        if (_customStaged) then {_b set [6, _exactVolume];};
        _bags set [_bi, _b]; _map set [_part, _bags];
        [_patient, _map, false] call ACME_fnc_ivBagsCommit;
        private _ctx = [_patient, _part, _bi, _b select 0, _access, _site, _iv, _b select 5, _b select 6, _b select 7, _b select 1, _bagId];
        private _accepted = true;
        _reason = "medication-registration";
        {
            _x params ["_med", "_dose"];
            private _partId = format ["%1:%2", _id, _forEachIndex];
            private _registered = [_ctx, _med, _dose, _prepared param [5,600], _prepared param [6,20], 0, 0, _partId, _bagId, _epoch, [], 0, true] call ACME_fnc_infusionRegisterLocal;
            if (isNil "_registered" || {!(_registered isEqualType "")} || {_registered == ""}) exitWith {_accepted = false;};
            private _recorded = (_patient getVariable ["ACME_infusion_BagMedications", []]) findIf {
                (_x param [0, ""]) == _registered && {(_x param [23, ""]) == _bagId}
                    && {(_x param [11, ""]) == _med}
            };
            if (_recorded < 0) exitWith {_accepted = false;};
            if (_doseId == "") then {_doseId = _registered;};
        } forEach _components;
        if (!_accepted) then {_doseId = "";};
    };
    _ok = _doseId != "";
    if (!_ok) then {
        // Includes missing/ambiguous identity and partial multi-drug registration.
        // Restore the exact pre-call state; never leave a plain carrier or partial dose.
        private _map = _patient getVariable ["ACM_circulation_IV_Bags", createHashMap];
        if (_hadPart) then {_map set [_part, _beforeBags];} else {_map deleteAt _part;};
        [_patient, _beforeMeds] call ACME_fnc_infusionMedicationStateCommit;
        [_patient, _map] call ACME_fnc_ivBagsCommit;
        [_patient, [["ivBagsActive", _beforeActive]], true] call ACM_circulation_fnc_setRuntimeState;
        [_patient, _part] call ACM_circulation_fnc_updateActiveFluidBags;
    } else {
        // Publish the complete medicated bag before enabling the native drain loop.
        private _entries = _patient getVariable ["ACME_infusion_BagMedications", []];
        [_patient, _entries] call ACME_fnc_infusionMedicationStateCommit;
        [_patient, _patient getVariable ["ACM_circulation_IV_Bags", createHashMap]] call ACME_fnc_ivBagsCommit;
        private _first = _entries select (_entries findIf {(_x param [0, ""]) == _doseId});
        [_patient, _first] call ACME_fnc_infusionFlow;
        ACME_infusion_activePatients pushBackUnique _patient;
        if (_iv && {_site >= 1} && {_part in ["leftarm", "rightarm", "leftleg", "rightleg"]}
            && {(_components findIf {(_x select 0) == "Epinephrine"}) >= 0}) then {
            _patient setVariable ["ACME_rhythm_epiDripEarliest", CBA_missionTime + (missionNamespace getVariable ["ACME_infusion_epiArrhythmiaOnsetSec", 60]), true];
        };
        [_patient, _part] call ACM_circulation_fnc_updateActiveFluidBags;
        [_patient, _part, _iv, _site] call ACME_fnc_resumeSiteFlow;
        _reason = "";
    };
};
if (!_ok) then {
    diag_log format ["[ACME PREPARED ATTACH] rejected request=%1 patient=%2 provider=%3 access=%4/%5/%6 reason=%7; set retained, no carrier committed", _id, netId _patient, netId _medic, _part, _iv, _site, _reason];
};
_results set [_id, [_ok, _doseId, _reason, _fingerprint]];
if (count _results > 128) then {_results deleteAt ((keys _results) select 0);};
_patient setVariable ["ACME_preparedResults", _results, true];
["ACME_preparedAck", [_id, _ok, _doseId, _reason], _medic] call CBA_fnc_targetEvent;
