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

private _display = uiNamespace getVariable [QGVAR(TransfusionMenu_DLG), displayNull];
private _medic = missionNamespace getVariable [QGVAR(TransfusionMenu_Medic), objNull];
if (isNull _medic) then {_medic = call ACME_fnc_controlledProvider;};
if (isNull _medic) exitWith {};
private _ctrlBagPanel = _display displayCtrl IDC_TRANSFUSIONMENU_LEFTLISTPANEL;
private _selectionIndex = lbCurSel _ctrlBagPanel;

if (_selectionIndex < 0 && !(GVAR(TransfusionMenu_Move_Active))) exitWith {};

private _ctrlMoveButton = _display displayCtrl IDC_TRANSFUSIONMENU_BUTTON_MOVEBAG;

if (GVAR(TransfusionMenu_Move_Active)) then {
    private _validDestination = [GVAR(TransfusionMenu_Target),GVAR(TransfusionMenu_Selected_BodyPart),GVAR(TransfusionMenu_SelectIV),GVAR(TransfusionMenu_Selected_AccessSite)] call ACME_fnc_transfusionAccessValid;
    if (!_validDestination) exitWith {
        ["Select an established IV or IO before placing the bag.",2.5,_medic,13] call ACEFUNC(common,displayTextStructured);
    };
    _ctrlMoveButton ctrlSetText LLSTRING(TransfusionMenu_MoveBag_Display);
    _ctrlMoveButton ctrlSetTooltip LLSTRING(TransfusionMenu_MoveBag_ToolTip);

    private _fnc_completeMove = {
        params ["_medic", "_patient"];

        private _bodypart = GVAR(TransfusionMenu_Selected_BodyPart);

        GVAR(TransfusionMenu_Move_IVBagContents) params ["_type", "_remainingVolume", "_accessType", "_accessSite", "_iv", "_bloodType", "_volume"];

        private _bagUid = GVAR(TransfusionMenu_Move_IVBagContents) param [8, ""];
        [_patient, "bagMove", [_patient, _medic, _bagUid, "place", _bodypart, GVAR(TransfusionMenu_SelectIV), GVAR(TransfusionMenu_Selected_AccessSite), missionNamespace getVariable ["ACME_moveEpoch", -1]]] call ACME_fnc_ownerDispatch;
        GVAR(TransfusionMenu_Move_Active_Moving) = false;

        private _fluidBagString = [([_type, _volume, _bloodType, true] call FUNC(formatFluidBagName))] call FUNC(getFluidBagString);
        [_patient, "activity", LLSTRING(GUI_MovedTransfusing), [[_medic, false, true] call ACEFUNC(common,getName), _fluidBagString, ([_bodypart] call EFUNC(core,getBodyPartString))]] call ACEFUNC(medical_treatment,addToLog);
    };

    GVAR(TransfusionMenu_Move_Active_Moving) = true;
    GVAR(TransfusionMenu_Move_Active) = false;

    GVAR(TransfusionMenu_Move_IVBagContents) params ["_type", "", "", "", "", "_bloodType", "_volume"];

    private _itemClassNameString = getText (configFile >> "CfgWeapons" >> ([_type, _volume, _bloodType] call FUNC(formatFluidBagName)) >> "displayName");

    [[_medic, GVAR(TransfusionMenu_Target), _fnc_completeMove], {
        params ["_medic", "_patient", "_fnc_completeMove"];

        [_medic, _patient] call _fnc_completeMove;

        closeDialog 0;

        [{
            params ["_medic", "_patient"];

            [_medic, _patient, GVAR(TransfusionMenu_Selected_BodyPart)] call FUNC(openTransfusionMenu);
        }, [_medic, _patient], 0.05] call CBA_fnc_waitAndExecute;
    }, {
        params ["_medic", "_patient"];

        closeDialog 0;

        [_medic, _patient, GVAR(TransfusionMenu_Selected_BodyPart)] call FUNC(openTransfusionMenu);
        GVAR(TransfusionMenu_Move_Active_Moving) = false;
    }, (format [LLSTRING(TransfusionMenu_MoveBag_Progress), _itemClassNameString, ([GVAR(TransfusionMenu_Selected_BodyPart)] call EFUNC(core,getBodyPartString))]), 2.5] call EFUNC(core,progressBarAction);
} else {
    _ctrlMoveButton ctrlSetText LLSTRING(TransfusionMenu_MoveBag_Place_Display);
    _ctrlMoveButton ctrlSetTooltip LLSTRING(TransfusionMenu_MoveBag_Place_Tooltip);

    GVAR(TransfusionMenu_Move_Active) = true;
    GVAR(TransfusionMenu_Move_Active_Moving) = false;
    GVAR(TransfusionMenu_Move_OriginIV) = GVAR(TransfusionMenu_SelectIV);
    GVAR(TransfusionMenu_Move_OriginBodyPart) = GVAR(TransfusionMenu_Selected_BodyPart);
    GVAR(TransfusionMenu_Move_OriginAccessSite) = GVAR(TransfusionMenu_Selected_AccessSite);

    private _targetIndex = (GVAR(TransfusionMenu_Selection_IVBags) select _selectionIndex) select 8;

    private _IVBags = GVAR(TransfusionMenu_Target) getVariable [QGVAR(IV_Bags), createHashMap];
    private _IVBagsOnBodyPart = _IVBags getOrDefault [GVAR(TransfusionMenu_Selected_BodyPart), []];

    GVAR(TransfusionMenu_Move_IVBagContents) = +(_IVBagsOnBodyPart select _targetIndex);

    GVAR(TransfusionMenu_Move_IVBagContents) params ["_type", "", "", "", "", "_bloodType", "_volume", "_id"];

    private _itemClassNameString = getText (configFile >> "CfgWeapons" >> ([_type, _volume, _bloodType] call FUNC(formatFluidBagName)) >> "displayName");
    [(format [LLSTRING(TransfusionMenu_MoveBag_Hint), _itemClassNameString]), 2, _medic] call ACEFUNC(common,displayTextStructured);

    private _bagUid = GVAR(TransfusionMenu_Move_IVBagContents) param [8, ""];
    ACME_moveEpoch = [GVAR(TransfusionMenu_Target)] call ACME_fnc_clinicalEpoch;
    [GVAR(TransfusionMenu_Target), "bagMove", [GVAR(TransfusionMenu_Target), _medic, _bagUid, "reserve", GVAR(TransfusionMenu_Selected_BodyPart), GVAR(TransfusionMenu_SelectIV), GVAR(TransfusionMenu_Selected_AccessSite), ACME_moveEpoch]] call ACME_fnc_ownerDispatch;
};
