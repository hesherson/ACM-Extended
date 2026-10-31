#include "\x\ACM\addons\circulation\script_component.hpp"
#include "\x\ACM\addons\circulation\TransfusionMenu_defines.hpp"
/*
 * Author: Blue
 * Handle move fluid bag button.
 *
 * Arguments:
 * None
 *
 * Return Value:
 * None
 *
 * Example:
 * [] call ACM_circulation_fnc_TransfusionMenu_MoveBag;
 *
 * Public: No
 */

private _medic = missionNamespace getVariable [QGVAR(TransfusionMenu_Medic), objNull];
if (isNull _medic) then {_medic = call ACME_fnc_controlledProvider;};
if (isNull _medic || {!local _medic} || {_medic isNotEqualTo (call ACME_fnc_controlledProvider)}) exitWith {};
private _display = uiNamespace getVariable [QGVAR(TransfusionMenu_DLG), displayNull];
private _ctrlBagPanel = _display displayCtrl IDC_TRANSFUSIONMENU_LEFTLISTPANEL;
// The Fluids list excludes drug infusions and its rows retain their selection
// index in lbValue. The infusion pane passes that index directly, without
// selecting an unrelated visible fluid row to proxy the native move action.
private _selectionIndex = _this param [0, -1];
if !(_selectionIndex isEqualType 0) then {_selectionIndex = -1;};
if (_selectionIndex < 0) then {
    private _row = lbCurSel _ctrlBagPanel;
    if (_row >= 0) then {_selectionIndex = _ctrlBagPanel lbValue _row;};
};

if ((_selectionIndex < 0 || {_selectionIndex >= count GVAR(TransfusionMenu_Selection_IVBags)})
    && !(GVAR(TransfusionMenu_Move_Active))) exitWith {};

private _ctrlMoveButton = _display displayCtrl IDC_TRANSFUSIONMENU_BUTTON_MOVEBAG;

if (GVAR(TransfusionMenu_Move_Active)) then {
    private _validDestination = [GVAR(TransfusionMenu_Target),GVAR(TransfusionMenu_Selected_BodyPart),GVAR(TransfusionMenu_SelectIV),GVAR(TransfusionMenu_Selected_AccessSite)] call ACME_fnc_transfusionAccessValid;
    if (!_validDestination) exitWith {
        ["Select an established IV or IO before placing the bag.",2.5,_medic,13] call ACEFUNC(common,displayTextStructured);
    };
    _ctrlMoveButton ctrlSetText LLSTRING(TransfusionMenu_MoveBag_Display);
    _ctrlMoveButton ctrlSetTooltip LLSTRING(TransfusionMenu_MoveBag_ToolTip);

    // Capture the exact move episode and destination before entering the progress
    // worker. A later menu selection may never retarget this callback.
    private _contents = +GVAR(TransfusionMenu_Move_IVBagContents);
    private _bagUid = _contents param [8, ""];
    private _destinationPart = GVAR(TransfusionMenu_Selected_BodyPart);
    private _destinationIV = GVAR(TransfusionMenu_SelectIV);
    private _destinationSite = GVAR(TransfusionMenu_Selected_AccessSite);
    private _epoch = missionNamespace getVariable ["ACME_moveEpoch", -1];
    private _token = missionNamespace getVariable ["ACME_moveToken", ""];
    private _fnc_completeMove = {
        params ["_medic", "_patient", "_bagUid", "_bodypart", "_iv", "_site", "_epoch", "_token", "_contents"];
        if (_token == "" || {_token != (missionNamespace getVariable ["ACME_moveToken", ""])}
            || {_bagUid != ((missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Move_IVBagContents", []]) param [8, ""])}) exitWith {false};
        [_patient, "bagMove", [_patient, _medic, _bagUid, "place", _bodypart, _iv, _site, _epoch, _token]] call ACME_fnc_ownerDispatch;
        GVAR(TransfusionMenu_Move_Active_Moving) = false;
        _contents params ["_type", "", "", "", "", "_bloodType", "_volume"];
        private _fluidBagString = [([_type, _volume, _bloodType, true] call FUNC(formatFluidBagName)),
            _contents param [10, []], _bloodType, _contents param [7, -1]] call FUNC(getFluidBagString);
        [_patient, "activity", LLSTRING(GUI_MovedTransfusing), [[_medic, false, true] call ACEFUNC(common,getName), _fluidBagString, ([_bodypart] call EFUNC(core,getBodyPartString))]] call ACEFUNC(medical_treatment,addToLog);
        true
    };

    GVAR(TransfusionMenu_Move_Active_Moving) = true;
    GVAR(TransfusionMenu_Move_Active) = false;
    _contents params ["_type", "", "", "", "", "_bloodType", "_volume"];
    private _itemClassNameString = getText (configFile >> "CfgWeapons" >> ([_type, _volume, _bloodType] call FUNC(formatFluidBagName)) >> "displayName");
    private _moveArgs = [_medic, GVAR(TransfusionMenu_Target), _fnc_completeMove, _bagUid, _destinationPart, _destinationIV, _destinationSite, _epoch, _token, _contents];
    [_moveArgs, {
        params ["_medic", "_patient", "_complete", "_bagUid", "_part", "_iv", "_site", "_epoch", "_token", "_contents"];
        if !([_medic, _patient, _bagUid, _part, _iv, _site, _epoch, _token, _contents] call _complete) exitWith {};
        closeDialog 0;
        [[_medic, _patient, _part, _iv, _site]] call ACME_fnc_reopenTransfusion;
    }, {
        params ["_medic", "_patient", "", "_bagUid", "_part", "_iv", "_site", "_epoch", "_token"];
        // Release the original owner token even if the provider has since armed
        // another move; a stale cancel cannot release the successor reservation.
        [_patient, "bagMove", [_patient, _medic, _bagUid, "cancel", "", true, -1, _epoch, _token]] call ACME_fnc_ownerDispatch;
        if (_token != (missionNamespace getVariable ["ACME_moveToken", ""])) exitWith {};
        GVAR(TransfusionMenu_Move_Active_Moving) = false;
        closeDialog 0;
        [[_medic, _patient, _part, _iv, _site]] call ACME_fnc_reopenTransfusion;
    }, (format [LLSTRING(TransfusionMenu_MoveBag_Progress), _itemClassNameString, ([_destinationPart] call EFUNC(core,getBodyPartString))]), 2.5] call EFUNC(core,progressBarAction);
} else {
    private _selected = GVAR(TransfusionMenu_Selection_IVBags) select _selectionIndex;
    private _expectedUid = _selected param [9, ""];
    private _IVBags = GVAR(TransfusionMenu_Target) getVariable [QGVAR(IV_Bags), createHashMap];
    private _IVBagsOnBodyPart = _IVBags getOrDefault [GVAR(TransfusionMenu_Selected_BodyPart), []];
    private _targetIndex = -1;
    if (_expectedUid != "") then {
        _targetIndex = _IVBagsOnBodyPart findIf {(_x param [8, ""]) == _expectedUid};
    } else {
        // Historical rows have no UID. Only their exact native signature may
        // identify the slot; a shifted index alone cannot choose another bag.
        private _oldIndex = _selected param [8, -1];
        if (_oldIndex >= 0 && {_oldIndex < count _IVBagsOnBodyPart}
            && {((_IVBagsOnBodyPart select _oldIndex) select [0,8]) isEqualTo (_selected select [0,8])}) then {_targetIndex = _oldIndex;};
    };
    if (_targetIndex < 0) exitWith {["That bag changed or moved. Select it again before moving.",2.5,_medic,13] call ACEFUNC(common,displayTextStructured);};
    private _resolved = _IVBagsOnBodyPart select _targetIndex;
    if ((_resolved param [3,-1]) != (_selected param [3,-1])
        || {(_resolved param [4,true]) isNotEqualTo (_selected param [4,true])}) exitWith {["That bag changed access. Select it again before moving.",2.5,_medic,13] call ACEFUNC(common,displayTextStructured);};
    GVAR(TransfusionMenu_Move_IVBagContents) = +_resolved;
    if ((GVAR(TransfusionMenu_Move_IVBagContents) param [8, ""]) == "") exitWith {["This bag is awaiting owner identity. Reopen the menu before moving.",2.5,_medic,13] call ACEFUNC(common,displayTextStructured);};
    _ctrlMoveButton ctrlSetText LLSTRING(TransfusionMenu_MoveBag_Place_Display);
    _ctrlMoveButton ctrlSetTooltip LLSTRING(TransfusionMenu_MoveBag_Place_Tooltip);

    GVAR(TransfusionMenu_Move_Active) = true;
    GVAR(TransfusionMenu_Move_Active_Moving) = false;
    GVAR(TransfusionMenu_Move_OriginIV) = GVAR(TransfusionMenu_SelectIV);
    GVAR(TransfusionMenu_Move_OriginBodyPart) = GVAR(TransfusionMenu_Selected_BodyPart);
    GVAR(TransfusionMenu_Move_OriginAccessSite) = GVAR(TransfusionMenu_Selected_AccessSite);

    GVAR(TransfusionMenu_Move_IVBagContents) params ["_type", "", "", "", "", "_bloodType", "_volume", "_id"];

    private _itemClassNameString = getText (configFile >> "CfgWeapons" >> ([_type, _volume, _bloodType] call FUNC(formatFluidBagName)) >> "displayName");
    [(format [LLSTRING(TransfusionMenu_MoveBag_Hint), _itemClassNameString]), 2, _medic] call ACEFUNC(common,displayTextStructured);

    private _bagUid = GVAR(TransfusionMenu_Move_IVBagContents) param [8, ""];
    ACME_moveEpoch = [GVAR(TransfusionMenu_Target)] call ACME_fnc_clinicalEpoch;
    private _moveSerial = (missionNamespace getVariable ["ACME_moveSerial",0]) + 1;
    missionNamespace setVariable ["ACME_moveSerial",_moveSerial];
    ACME_moveToken = format["move:%1:%2:%3",clientOwner,_moveSerial,floor(diag_tickTime*1000)];
    [GVAR(TransfusionMenu_Target), "bagMove", [GVAR(TransfusionMenu_Target), _medic, _bagUid, "reserve", GVAR(TransfusionMenu_Selected_BodyPart), GVAR(TransfusionMenu_SelectIV), GVAR(TransfusionMenu_Selected_AccessSite), ACME_moveEpoch, ACME_moveToken]] call ACME_fnc_ownerDispatch;
};
