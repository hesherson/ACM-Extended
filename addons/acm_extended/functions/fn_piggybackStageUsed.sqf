/* Preserve an equipped used bag's line; a bag-only return needs one actual
 * branch line. Stage exact contents, then wait for native prepared custody. */
if (canSuspend) exitWith {private _ok = false; isNil {_ok = _this call ACME_fnc_piggybackStageUsed;}; _ok};
params [["_usedId", "", [""]]];
private _medic = ACE_player;
private _intent = +(missionNamespace getVariable ["ACME_piggybackPending", []]);
private _workflow = missionNamespace getVariable ["ACME_piggybackWorkflowGeneration",0];
if (isNull _medic || {!local _medic} || {!alive _medic} || {_usedId == ""} || {count _intent != 6}) exitWith {false};
_intent params ["_patient", "_part", "_iv", "_site", "_primaryUid", "_epoch"];
if (isNull _patient || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}
    || {_medic getVariable ["ACME_persistenceFrozen", false]} || {_patient getVariable ["ACME_persistenceFrozen", false]}) exitWith {false};
private _current = [missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull],
    missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""],
    missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV", true],
    missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite", -1]];
if ((_intent select [0, 4]) isNotEqualTo _current) exitWith {false};
private _usedBefore = +(_medic getVariable ["ACME_usedBags", []]);
private _matches = _usedBefore select {(_x param [0, ""]) == _usedId};
if (count _matches != 1 || {count (_matches select 0) < 7}) exitWith {false};
private _row = +(_matches select 0);
private _needsLine = (_row param [9, ""]) isEqualTo "bagOnly";
_row params ["", ["_type", ""], ["_remaining", 0], "", ["_bloodType", -1], ["_original", 0], ["_name", ""], ["_freshId", -1]];
if (!(_remaining isEqualType 0) || {!(_original isEqualType 0)} || {!finite _remaining} || {!finite _original}
    || {_remaining <= 1} || {_remaining > _original}
    || {!([_patient, _part, _iv, _site, _type, false] call ACME_fnc_piggybackEligible)}) exitWith {false};
private _bags = (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [toLowerANSI _part, []];
if ((_bags findIf {(_x param [8, ""]) == _primaryUid && {(_x param [3, -1]) == _site}
    && {(_x param [4, true]) isEqualTo _iv}}) < 0) exitWith {false};

private _class = "";
private _action = "";
private _freshMetadata = [];
if (_type == "FreshBlood") then {
    _freshMetadata = _row param [8, []];
    private _validFresh = _freshMetadata isEqualType [] && {_freshId isEqualType 0}
        && {_bloodType isEqualType 0} && {finite _freshId} && {finite _bloodType};
    private _donor = if (_validFresh) then {[_freshId, _freshMetadata, _bloodType] call ACME_fnc_freshBloodResolve} else {[]};
    // Canonical returned blood carries immutable donor facts and no session ID.
    // The legacy action can use ID 0 without rebinding those facts to its seed.
    if (_freshId isEqualTo -1 && {_freshMetadata isNotEqualTo []} && {_donor isNotEqualTo []}) then {_freshId = 0;};
    if (_donor isNotEqualTo [] && {_freshId >= 0} && {_freshId <= 512} && {_freshId == floor _freshId}) then {
        _freshMetadata = ["freshV1", _donor select 3, _donor select 4, _donor select 2];
        private _capacity = if (_original == 250 || {_remaining <= 250 && {_original != 500}}) then {250} else {500};
        if (_remaining <= _capacity) then {
            _class = if (_freshId == 0) then {format ["ACM_FreshBloodBag_%1", _capacity]} else {format ["ACM_FreshBloodBag_%1_%2", _capacity, _freshId]};
            _action = format ["FreshBloodBag_%1_%2", _capacity, _freshId];
            if (!isClass (configFile >> "CfgWeapons" >> _class)) then {_class = "";};
        };
    };
} else {
    private _classes = missionNamespace getVariable ["ACM_circulation_Fluids_Array", []];
    private _actions = missionNamespace getVariable ["ACM_circulation_Fluids_Array_Data", []];
    private _bestVolume = 1e10;
    {
        private _candidate = _x;
        private _candidateAction = _actions param [_forEachIndex, ""];
        private _cfg = configFile >> "ace_medical_treatment" >> "IV" >> _candidateAction;
        private _volume = getNumber (_cfg >> "volume");
        private _donorType = if (isNumber (_cfg >> "bloodtype")) then {getNumber (_cfg >> "bloodtype")} else {-1};
        if (_candidateAction != "" && {isClass (configFile >> "CfgWeapons" >> _candidate)}
            && {(getText (_cfg >> "type")) == _type} && {finite _volume} && {_volume >= _remaining}
            && {_type != "Blood" || {_donorType == _bloodType}}
            && {_volume == _original || {_bestVolume != _original && {_volume < _bestVolume}}}) then {
            _class = _candidate; _action = _candidateAction; _bestVolume = _volume;
        };
    } forEach _classes;
};
if (_class == "" || {_action == ""}) exitWith {
    [_medic, "That used fluid has no matching bag definition or donor metadata. Its contents were kept."] call ACME_fnc_clinicalNotice;
    false
};
private _lineReceipt = [];
if (_needsLine) then {
    _lineReceipt = [_medic, _patient, ["ACME_IVLine"]] call ACME_fnc_treatmentSupplyTake;
};
if (_needsLine && {_lineReceipt isEqualTo []}) exitWith {
    [_medic, "A secondary bag needs one IV line. The used bag was kept."] call ACME_fnc_clinicalNotice;
    false
};
private _setsBefore = +(_medic getVariable ["ACME_preparedIVSets", []]);
private _serial = (missionNamespace getVariable ["ACME_preparedItemSerial", 0]) + 1;
missionNamespace setVariable ["ACME_preparedItemSerial", _serial];
private _id = format ["used-pib:%1:%2:%3", clientOwner, netId _medic, _serial];
private _kind = if (_type in ["Blood", "FreshBlood"]) then {"blood"} else {if (_type == "Saline") then {"saline"} else {"premixed"}};
private _set = [_id, _class, _action, "", "", "", format ["%1 (%2 mL) [Used]", _name, round _remaining], false, _kind, _remaining, 0, _freshMetadata];
private _setsAfter = +_setsBefore; _setsAfter pushBack _set;
private _usedAfter = _usedBefore select {(_x param [0, ""]) != _usedId};
_medic setVariable ["ACME_preparedIVSets", _setsAfter, true];
_medic setVariable ["ACME_usedBags", _usedAfter, true];
private _committed = [_medic] call ACME_fnc_preparedInventoryCommit;
if (isNil "_committed" || {!_committed}) exitWith {
    _medic setVariable ["ACME_preparedIVSets", _setsBefore, true];
    _medic setVariable ["ACME_usedBags", _usedBefore, true];
    if (_lineReceipt isNotEqualTo []) then {[_lineReceipt] call ACME_fnc_treatmentSupplyRefund;};
    [_medic, "The used bag could not be staged. Its exact contents were kept."] call ACME_fnc_clinicalNotice;
    false
};
if (_lineReceipt isNotEqualTo []) then {[_lineReceipt, false] call ACME_fnc_treatmentSupplyRefund;};
uiNamespace setVariable ["ACME_usedRowSig", "__force__"];
uiNamespace setVariable ["ACME_preparedRowSig", "__force__"];
private _contextValid = {
    params ["_medic", "_intent", "_kit", "_locality", "_workflow"];
    private _patient = _intent select 0;
    private _primaryLive = !isNull _patient && {
        (((_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [toLowerANSI (_intent select 1), []]) findIf {
            (_x param [8, ""]) == (_intent select 4) && {(_x param [3, -1]) == (_intent select 3)}
                && {(_x param [4, true]) isEqualTo (_intent select 2)}
        }) >= 0
    };
    !isNull _medic && {local _medic} && {alive _medic} && {_medic isEqualTo ACE_player}
        && {(_medic getVariable ["ACME_equipmentKitEpoch", 0]) == _kit}
        && {(_medic getVariable ["ACME_providerLocalityEpoch", 0]) == _locality}
        && {!(_medic getVariable ["ACME_persistenceFrozen", false])}
        && {(missionNamespace getVariable ["ACME_piggybackPending", []]) isEqualTo _intent}
        && {(missionNamespace getVariable ["ACME_piggybackWorkflowGeneration",0]) == _workflow}
        && {_primaryLive} && {!(_patient getVariable ["ACME_persistenceFrozen", false])}
        && {(_intent select 5) == ([_intent select 0] call ACME_fnc_clinicalEpoch)}
        && {(_intent select [0, 4]) isEqualTo [missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull],
            missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""],
            missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV", true],
            missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite", -1]]}
};
private _waitArgs = [_medic, _intent, _id, _medic getVariable ["ACME_equipmentKitEpoch", 0], _medic getVariable ["ACME_providerLocalityEpoch", 0], _workflow, _contextValid];
[
    {
        params ["_medic", "_intent", "_id", "_kit", "_locality", "_workflow", "_valid"];
        !([_medic, _intent, _kit, _locality, _workflow] call _valid) || {[_medic, "prepared", _id] call ACME_fnc_inventoryLedgerPossessed}
    },
    {
        params ["_medic", "_intent", "_id", "_kit", "_locality", "_workflow", "_valid"];
        if ([_medic, _intent, _kit, _locality, _workflow] call _valid
            && {[_medic, "prepared", _id] call ACME_fnc_inventoryLedgerPossessed}) then {
            [_id] call ACME_fnc_piggybackAttachRequest;
        };
    },
    _waitArgs,
    10,
    {
        params ["_medic"];
        if (!isNull _medic && {local _medic}) then {
            [_medic, "The used bag remains in Prepared IV Sets while its inventory receipt is pending."] call ACME_fnc_clinicalNotice;
        };
    }
] call CBA_fnc_waitUntilAndExecute;
call ACME_fnc_updateTransfusionControls;
true
