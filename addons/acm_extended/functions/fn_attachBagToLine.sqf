/* Convert only the selected fluid into custody, then reuse the certified
 * prepared-set hang. The already-installed IV line is not charged again. */
if (canSuspend) exitWith {private _ok = false; isNil {_ok = _this call ACME_fnc_attachBagToLine;}; _ok};
params ["_class", "_action", "_expectedUID", ["_fromCooler", false]];
private _medic = ACE_player;
if (isNull _medic || {!local _medic} || {!alive _medic}
    || {_medic getVariable ["ACE_isUnconscious", false]}
    || {_medic getVariable ["ACME_persistenceFrozen", false]}
    || {(_medic getVariable ["ACME_lineBagPending", []]) isNotEqualTo []}) exitWith {false};
private _context = call ACME_fnc_getSelectedIVLineContext;
if (count _context != 6) exitWith {false};
_context params ["_patient", "_part", "_iv", "_site", "_uid", "_epoch"];
if (_uid != _expectedUID || {_patient getVariable ["ACME_persistenceFrozen", false]}
    || {([_patient, _part, _iv, _site, _uid] call ACME_fnc_ivLineSlot) isEqualTo []}) exitWith {false};

private _freshParts = _action splitString "_";
private _fresh = (_freshParts param [0, ""]) == "FreshBloodBag";
private _cfg = configFile >> "ace_medical_treatment" >> "IV" >> _action;
private _type = if (_fresh) then {"FreshBlood"} else {getText (_cfg >> "type")};
private _volume = if (_fresh) then {parseNumber (_freshParts param [1, "0"])} else {getNumber (_cfg >> "volume")};
private _premixed = toLowerANSI _type in keys (missionNamespace getVariable ["ACME_infusion_premixedByType", createHashMap]);
if (_class == "" || {_type == ""} || {_volume <= 0}
    || {_type in ["FBTK", "ACME_Propofol", "ACME_SalineY", "ACME_Empty", "ACME_EmptySaline"]}
    || {_premixed}) exitWith {
    [_medic, "Select an ordinary fluid bag for this line. Prepare medication infusions separately."] call ACME_fnc_clinicalNotice;
    false
};
private _fa = missionNamespace getVariable ["ACM_circulation_Fluids_Array", []];
private _fad = missionNamespace getVariable ["ACM_circulation_Fluids_Array_Data", []];
private _fi = _fa find _class;
private _pairValid = _fi >= 0 && {(_fad param [_fi, ""]) == _action};
private _portableFresh = [];
if (_fresh) then {
    private _id = parseNumber (_freshParts param [2, "-1"]);
    private _freshClass = if (_id == 0) then {format ["ACM_FreshBloodBag_%1", _volume]}
        else {format ["ACM_FreshBloodBag_%1_%2", _volume, _id]};
    _pairValid = count _freshParts == 3 && {_volume in [250, 500]} && {_id >= 0}
        && {_id <= 512} && {str _volume == (_freshParts select 1)} && {str _id == (_freshParts select 2)}
        && {_class == _freshClass};
    private _entry = [_id] call ACME_fnc_freshBloodResolve;
    if (_entry isNotEqualTo []) then {_portableFresh = ["freshV1", _entry select 3, _entry select 4, _entry select 2];};
    _pairValid = _pairValid && {_portableFresh isNotEqualTo []};
};
if (!_pairValid) exitWith {
    [_medic, "The selected fluid or donor data is no longer available. The bag was not consumed."] call ACME_fnc_clinicalNotice;
    false
};
private _serial = (missionNamespace getVariable ["ACME_preparedItemSerial", 0]) + 1;
missionNamespace setVariable ["ACME_preparedItemSerial", _serial];
private _sid = format ["set:%1:%2:%3", clientOwner, netId _medic, _serial];
private _name = getText (configFile >> "CfgWeapons" >> _class >> "displayName");
if (_name == "") then {_name = _class;};
// This carried product contains a bag, never another administration set. A
// delayed/refused connection can only use a separately installed line later.
private _set = [_sid, _class, _action, "", "", "", _name, _fromCooler, "bagOnly", _volume, 0, _portableFresh];
if ((["prepared", [_sid, _set, []]] call ACME_fnc_inventoryLedgerClass) == "") exitWith {
    [_medic, "This bag cannot be stored without changing its inventory weight. The bag was not consumed."] call ACME_fnc_clinicalNotice;
    false
};
private _mode = if (_fromCooler) then {0} else {missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_Inventory", 0]};
private _receipt = [_medic, _patient, _class, _mode, objectParent _medic] call ACME_fnc_transfusionTakeSelected;
if (_receipt isEqualTo []) exitWith {
    [_medic, "The selected bag is no longer in that inventory."] call ACME_fnc_clinicalNotice;
    false
};
private _sets = +(_medic getVariable ["ACME_preparedIVSets", []]);
_sets pushBack _set;
_medic setVariable ["ACME_preparedIVSets", _sets, true];
// The native debit now funds this one durable preparation. Never refund it in
// addition to returning the prepared carrier after an owner-side refusal.
[_receipt, false] call ACME_fnc_treatmentSupplyRefund;
private _kit = _medic getVariable ["ACME_equipmentKitEpoch", 0];
private _locality = _medic getVariable ["ACME_providerLocalityEpoch", 0];
private _deadline = diag_tickTime + 15;
_medic setVariable ["ACME_lineBagPending", [_sid, _patient, _uid, _deadline]];
[_medic] call ACME_fnc_preparedInventoryCommit;
uiNamespace setVariable ["ACME_preparedRowSig", "__force__"];
[_medic, "Connecting bag to the installed IV line..."] call ACME_fnc_clinicalNotice;

private _args = [_medic, _context, _sid, _kit, _locality, _deadline];
[
    {
        params ["_m", "_captured", "_sid", "_kit", "_locality", "_deadline"];
        isNull _m || {!local _m} || {!alive _m} || {diag_tickTime >= _deadline}
            || {_m getVariable ["ACME_persistenceFrozen", false]}
            || {(_captured select 0) getVariable ["ACME_persistenceFrozen", false]}
            || {(_m getVariable ["ACME_equipmentKitEpoch", 0]) != _kit}
            || {(_m getVariable ["ACME_providerLocalityEpoch", 0]) != _locality}
            || {(call ACME_fnc_getSelectedIVLineContext) isNotEqualTo _captured}
            || {[_m, "prepared", _sid] call ACME_fnc_inventoryLedgerPossessed}
    },
    {
        params ["_m", "_captured", "_sid", "_kit", "_locality", "_deadline"];
        if (isNull _m) exitWith {};
        if (!local _m) exitWith {
            // This is origin-client presentation state, never a public or
            // patient-owned mutation. Do not leave it latched on a later return.
            private _pending = _m getVariable ["ACME_lineBagPending", []];
            if ((_pending param [0, ""]) == _sid) then {_m setVariable ["ACME_lineBagPending", []];};
        };
        private _same = alive _m && {diag_tickTime < _deadline}
            && {!(_m getVariable ["ACME_persistenceFrozen", false])}
            && {!((_captured select 0) getVariable ["ACME_persistenceFrozen", false])}
            && {(_m getVariable ["ACME_equipmentKitEpoch", 0]) == _kit}
            && {(_m getVariable ["ACME_providerLocalityEpoch", 0]) == _locality}
            && {(call ACME_fnc_getSelectedIVLineContext) isEqualTo _captured}
            && {[_m, "prepared", _sid] call ACME_fnc_inventoryLedgerPossessed};
        private _started = false;
        if (_same) then {
            private _result = [_sid, _captured select 4] call ACME_fnc_hangPreparedSet;
            _started = !isNil "_result" && {_result isEqualType true} && {_result};
        };
        if (!_started) then {
            private _pending = _m getVariable ["ACME_lineBagPending", []];
            if ((_pending param [0, ""]) == _sid) then {_m setVariable ["ACME_lineBagPending", []];};
            [_m, "The line or selection changed. The bag remains in Prepared IV Sets."] call ACME_fnc_clinicalNotice;
        };
    },
    _args
] call CBA_fnc_waitUntilAndExecute;
// Presentation busy state is bounded. Certified prepared-hang intents retain
// their own recovery and save fences if an acknowledgement is delayed longer.
[{
    params ["_m", "_sid"];
    if (!isNull _m) then {
        private _pending = _m getVariable ["ACME_lineBagPending", []];
        if ((_pending param [0, ""]) == _sid) then {_m setVariable ["ACME_lineBagPending", []];};
    };
}, [_medic, _sid], 15] call CBA_fnc_waitAndExecute;
true
