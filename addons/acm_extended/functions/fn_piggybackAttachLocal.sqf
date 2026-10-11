/* Owner-authoritative, non-suspending physical secondary attach. Stock is already in provider escrow.
   The receipt and both UID endpoints publish before ACK; another request cannot debit that set twice. */
if (canSuspend) exitWith {isNil {_this call ACME_fnc_piggybackAttachLocal;};};
params ["_medic","_patient","_id","_setId","_part","_iv","_site","_primaryUid","_epoch","_set","_prepared","_issued"];
if (isNull _patient || {isNull _medic} || {_id == ""} || {_setId == ""}) exitWith {false};
if (!local _patient) exitWith {[_patient,"piggybackAttach",_this] call ACME_fnc_ownerDispatch;false};
_part = toLowerANSI _part;
private _fingerprint = [_medic,_setId,_part,_iv,_site,_primaryUid,_epoch,+_set,+_prepared,_issued];
private _results = _patient getVariable ["ACME_piggybackResults",createHashMap];
private _previous = _results getOrDefault [_id,[]];
if !(_previous isEqualTo []) exitWith {
    if ((_previous param [4,[]]) isEqualTo _fingerprint) then {
        ["ACME_piggybackAttachAck",[_patient,_id,_setId,_previous select 0,_previous select 1,_previous select 2,_medic],_medic] call CBA_fnc_targetEvent;
    };
    _previous select 0
};
// Exact replicated escrow is the custody proof after owner transfer; age alone never refunds a bag.
if (!(_issued isEqualType 0) || {!finite _issued} || {_issued > serverTime + 2}) exitWith {false};
private _reply = {
    params ["_ok","_message",["_doseId",""]];
    _results set [_id,[_ok,_message,_doseId,_issued,_fingerprint]];
    // Keep every terminal decision for the entire request acceptance window.
    {
        private _record = _results get _x;
        private _fp = _record param [4,[]];
        private _provider = _fp param [0,objNull];
        private _sourceId = _fp param [1,""];
        private _reservation = if (isNull _provider) then {[]} else {(_provider getVariable ["ACME_piggybackEscrow",createHashMap]) getOrDefault [_sourceId,[]]};
        private _outstanding = !(_reservation isEqualTo []) && {(_reservation param [0,""]) == _x};
        if (!_outstanding && {serverTime - (_record param [3,serverTime]) > 180}) then {_results deleteAt _x;};
    } forEach keys _results;
    [_patient,"ACME_piggybackResults",_results,true] call ACME_fnc_setVarNet;
    ["ACME_piggybackAttachAck",[_patient,_id,_setId,_ok,_message,_doseId,_medic],_medic] call CBA_fnc_targetEvent;
    _ok
};
private _held = (_medic getVariable ["ACME_piggybackEscrow",createHashMap]) getOrDefault [_setId,[]];
// Escrow publication may arrive after the event. Retry, without changing custody.
if (_held isEqualTo []) exitWith {false};
if !((_held select [0,6]) isEqualTo [_id,_patient,_epoch,_set,_prepared,_issued]) exitWith {[false,"The reserved piggyback bag changed. It was not attached."] call _reply};
if (_epoch != ([_patient] call ACME_fnc_clinicalEpoch)) exitWith {[false,"Patient state changed. The prepared bag was returned."] call _reply};
private _sameVehicle = !isNull objectParent _medic && {objectParent _medic isEqualTo objectParent _patient};
if (!alive _patient || {!alive _medic} || {!([_medic] call ace_common_fnc_isAwake)} || {_medic distance _patient > 5 && {!_sameVehicle}}) exitWith {[false,"Provider is unavailable or out of range. The prepared bag was returned."] call _reply};
if ((_set param [0,""]) != _setId || {(_set param [8,"yset"]) in ["yset","blood","propofol"]}
    || {(_set param [5,""]) != "" && {(_set select 5) != netId _patient}}) exitWith {[false,"That set cannot be used as a piggyback."] call _reply};
private _action = _set param [2,""];
private _cfg = configFile >> "ace_medical_treatment" >> "IV" >> _action;
private _type = getText (_cfg >> "type");
private _normalVolume = getNumber (_cfg >> "volume");
if (!isClass _cfg || {!finite _normalVolume} || {_normalVolume <= 1}) exitWith {[false,"The selected fluid definition is unavailable. The bag was returned."] call _reply};
private _isInfusion = !(_prepared isEqualTo []);
if !([_patient,_part,_iv,_site,_type,_isInfusion] call ACME_fnc_piggybackEligible) exitWith {[false,"This line changed or cannot accept that piggyback. The prepared bag was returned."] call _reply};
private _beforeMap = _patient getVariable ["ACM_circulation_IV_Bags",createHashMap];
private _beforeBags = +(_beforeMap getOrDefault [_part,[]]);
private _primary = _beforeBags findIf {(_x param [8,""]) == _primaryUid && {(_x param [3,-1]) == _site} && {(_x param [4,true]) == _iv}};
if (_primary < 0) exitWith {[false,"The original primary bag moved or was removed. The prepared bag was returned."] call _reply};
// A second transaction cannot consume the same escrow, even with a new request ID.
if ((values _results findIf {(_x param [0,false]) && {((_x param [4,[]]) param [0,objNull]) isEqualTo _medic} && {((_x param [4,[]]) param [1,""]) == _setId}}) >= 0) exitWith {[false,"This set is already connected."] call _reply};
private _components = if (_isInfusion) then {[_prepared] call ACME_fnc_preparedComponents} else {[]};
private _exactVolume = if (_isInfusion) then {_prepared param [10,0]} else {_set param [9,0]};
if (_exactVolume <= 0 && {!_isInfusion}) then {_exactVolume = _normalVolume;};
if (!finite _exactVolume || {_exactVolume <= 1}) exitWith {[false,"That prepared bag is empty. It was returned."] call _reply};
if (_isInfusion && {(_prepared param [0,""]) != _setId || {(_prepared param [15,""]) != _setId}
    || {(_prepared param [2,""]) != _action} || {_type != "Saline"} || {_components isEqualTo []}
    || {(_components findIf {
        private _class = (missionNamespace getVariable ["ACME_infusion_deliveryClassOverride",createHashMap]) getOrDefault [_x select 0,format["%1_IV",_x select 0]];
        (_x select 0) == "Propofol" || {!finite (_x select 1)} || {(_x select 1) <= 0}
            || {!(isClass(configFile >> "ACM_Medication" >> "Medications" >> _class) || {(_x select 0) in (missionNamespace getVariable ["ACME_infusion_osmoticAgents",[]])})}
    }) >= 0}}) exitWith {[false,"This medication carrier cannot be piggybacked. The prepared bag was returned."] call _reply};
private _pi = ACME_infusion_bodyParts find _part;
private _access = [_patient,_iv,_pi,_site] call ACM_circulation_fnc_getAccessType;
private _beforeMeds = +(_patient getVariable ["ACME_infusion_BagMedications",[]]);
private _beforeActive = _patient getVariable ["ACM_circulation_IV_Bags_Active",false];
[_patient,_part,_action,_access,_iv,_site,false,true] call ace_medical_treatment_fnc_ivBagLocal;
private _created = [_patient,_part,_beforeBags,_type,_normalVolume,_site,_iv,_access] call ACME_fnc_preparedCarrierResolve;
private _ok = !(_created isEqualTo []);
private _doseId = "";
private _secondaryUid = "";
if (_ok) then {
    _created params ["_index","_uid"];
    _secondaryUid = _uid;
    private _map = _patient getVariable ["ACM_circulation_IV_Bags",createHashMap];
    private _bags = +(_map getOrDefault [_part,[]]);
    private _bag = +(_bags select _index);
    _bag set [1,_exactVolume]; _bag set [6,_exactVolume];
    _bags set [_index,_bag]; _map set [_part,_bags];
    [_patient,_map,false] call ACME_fnc_ivBagsCommit;
    if (_isInfusion) then {
        private _context = [_patient,_part,_index,_type,_access,_site,_iv,_bag param [5,-1],_exactVolume,_bag param [7,-1],_exactVolume,_uid];
        {
            _x params ["_med","_dose"];
            private _registered = [_context,_med,_dose,_prepared param [5,600],_prepared param [6,20],0,0,format["%1:%2",_id,_forEachIndex],_uid,_epoch,[],0,true] call ACME_fnc_infusionRegisterLocal;
            if (isNil "_registered" || {!(_registered isEqualType "")} || {_registered == ""}) exitWith {_ok = false;};
            private _recorded = (_patient getVariable ["ACME_infusion_BagMedications",[]]) findIf {
                (_x param [0,""]) == _registered && {(_x param [23,""]) == _uid} && {(_x param [11,""]) == _med}
            };
            if (_recorded < 0) exitWith {_ok = false;};
            if (_doseId == "") then {_doseId = _registered;};
        } forEach _components;
    };
};
if (!_ok) exitWith {
    private _map = _patient getVariable ["ACM_circulation_IV_Bags",createHashMap];
    _map set [_part,_beforeBags];
    [_patient,_beforeMeds] call ACME_fnc_infusionMedicationStateCommit;
    [_patient,_map] call ACME_fnc_ivBagsCommit;
    [_patient,[["ivBagsActive",_beforeActive]],true] call ACM_circulation_fnc_setRuntimeState;
    [_patient,_part] call ACM_circulation_fnc_updateActiveFluidBags;
    [false,"The piggyback could not be connected. The exact prepared bag was returned."] call _reply
};
private _lines = _patient getVariable ["ACME_PiggybackLines",createHashMap];
_lines set [toLowerANSI format["%1#%2#%3",_part,_iv,_site],[_primaryUid,_secondaryUid,_epoch]];
[_patient,_lines] call ACME_fnc_piggybackLinesCommit;
[_patient,_patient getVariable ["ACME_infusion_BagMedications",[]]] call ACME_fnc_infusionMedicationStateCommit;
[_patient,_patient getVariable ["ACM_circulation_IV_Bags",createHashMap]] call ACME_fnc_ivBagsCommit;
[_patient,_part] call ACM_circulation_fnc_updateActiveFluidBags;
[_patient,_part,_iv,_site] call ACME_fnc_resumeSiteFlow;
if (_isInfusion) then {ACME_infusion_activePatients pushBackUnique _patient;};
[_patient,"activity","%1 connected a piggyback secondary",[[_medic,false,true] call ace_common_fnc_getName]] call ace_medical_treatment_fnc_addToLog;
[true,"Piggyback connected. Secondary gravity flow runs first; the primary is held until it empties.",_doseId] call _reply
