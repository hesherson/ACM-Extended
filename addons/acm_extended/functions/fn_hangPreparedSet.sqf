// "Hang Set": hang the selected stored prepared iv set onto the current access site. it is routed here from
// fn_transfusionspikeoradd when the prepared iv sets list mode is active and the spike button, relabeled "Hang
// Set", is pressed. this is the one hang and refill path in the menu, because there is no add bag.
// there are two kinds of set.
// "yset" is blood plus clamped saline, hung as a y line through the shared fn_ylineattach.
// "blood", "saline" and "premixed" are a single spiked bag, hung on its own.
// one line per access site is enforced here.
// a fresh site hangs.
// an empty slot on this line, from a spent unit, refills: drop the empty marker and hang the new bag. for a y line
// only a blood refill is allowed, and the clamped saline reserve stays.
// a unit still running on this site refuses.
// a set is single-use, so hanging it consumes it.
private _display = findDisplay 86000;
if (isNull _display) exitWith {};

private _setList = _display displayCtrl 86145;
private _row = if (!isNull _setList) then { lbCurSel _setList } else { -1 };
private _setId = if (_row >= 0) then { _setList lbData _row } else { "" };
if (_setId isEqualTo "") exitWith {
    ["Select a prepared IV set first.", 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

private _sets = ACE_player getVariable ["ACME_preparedIVSets", []];
private _setIdx = _sets findIf { (_x param [0, ""]) isEqualTo _setId };
if (_setIdx < 0) exitWith {
    ["That prepared set is no longer available.", 3, ACE_player, 13] call ace_common_fnc_displayTextStructured;
    uiNamespace setVariable ["ACME_preparedRowSig", "__force__"];
};
private _rec = _sets select _setIdx;
_rec params [["_id", ""], ["_bloodClass", ""], ["_bloodAction", ""], ["_salineClass", ""], ["_salineAction", ""], ["_tied", ""], ["_label", ""], ["_bloodCold", false], ["_kind", "yset"], ["_bloodExactVol", 0], ["_salineExactVol", 0]];
private _isSingle = (_kind != "yset");

private _target = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];
if (isNull _target) exitWith {
    ["No casualty selected.", 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};
private _bodyPart = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""];
private _iv       = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV", true];
private _site     = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite", -1];
if !([_target,_bodyPart,_iv,_site] call ACME_fnc_transfusionAccessValid) exitWith {
    ["Establish and select an IV/IO before hanging this set.",2.5,ACE_player,13] call ace_common_fnc_displayTextStructured;
};
private _lineKey  = format ["%1#%2#%3", _bodyPart, _iv, _site];

// a set that came off a patient, through remove-to-list, is tied to that patient. untied sets hang on anyone.
if (_tied != "" && {_tied != (netId _target)}) exitWith {
    ["This set was pulled from a different casualty and cannot be reused here.", 4, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

// re-derive the hang actions from the current fluid tables by class, with the stored action as the fallback. it is
// deterministic for cooler blood and for standard saline and carriers, and the fallback covers a class not
// momentarily listed.
private _fa  = missionNamespace getVariable ["ACM_circulation_Fluids_Array", []];
private _fad = missionNamespace getVariable ["ACM_circulation_Fluids_Array_Data", []];
private _bi = _fa find _bloodClass;
if (_bi >= 0) then { _bloodAction = _fad param [_bi, _bloodAction]; };
if (!_isSingle) then {
    private _si = _fa find _salineClass;
    if (_si >= 0) then { _salineAction = _fad param [_si, _salineAction]; };
};
if (_bloodAction isEqualTo "") exitWith {
    ["Cannot reconstruct this set's contents. Rebuild it.", 3.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};
if (!_isSingle && {_salineAction isEqualTo ""}) exitWith {
    ["Cannot reconstruct this set's contents. Rebuild it.", 3.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

// the site state, for the one-line-per-site rule.
private _lineYd = _lineKey in (_target getVariable ["ACME_YLines", []]);
private _siteBags = (_target getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [_bodyPart, []];
private _activeBlood = (_siteBags findIf {
    ((_x param [3, -1]) isEqualTo _site) && {(_x param [4, true]) isEqualTo _iv} &&
    {((_x param [0, ""]) in ["Blood", "FreshBlood"])} && {(_x param [1, 0]) > 0.01}
}) > -1;
private _activeOther = (_siteBags findIf {
    ((_x param [3, -1]) isEqualTo _site) && {(_x param [4, true]) isEqualTo _iv} &&
    {!((_x param [0, ""]) in ["ACME_SalineY", "ACME_Empty", "ACME_EmptySaline"])} && {(_x param [1, 0]) > 0.01}
}) > -1;
private _dirty = (_target getVariable ["ACME_YLineDirty", createHashMap]) getOrDefault [toLower (format ["%1#%2#%3", _bodyPart, _iv, _site]), false];

// the one-line-per-site gate. it computes a refusal message, then exits once at the top level, so no nested
// exitwith is needed.
private _refuse = "";
if (!_isSingle) then {
    // a y set needs a clear site: no existing y line and no running single line.
    if (_lineYd) then { _refuse = "This IV spot already has a Y line."; };
    if (_refuse == "" && _activeOther) then { _refuse = "This IV/IO already has a line running."; };
} else {
    if (_lineYd) then {
        // an existing y line: only a blood unit can refill it, because the clamped saline reserve stays.
        if (_kind != "blood") then { _refuse = "This IV spot already has a Y line."; }
        else {
            if (_activeBlood) then { _refuse = "A unit is still running on this Y line."; };
            if (_refuse == "" && _dirty) then { _refuse = "Flush the line (Flush Line) before hanging the next unit."; };
        };
    } else {
        // a non-y site: refuse only if a unit is actively running. an empty slot or a fresh site is fine to hang on.
        if (_activeOther) then { _refuse = "This IV/IO already has a line running."; };
    };
};
if (_refuse != "") exitWith {
    [_refuse, 4, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};


private _prepared = ACE_player getVariable ["ACME_infusion_PreparedBags", []];
private _custom = _prepared findIf {(_x param [0, ""]) == _id};
if (_custom >= 0) exitWith {
    missionNamespace setVariable ["ACME_infusion_SelectedPreparedIndex", _custom];
    private _l = _display displayCtrl 86130;
    // GivePreparedBag accepts this stable set ID independently of list selection.
    [_id] call ACME_fnc_givePreparedBag;
};

// Premixed medication must be clamped and acknowledged before its setup dialog opens.
private _singleType = getText (configFile >> "ace_medical_treatment" >> "IV" >> _bloodAction >> "type");
private _medicatedPremix = (toLowerANSI _singleType) in keys (missionNamespace getVariable ["ACME_infusion_premixedByType", createHashMap]);
if (_isSingle && {_medicatedPremix}) exitWith {
    [_rec, _target, _bodyPart, _iv, _site, _bloodAction] call ACME_fnc_givePremixedSet;
};

// The actual hang is a casualty-owner transaction.  The local checks above are only fast feedback; the owner
// repeats the access/occupancy checks against the latest IV_Bags state and consumes the prepared set only after a
// successful attach.  This closes the MP race where two providers could both see an empty site and where a set
// could be deleted locally just before the patient changed locality or the access disappeared.
private _pending = missionNamespace getVariable ["ACME_preparedHangPending", createHashMap];
if (((values _pending) findIf {
    private _r = _x;
    !(_r param [3, false]) && {(((_r param [1, []]) param [3, ""]) isEqualTo _id)}
}) >= 0) exitWith {
    ["That prepared set is already being connected.", 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

private _freshEntry = [];
private _ap = _bloodAction splitString "_";
if ((_ap param [0, ""]) isEqualTo "FreshBloodBag") then {
    private _freshId = parseNumber (_ap param [2, "-1"]);
    if (_freshId >= 0) then {_freshEntry = [_freshId] call ACM_circulation_fnc_getFreshBloodEntry;};
};
private _epoch = [_target] call ACME_fnc_clinicalEpoch;
private _serial = (missionNamespace getVariable ["ACME_preparedHangSerial", 0]) + 1;
missionNamespace setVariable ["ACME_preparedHangSerial", _serial];
private _requestId = format ["preparedHang:%1:%2:%3", clientOwner, _serial, floor (diag_tickTime * 1000)];
private _warmer = ([ACE_player, _target, "ACME_BloodWarmer"] call ACME_fnc_treatmentSupplyCount) >= 1;
private _args = [_target, ACE_player, _requestId, _id, _bodyPart, _iv, _site, _epoch, _warmer, _freshEntry];
_pending set [_requestId, [_target, _args, CBA_missionTime, false]];
missionNamespace setVariable ["ACME_preparedHangPending", _pending];

["Connecting prepared set...", 2.5, ACE_player] call ace_common_fnc_displayTextStructured;
[_target, "preparedHang", _args] call ACME_fnc_ownerDispatch;
