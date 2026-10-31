// move the bag behind the selected infusions-list entry, by mapping the selection onto the native bag list of ACM
// and proxying into the move flow of ACM.
private _display = findDisplay 86000;
if (isNull _display) exitWith {false};

private _ctrlInf = _display displayCtrl 86129;
private _ownsPopover = (_display getVariable ["ACME_txActionMenu", ""]) == "infusion";
if (isNull _ctrlInf || {!ctrlShown _ctrlInf && {!_ownsPopover}}) exitWith {false};

private _row = lbCurSel _ctrlInf;
if (_row < 0) exitWith {
    ["Select an infusion first.", 1.5, ACE_player] call ace_common_fnc_displayTextStructured;
    false
};

private _ctrlNative = _display displayCtrl 86004;
if (isNull _ctrlNative) exitWith {false};

private _patient = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];
private _bodyPart = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""];
private _selection = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selection_IVBags", []];

// resolve the bag by its stable IV_Bags index rather than a display-row position: the two lists rebuild
// independently, so a positional lbvalue match can point at the wrong bag, or none, after a reorder, which
// silently no-opped the move. prefer the tracked selection, recorded by the infusions-list handler, then the
// selection entry of the row.
private _trueIndex = missionNamespace getVariable ["ACME_infusion_SelectedActiveInfusionTrueIndex", -1];
if (_trueIndex < 0) then {
    private _value = _ctrlInf lbValue _row;
    if (_value >= 0 && {_value < count _selection}) then { _trueIndex = (_selection select _value) param [8, -1]; };
};
if (_trueIndex < 0) exitWith {
    ["Could not resolve that infusion. Reopen the transfusion menu and try again.", 2.5, ACE_player] call ace_common_fnc_displayTextStructured;
    false
};

// Resolve the selection index independently of the filtered native Fluids list.
private _nativeRow = _selection findIf { (_x param [8, -1]) == _trueIndex };
if (_nativeRow < 0) exitWith {
    ["Could not resolve that infusion. Reopen the transfusion menu and try again.", 2.5, ACE_player] call ace_common_fnc_displayTextStructured;
    false
};

// resolve the infusion entry behind this bag before the move, so the entry can be re-linked once ACM relocates the
// bag and its bodypart and index go stale.
private _pending = [];
if (!isNull _patient && {_nativeRow < count _selection}) then {
    (_selection select _nativeRow) params ["_sType", "_sRemaining", "_sAccessType", "_sAccessSite", "_sIV", ["_sBloodType", -1], ["_sVolume", 0], ["_sFreshBloodID", -1], ["_sTrueIndex", -1]];
    {
        _x params ["_uid", "_eBodyPart", "_eBagIndex", "_eType", "_eAccessSite", "_eIV", "_eBloodType", "_eVolume", "_eFreshBloodID"];
        if (_eBodyPart == _bodyPart && {_eBagIndex == _sTrueIndex} && {_eType == _sType} && {_eAccessSite == _sAccessSite} && {_eIV == _sIV} && {_eBloodType == _sBloodType} && {_eVolume == _sVolume} && {_eFreshBloodID == _sFreshBloodID}) exitWith {
            _pending = [_patient, _uid, _sType, _sBloodType, _sVolume];
        };
    } forEach (_patient getVariable ["ACME_infusion_BagMedications", []]);
};

[_nativeRow] call ACM_circulation_fnc_TransfusionMenu_MoveBag;

// once the move flow of ACM settles, completed or canceled, re-link the entry to wherever the bag ended up. the
// condition stays false while the flow is armed.
if !(_pending isEqualTo []) then {
    [
        {
            !(missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Move_Active", false])
            && {!(missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Move_Active_Moving", false])}
        },
        {_this call ACME_fnc_relinkInfusionBag;},
        _pending,
        120,
        {}
    ] call CBA_fnc_waitUntilAndExecute;
};

call ACME_fnc_updateTransfusionControls;
true
