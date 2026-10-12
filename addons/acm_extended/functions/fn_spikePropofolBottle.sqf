/* An unopened propofol bottle is its own 50 mL infusion, never a saline admixture.
 * Both physical components are consumed at preparation. The two matching custody
 * records then use the existing prepared-attach owner transaction and clamp ACK.
 */
private _display = findDisplay 86000;
if (isNull _display || {uiNamespace getVariable ["ACME_preparedListMode", false]}) exitWith {};
private _list = _display displayCtrl 86005;
private _row = lbCurSel _list;
if (_row < 0) exitWith {};
private _class = ((_list lbData _row) splitString "|") param [0, ""];
if (_class != "ACM_Vial_Propofol") exitWith {};
if (count (missionNamespace getVariable ["ACME_spikingActive", []]) > 0) exitWith {};

private _medic = ACE_player;
private _patient = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];
private _mode = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_Inventory", 0];
private _vehicle = objectParent _medic;
private _holder = [_medic, _patient, _vehicle] param [_mode, objNull];
if (isNull _holder || {!(_mode in [0,1,2])}) exitWith {};
if (([_medic, _patient, "ACME_IVLine"] call ACME_fnc_treatmentSupplyCount) < 1) exitWith {
    ["You need one IV line to spike this propofol bottle.", 2.5, _medic, 13] call ace_common_fnc_displayTextStructured;
};

// Capture the selected donor before the brief spike animation. The pooled open-vial
// ledger is deliberately not consulted: only this source's unopened physical item
// can become a bottle infusion. A changed selector cannot redirect the later debit.
// Shared patient/vehicle inventory uses the same owner-arbitrated lease as the
// syringe draw path. Two providers cannot spike/draw the same unopened bottle.
private _release = {
    params ["_medic", "_holder", "_token"];
    if (_holder isEqualTo _medic) exitWith {};
    private _accepted = missionNamespace getVariable ["ACME_vialLeaseAccepted", []];
    private _pending = missionNamespace getVariable ["ACME_vialLeasePending", []];
    private _ownsAccepted = (_accepted param [0, objNull]) isEqualTo _holder
        && {(_accepted param [1, ""]) == _token};
    private _ownsPending = (_pending param [0, objNull]) isEqualTo _holder
        && {(_pending param [1, ""]) == _token};
    if (_token != "") then {[_holder, "vialLease", [_medic, "release", _token]] call ACME_fnc_ownerDispatch;};
    // An unrelated Narc Box session may have replaced the local lease while the
    // spike was pending. Release only this captured request, never its new source.
    if (_ownsAccepted) then {
        missionNamespace setVariable ["ACME_vialLeaseAccepted", []];
        missionNamespace setVariable ["ACME_vialLeaseRenewAt", 0];
    };
    if (_ownsPending) then {missionNamespace setVariable ["ACME_vialLeasePending", []];};
};
private _begin = {
    params ["_medic", "_patient", "_mode", "_vehicle", "_holder", "_token", "_release"];
    missionNamespace setVariable ["ACME_spikingActive", ["ACM_Vial_Propofol", diag_tickTime + 1.6]];
    call ACME_fnc_updateTransfusionControls;
    [{
    params ["_medic", "_patient", "_mode", "_vehicle", "_holder", "_token", "_release"];
    missionNamespace setVariable ["ACME_spikingActive", []];
    if (isNull _medic || {!local _medic} || {!alive _medic}
        || {_medic getVariable ["ACE_isUnconscious", false]}
        || {!isNull _patient && {_medic distance _patient > 5}
            && {isNull objectParent _medic || {objectParent _medic != objectParent _patient}}}) exitWith {
        [_medic, _holder, _token] call _release;
    };
    private _acceptedLease = missionNamespace getVariable ["ACME_vialLeaseAccepted", []];
    private _leaseValid = _holder isEqualTo _medic || {
        (_acceptedLease param [0, objNull]) isEqualTo _holder
            && {(_acceptedLease param [1, ""]) == _token}
            && {(_acceptedLease param [2, 0]) > serverTime}
    };
    if (!_leaseValid) exitWith {
        [_medic, _holder, _token] call _release;
        ["The shared medication source changed. Select the bottle and spike it again.", 2.5, _medic, 13] call ace_common_fnc_displayTextStructured;
    };
    private _preparedIndex = -1;
    isNil {
        private _bottleReceipt = [_medic, _patient, "ACM_Vial_Propofol", _mode, _vehicle] call ACME_fnc_transfusionTakeSelected;
        if (_bottleReceipt isNotEqualTo []) then {
            private _lineReceipt = [_medic, _patient, ["ACME_IVLine"]] call ACME_fnc_treatmentSupplyTake;
            if (_lineReceipt isEqualTo []) then {
                [_bottleReceipt] call ACME_fnc_treatmentSupplyRefund;
            } else {
                private _serial = (missionNamespace getVariable ["ACME_propofolBottleSerial", 0]) + 1;
                missionNamespace setVariable ["ACME_propofolBottleSerial", _serial];
                private _uid = format ["propofol-bottle:%1:%2:%3", clientOwner, netId _medic, _serial];
                private _duration = (missionNamespace getVariable ["ACME_infusion_defaultDurationSeconds", createHashMap]) getOrDefault ["Propofol", 1800];
                private _entry = [_uid, "ACM_Vial_Propofol", "ACME_PropofolIV_50", "Propofol", 500,
                    _duration, ACME_infusion_defaultDropSet, 0, 0, CBA_missionTime, 50,
                    0, _medic, objNull, [["Propofol", 500, 1]], _uid, 50, "propofol-bottle"];
                private _set = [_uid, "ACM_Vial_Propofol", "ACME_PropofolIV_50", "", "", "",
                    [_entry] call ACME_fnc_formatPreparedLabel, false, "propofol", 50, 0];
                private _sets = _medic getVariable ["ACME_preparedIVSets", []];
                private _prepared = _medic getVariable ["ACME_infusion_PreparedBags", []];
                _sets pushBack _set;
                _preparedIndex = _prepared pushBack _entry;
                _medic setVariable ["ACME_preparedIVSets", _sets, true];
                _medic setVariable ["ACME_infusion_PreparedBags", _prepared, true];
                [_medic] call ACME_fnc_preparedInventoryCommit;
                [_bottleReceipt, false] call ACME_fnc_treatmentSupplyRefund;
                [_lineReceipt, false] call ACME_fnc_treatmentSupplyRefund;
            };
        };
        true
    };
    [_medic, _holder, _token] call _release;
    if (_preparedIndex < 0) exitWith {
        ["The selected unopened propofol bottle or IV line is no longer available.", 2.5, _medic, 13] call ace_common_fnc_displayTextStructured;
    };
    missionNamespace setVariable ["ACME_infusion_SelectedPreparedIndex", _preparedIndex];
    uiNamespace setVariable ["ACME_preparedRowSig", "__force__"];
    ["Propofol bottle spiked. Select it in Prepared Infusions, then Give Infusion.", 3, _medic, 13] call ace_common_fnc_displayTextStructured;
    if (!isNull (findDisplay 86000)) then {
        [false] call ACM_circulation_fnc_TransfusionMenu_SwitchTargetInventory;
        call ACME_fnc_updateTransfusionControls;
    };
    }, [_medic, _patient, _mode, _vehicle, _holder, _token, _release], 1.6] call CBA_fnc_waitAndExecute;
};
if (_holder isEqualTo _medic) exitWith {[_medic, _patient, _mode, _vehicle, _holder, "", _release] call _begin;};

missionNamespace setVariable ["ACME_spikingActive", ["ACM_Vial_Propofol", diag_tickTime + 3]];
private _leaseReady = [_medic, _holder] call ACME_fnc_vialLeaseEnsure;
// Switching away from an old/expired holder releases it on the first ensure
// call. Start this holder's request now rather than waiting for a second click.
if (!_leaseReady && {!(((missionNamespace getVariable ["ACME_vialLeasePending", []]) param [0, objNull]) isEqualTo _holder)}) then {
    [_medic, _holder] call ACME_fnc_vialLeaseEnsure;
};
private _request = missionNamespace getVariable ["ACME_vialLeasePending", []];
private _accepted = missionNamespace getVariable ["ACME_vialLeaseAccepted", []];
private _token = if ((_accepted param [0, objNull]) isEqualTo _holder) then {_accepted param [1, ""]} else {_request param [1, ""]};
call ACME_fnc_updateTransfusionControls;
[{
    params ["_medic", "", "_mode", "_vehicle", "_holder", "_token"];
    private _accepted = missionNamespace getVariable ["ACME_vialLeaseAccepted", []];
    private _pending = missionNamespace getVariable ["ACME_vialLeasePending", []];
    isNull _medic || {!local _medic} || {!alive _medic}
        || {_mode == 2 && {objectParent _medic isNotEqualTo _vehicle}}
        || {(_accepted param [0, objNull]) isEqualTo _holder && {(_accepted param [1, ""]) == _token}}
        || {(_pending param [1, ""]) != _token}
}, {
    params ["_medic", "_patient", "_mode", "_vehicle", "_holder", "_token", "_release", "_begin"];
    private _accepted = missionNamespace getVariable ["ACME_vialLeaseAccepted", []];
    if (isNull _medic || {!local _medic} || {!alive _medic}
        || {_mode == 2 && {objectParent _medic isNotEqualTo _vehicle}}
        || {!((_accepted param [0, objNull]) isEqualTo _holder)}
        || {(_accepted param [1, ""]) != _token}
        || {(_accepted param [2, 0]) <= serverTime}) exitWith {
        missionNamespace setVariable ["ACME_spikingActive", []];
        [_medic, _holder, _token] call _release;
    };
    [_medic, _patient, _mode, _vehicle, _holder, _token, _release] call _begin;
}, [_medic, _patient, _mode, _vehicle, _holder, _token, _release, _begin], 3, {
    params ["_medic", "", "", "", "_holder", "_token", "_release"];
    missionNamespace setVariable ["ACME_spikingActive", []];
    [_medic, _holder, _token] call _release;
    ["Could not reserve the shared medication source. Select the bottle and try again.", 2.5, _medic, 13] call ace_common_fnc_displayTextStructured;
}] call CBA_fnc_waitUntilAndExecute;
