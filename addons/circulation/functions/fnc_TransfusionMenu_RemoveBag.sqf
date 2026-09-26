#include "..\script_component.hpp"
#include "..\TransfusionMenu_defines.hpp"
/*
 * Author: Blue
 * Handle remove bag button.
 *
 * Arguments:
 * None
 *
 * Return Value:
 * None
 *
 * Example:
 * [] call ACM_circulation_fnc_TransfusionMenu_RemoveBag;
 *
 * Public: No
 */

private _display = uiNamespace getVariable [QGVAR(TransfusionMenu_DLG), displayNull];
private _ctrlBagPanel = _display displayCtrl IDC_TRANSFUSIONMENU_LEFTLISTPANEL;
private _selectionIndex = lbCurSel _ctrlBagPanel;
if (_selectionIndex < 0) exitWith {};

private _medic = missionNamespace getVariable [QGVAR(TransfusionMenu_Medic), objNull];
if (isNull _medic) then {_medic = call ACME_fnc_controlledProvider;};
if (isNull _medic) exitWith {};
private _patient = GVAR(TransfusionMenu_Target);
private _part = GVAR(TransfusionMenu_Selected_BodyPart);
private _targetIndex = (GVAR(TransfusionMenu_Selection_IVBags) select _selectionIndex) select 8;
private _map = _patient getVariable [QGVAR(IV_Bags), createHashMap];
private _arr = _map getOrDefault [_part, []];
if (_targetIndex < 0 || {_targetIndex >= count _arr}) exitWith {};
private _bag = +(_arr select _targetIndex);
_bag params ["_type", "_remainingVolume", "_accessType", "_accessSite", "_iv", "_bloodType", "_volume"];
private _bagUid = _bag param [8, "", [""]];
private _expectedSig = +(_bag select [0, 8]);

// Progress text is presentation-only. Inventory return happens only after the patient owner accepts the exact bag.
private _returnVolume = [_remainingVolume] call FUNC(getReturnVolume);
if (_type == "FBTK") then {
    private _tol = missionNamespace getVariable ["ACME_fbtk_fullToleranceMl", 1];
    if (!(_tol isEqualType 0) || {!finite _tol}) then {_tol = 1;};
    _tol = (_tol max 0) min 5;
    if (_remainingVolume >= ((_volume - _tol) max 0)) then {_returnVolume = _volume;};
};
private _itemClass = if (_type == "FBTK" && {_returnVolume <= 0}) then {format ["ACM_FieldBloodTransfusionKit_%1", _volume]} else {[_type, _returnVolume, _bloodType] call FUNC(formatFluidBagName)};
private _itemName = getText (configFile >> "CfgWeapons" >> _itemClass >> "displayName");
private _epoch = [_patient] call ACME_fnc_clinicalEpoch;
private _requestId = format ["txrm:%1:%2:%3", clientOwner, diag_frameNo, floor (diag_tickTime * 1000)];

[[_medic, _patient, _part, _bagUid, _targetIndex, _expectedSig, _epoch, _requestId], {
    params ["_medic", "_patient", "_part", "_bagUid", "_targetIndex", "_expectedSig", "_epoch", "_requestId"];
    uiNamespace setVariable ["ACME_txRemovePending", _requestId];
    [_patient, "transfusionRemoveBag", [_patient, _medic, _part, _bagUid, _targetIndex, _expectedSig, _epoch, _requestId]] call ACME_fnc_ownerDispatch;
    closeDialog 0;
}, {
    params ["_medic", "_patient", "_part"];
    closeDialog 0;
    [_medic, _patient, _part] call FUNC(openTransfusionMenu);
}, (format [LLSTRING(TransfusionMenu_RemoveBag_Progress), _itemName]), 2.5] call EFUNC(core,progressBarAction);
