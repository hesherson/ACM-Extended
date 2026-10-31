#include "..\script_component.hpp"
#include "..\TransfusionMenu_defines.hpp"
/*
 * Author: Blue
 * Handle stop transfusion button.
 *
 * Arguments:
 * None
 *
 * Return Value:
 * None
 *
 * Example:
 * [] call ACM_circulation_fnc_TransfusionMenu_ToggleIVFlow;
 *
 * Public: No
 */

private _medic = missionNamespace getVariable [QGVAR(TransfusionMenu_Medic), objNull];
if (isNull _medic) then {_medic = call ACME_fnc_controlledProvider;};
if (isNull _medic || {_medic isNotEqualTo (call ACME_fnc_controlledProvider)}) exitWith {};
private _patient = GVAR(TransfusionMenu_Target);
private _part = GVAR(TransfusionMenu_Selected_BodyPart);
private _site = GVAR(TransfusionMenu_Selected_AccessSite);
private _iv = GVAR(TransfusionMenu_SelectIV);
private _validAccess = [_patient, _part, _iv, _site] call ACME_fnc_transfusionAccessValid;
if (!_validAccess) exitWith {
    ["No established IV/IO is selected.",2,_medic,13] call ACEFUNC(common,displayTextStructured);
};
[_patient, "transfusionFlowToggle", [_patient, _part, _iv, _site, [_patient] call ACME_fnc_clinicalEpoch, _medic]] call ACME_fnc_ownerDispatch;
