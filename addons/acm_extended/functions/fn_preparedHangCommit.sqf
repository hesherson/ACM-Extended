/* Owner-authoritative prepared IV-set hang transaction.
 * The medic owns the prepared-set inventory, but the casualty owner owns the access topology and IV_Bags.  The
 * casualty owner therefore validates the live set/access, performs the attach, then removes only the successfully
 * consumed set from the medic's replicated prepared-set list.
 */
params [
    ["_patient", objNull, [objNull]],
    ["_medic", objNull, [objNull]],
    ["_requestId", "", [""]],
    ["_setId", "", [""]],
    ["_part", "", [""]],
    ["_iv", true, [true]],
    ["_site", -1, [0]],
    ["_epoch", -1, [0]],
    ["_warmer", false, [false]],
    ["_freshEntryNet", [], [[]]]
];
if (isNull _patient || {_requestId == ""} || {_setId == ""}) exitWith {};
if (!local _patient) exitWith {[_patient, "preparedHang", _this] call ACME_fnc_ownerDispatch;};

private _results = _patient getVariable ["ACME_preparedHangResults", createHashMap];
private _old = _results getOrDefault [_requestId, []];
if !(_old isEqualTo []) exitWith {
    ["ACME_preparedHangResult", [_requestId, _old param [0, false], _old param [1, ""]], _medic] call CBA_fnc_targetEvent;
};

private _finish = {
    params ["_ok", "_message"];
    _results set [_requestId, [_ok, _message]];
    if (count _results > 128) then {_results deleteAt ((keys _results) select 0);};
    _patient setVariable ["ACME_preparedHangResults", _results, true];
    if (!isNull _medic) then {["ACME_preparedHangResult", [_requestId, _ok, _message], _medic] call CBA_fnc_targetEvent;};
};

if (isNull _medic || {!alive _medic}) exitWith {[false, "Provider is no longer available. The prepared set was not consumed."] call _finish;};
if (_epoch != ([_patient] call ACME_fnc_clinicalEpoch)) exitWith {[false, "Patient state changed. The prepared set was not consumed."] call _finish;};
private _sameVehicle = !isNull objectParent _medic && {(objectParent _medic) isEqualTo (objectParent _patient)};
if ((_medic distance _patient) > 5 && {!_sameVehicle}) exitWith {[false, "Move back within treatment range. The prepared set was not consumed."] call _finish;};
if !([_patient, _part, _iv, _site] call ACME_fnc_transfusionAccessValid) exitWith {[false, "The selected IV/IO is no longer available. The prepared set was not consumed."] call _finish;};

private _sets = +(_medic getVariable ["ACME_preparedIVSets", []]);
private _setIdx = _sets findIf {(_x param [0, ""]) isEqualTo _setId};
if (_setIdx < 0) exitWith {[false, "That prepared set is no longer available."] call _finish;};
private _rec = +(_sets select _setIdx);
_rec params [
    ["_id", ""], ["_bloodClass", ""], ["_bloodAction", ""], ["_salineClass", ""], ["_salineAction", ""],
    ["_tied", ""], ["_label", ""], ["_bloodCold", false], ["_kind", "yset"],
    ["_bloodExactVol", 0], ["_salineExactVol", 0]
];
private _isSingle = _kind != "yset";
if (_tied != "" && {_tied != netId _patient}) exitWith {[false, "This set is tied to a different casualty."] call _finish;};

// Re-resolve treatment actions on the owner so a stale UI row cannot force an obsolete action string.
private _fa = missionNamespace getVariable ["ACM_circulation_Fluids_Array", []];
private _fad = missionNamespace getVariable ["ACM_circulation_Fluids_Array_Data", []];
private _bi = _fa find _bloodClass;
if (_bi >= 0) then {_bloodAction = _fad param [_bi, _bloodAction];};
if (!_isSingle) then {
    private _si = _fa find _salineClass;
    if (_si >= 0) then {_salineAction = _fad param [_si, _salineAction];};
};
if (_bloodAction == "" || {!_isSingle && {_salineAction == ""}}) exitWith {[false, "The staged fluid definition is no longer valid. Rebuild the set."] call _finish;};

private _lineKey = format ["%1#%2#%3", _part, _iv, _site];
private _lineKeyLower = toLowerANSI _lineKey;
private _lineYd = _lineKeyLower in ((_patient getVariable ["ACME_YLines", []]) apply {toLowerANSI _x});
private _map = _patient getVariable ["ACM_circulation_IV_Bags", createHashMap];
private _arr = +(_map getOrDefault [_part, []]);
private _activeBlood = (_arr findIf {
    ((_x param [3, -1]) isEqualTo _site) && {(_x param [4, true]) isEqualTo _iv}
        && {(_x param [0, ""]) in ["Blood", "FreshBlood"]} && {(_x param [1, 0]) > 0.01}
}) >= 0;
private _activeOther = (_arr findIf {
    ((_x param [3, -1]) isEqualTo _site) && {(_x param [4, true]) isEqualTo _iv}
        && {!((_x param [0, ""]) in ["ACME_SalineY", "ACME_Empty", "ACME_EmptySaline"])} && {(_x param [1, 0]) > 0.01}
}) >= 0;
private _dirty = (_patient getVariable ["ACME_YLineDirty", createHashMap]) getOrDefault [_lineKeyLower, false];
private _refuse = "";
if (!_isSingle) then {
    if (_lineYd) then {_refuse = "This IV spot already has a Y line.";};
    if (_refuse == "" && {_activeOther}) then {_refuse = "This IV/IO already has a line running.";};
} else {
    if (_lineYd) then {
        if (_kind != "blood") then {_refuse = "This IV spot already has a Y line.";}
        else {
            if (_activeBlood) then {_refuse = "A unit is still running on this Y line.";};
            if (_refuse == "" && {_dirty}) then {_refuse = "Flush the Y line before hanging the next unit.";};
        };
    } else {
        if (_activeOther) then {_refuse = "This IV/IO already has a line running.";};
    };
};
if (_refuse != "") exitWith {[false, _refuse + " The prepared set was not consumed."] call _finish;};

private _pi = ACME_infusion_bodyParts find toLowerANSI _part;
private _access = if (_pi >= 0) then {[_patient, _iv, _pi, _site] call ACM_circulation_fnc_getAccessType} else {0};
if (_access <= 0) exitWith {[false, "The selected access is no longer established. The prepared set was not consumed."] call _finish;};

private _attach = {
    params ["_action", ["_freshNet", [], [[]]]];
    private _parts = _action splitString "_";
    private _fresh = (_parts param [0, ""]) isEqualTo "FreshBloodBag";
    private _entry = [];
    if (_fresh) then {
        private _fid = parseNumber (_parts param [2, "-1"]);
        if (_freshNet isEqualType [] && {count _freshNet >= 3}) then {_entry = +_freshNet;}
        else {if (_fid >= 0) then {_entry = [_fid] call ACM_circulation_fnc_getFreshBloodEntry;};};
    };
    [_patient, _part, _action, _access, _iv, _site, _fresh, false, _entry] call ace_medical_treatment_fnc_ivBagLocal
};

private _created = [];
private _bloodUid = [_bloodAction, _freshEntryNet] call _attach;
if (_bloodUid == "") exitWith {[false, "The blood/fluid bag could not be attached. The prepared set was not consumed."] call _finish;};
_created pushBack _bloodUid;
private _salineUid = "";
if (!_isSingle) then {
    _salineUid = [_salineAction, []] call _attach;
    if (_salineUid != "") then {_created pushBack _salineUid;};
};

if (!_isSingle && {_salineUid == ""}) exitWith {
    // Roll back the first limb if the second limb could not be created.
    private _rollbackMap = _patient getVariable ["ACM_circulation_IV_Bags", createHashMap];
    private _rollback = +(_rollbackMap getOrDefault [_part, []]);
    _rollback = _rollback select {!((_x param [8, ""]) in _created)};
    _rollbackMap set [_part, _rollback];
    [_patient, _rollbackMap, true] call ACME_fnc_ivBagsCommit;
    [_patient, _part] call ACM_circulation_fnc_updateActiveFluidBags;
    [false, "The Y set could not be completed. The prepared set was not consumed."] call _finish;
};

// Remove spent placeholders only after the owner has successfully created the replacement bag(s), then apply exact
// pulled-bag volumes and the Y-line saline clamp against bag UIDs rather than array positions.
_map = _patient getVariable ["ACM_circulation_IV_Bags", createHashMap];
_arr = +(_map getOrDefault [_part, []]);
if (_isSingle) then {
    _arr = _arr select {
        !( ((_x param [0, ""]) in ["ACME_Empty", "ACME_EmptySaline"])
            && {(_x param [3, -1]) isEqualTo _site} && {(_x param [4, true]) isEqualTo _iv} )
    };
};
{
    private _uid = _x param [8, ""];
    if (_uid == _bloodUid && {_bloodExactVol > 0}) then {
        private _e = +_x;
        if ((_e param [1, 0]) > _bloodExactVol) then {_e set [1, _bloodExactVol];};
        _arr set [_forEachIndex, _e];
    };
    if (!_isSingle && {_uid == _salineUid}) then {
        private _e = +(_arr select _forEachIndex);
        _e set [0, "ACME_SalineY"];
        if (_salineExactVol > 0 && {(_e param [1, 0]) > _salineExactVol}) then {_e set [1, _salineExactVol];};
        _arr set [_forEachIndex, _e];
    };
} forEach +_arr;
_map set [_part, _arr];
[_patient, _map, true] call ACME_fnc_ivBagsCommit;

if (!_isSingle) then {
    private _yl = +(_patient getVariable ["ACME_YLines", []]);
    _yl pushBackUnique _lineKey;
    [_patient, _yl, true] call ACME_fnc_yLinesCommit;
};
[_patient, _part, _iv, _site] call ACME_fnc_resumeSiteFlow;

if (_kind == "blood" || {!_isSingle}) then {
    if (_warmer) then {
        [_patient, true, false, objNull, CBA_missionTime + 15, true] call ACME_fnc_bloodThermalStateCommit;
    } else {
        if (_bloodCold) then {[_patient, false, true, CBA_missionTime, CBA_missionTime + 15, true] call ACME_fnc_bloodThermalStateCommit;};
    };
};

// Consumption happens last.  Remove by stable ID from the medic's current live list so any newly prepared set is
// preserved even if it was created while this network transaction was in flight.
_sets = +(_medic getVariable ["ACME_preparedIVSets", []]);
_sets = _sets select {(_x param [0, ""]) != _setId};
_medic setVariable ["ACME_preparedIVSets", _sets, true];

if (!isNil "ace_medical_treatment_fnc_addToTriageCard") then {
    [_patient, _bloodClass] call ace_medical_treatment_fnc_addToTriageCard;
    if (!_isSingle) then {[_patient, _salineClass] call ace_medical_treatment_fnc_addToTriageCard;};
};
if (!isNil "ace_medical_treatment_fnc_addToLog") then {
    [_patient, "activity", "%1 connected prepared IV set: %2", [[_medic, false, true] call ace_common_fnc_getName, _label]] call ace_medical_treatment_fnc_addToLog;
};
[true, format ["Connected %1", _label]] call _finish;
