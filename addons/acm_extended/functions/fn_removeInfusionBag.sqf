// remove, meaning discard, the bag behind the selected infusions-list entry. a spent infusion is trash: the bag is
// deleted outright and its saline carrier is not returned to inventory, unlike a blood-flush saline reserve,
// which is a different, un-medicated bag. this is why it does not proxy into ACM's native remove bag, because
// native returns the carrier item to the medic. the infusions list only ever contains medicated bags, so this
// always trashes.
// the bag is resolved by its stable trueindex, its position in the IV_Bags array of the patient, rather than by a
// display-row index: the infusions list and ACM's native list rebuild on independent schedules, so a positional
// lbvalue match could point at the wrong bag, or none, after any reorder. that fragility is what made removal
// silently no-op.
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

private _target   = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];
private _bodyPart = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""];
if (isNull _target || {_bodyPart isEqualTo ""}) exitWith {false};

private _selection = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selection_IVBags", []];

// the stable IV_Bags index for the selected infusion: the tracked selection first, recorded by the infusions-list
// selection handler in fn_updatetransfusioncontrols, then the current selection_ivbags entry of the selected
// row.
private _trueIndex = missionNamespace getVariable ["ACME_infusion_SelectedActiveInfusionTrueIndex", -1];
if (_trueIndex < 0) then {
    private _value = _ctrlInf lbValue _row;
    if (_value >= 0 && {_value < count _selection}) then { _trueIndex = (_selection select _value) param [8, -1]; };
};
if (_trueIndex < 0) exitWith {
    ["Could not resolve that infusion. Reopen the transfusion menu and try again.", 2.5, ACE_player] call ace_common_fnc_displayTextStructured;
    false
};

private _ivBags = _target getVariable ["ACM_circulation_IV_Bags", createHashMap];
private _arr = _ivBags getOrDefault [_bodyPart, []];
if (_trueIndex >= count _arr) exitWith {
    ["Could not resolve that infusion. Reopen the transfusion menu and try again.", 2.5, ACE_player] call ace_common_fnc_displayTextStructured;
    false
};

private _bag = +(_arr select _trueIndex);
_bag params [["_type", ""], ["_remVol", 0], ["_accessType", 0], ["_accessSite", -1], ["_iv", true]];

private _bagUid = _bag param [8, ""];
if (_bagUid == "") exitWith {
    [ACE_player, "Bag identity is not synchronized yet. Reopen the transfusion menu."] call ACME_fnc_clinicalNotice;
    false
};
[_target, "infusionRemove", [_target, ACE_player, _bagUid, [_target] call ACME_fnc_clinicalEpoch]] call ACME_fnc_ownerDispatch;

missionNamespace setVariable ["ACME_infusion_SelectedActiveInfusionTrueIndex", -1];
missionNamespace setVariable ["ACME_infusion_SelectedActiveInfusionSelectionIndex", -1];
missionNamespace setVariable ["ACME_pull_selTrueIndex", -1];

if (!isNil "ace_medical_treatment_fnc_addToLog") then {
    [_target, "activity", "%1 removed and discarded a spent infusion", [[ACE_player, false, true] call ace_common_fnc_getName]] call ace_medical_treatment_fnc_addToLog;
};


if (!isNil "ACM_circulation_fnc_TransfusionMenu_UpdateBagList") then { [false] call ACM_circulation_fnc_TransfusionMenu_UpdateBagList; };
uiNamespace setVariable ["ACME_coolerRowSig", "__force__"];
call ACME_fnc_updateTransfusionControls;
true
