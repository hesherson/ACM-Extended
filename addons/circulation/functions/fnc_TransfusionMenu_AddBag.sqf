#include "..\script_component.hpp"
#include "..\TransfusionMenu_defines.hpp"
/*
 * Author: Blue
 * Handle add bag button.
 *
 * Arguments:
 * None
 *
 * Return Value:
 * None
 *
 * Example:
 * [] call ACM_circulation_fnc_TransfusionMenu_AddBag;
 *
 * Public: No
 */

private _display = uiNamespace getVariable [QGVAR(TransfusionMenu_DLG), displayNull];

private _ctrlInventoryPanel = _display displayCtrl IDC_TRANSFUSIONMENU_RIGHTLISTPANEL;

private _targetIndex = lbCurSel _ctrlInventoryPanel;

if (_targetIndex < 0) exitWith {};

((_ctrlInventoryPanel lbData _targetIndex) splitString "|") params ["_itemClassname", "_actionClassname"];

private _medic = ACE_player;
private _patient = GVAR(TransfusionMenu_Target);
// ACME Y-refill claims are optional. Ordinary Add Bag calls carry an empty context and remain native behavior.
private _yRefill = +(uiNamespace getVariable ["ACME_yRefillActive", []]);

// FBTK is a donor-collection circuit, not an infusion product. The circulation model deliberately
// refuses to draw donor blood through IO. Reject it before inventory consumption so the kit can never
// be hung on a line that will sit at 0 mL forever and look broken to the provider.
private _isFBTK = (_itemClassname in FBTK_ARRAY) || {_actionClassname in FBTK_ARRAY_DATA};
if (_isFBTK && {!GVAR(TransfusionMenu_SelectIV)}) exitWith {
    ["FBTK blood collection requires IV access. It cannot collect through IO.", 3, ACE_player, 13] call ACEFUNC(common,displayTextStructured);
};

private _validAccess = [
    _patient,
    GVAR(TransfusionMenu_Selected_BodyPart),
    GVAR(TransfusionMenu_SelectIV),
    GVAR(TransfusionMenu_Selected_AccessSite)
] call ACME_fnc_transfusionAccessValid;
if (!_validAccess) exitWith {
    ["Establish and select an IV or IO before hanging fluid.",2.5,ACE_player,13] call ACEFUNC(common,displayTextStructured);
};

private _vehicle = objectParent _medic;

private _target = [_medic, _patient, _vehicle] select GVAR(TransfusionMenu_Selected_Inventory);

// A fresh whole-blood item is only safe to consume once its donor metadata is present locally. JIP/MP registry
// synchronization can trail the physical inventory item briefly. Never remove the bag first and discover that its
// ABO/time metadata is missing afterward. Ask the server to resync and leave the item untouched.
private _itemCfg = configFile >> "CfgWeapons" >> _itemClassname;
private _freshMetadataReady = true;
if ((getNumber (_itemCfg >> "uniqueBag")) > 0) then {
    private _parts = _itemClassname splitString "_";
    private _freshID = parseNumber (_parts param [3, "-1"]);
    private _freshEntry = [_freshID] call FUNC(getFreshBloodEntry);
    _freshMetadataReady = _freshEntry isEqualType [] && {count _freshEntry >= 3};
};
if (!_freshMetadataReady) exitWith {
    [QGVAR(requestFreshBloodRegistry), [ACE_player]] call CBA_fnc_serverEvent;
    ["Donor blood bag data is still synchronizing. Reopen the transfusion menu in a moment.", 2.5] call ACEFUNC(common,displayTextStructured);
};

if (GVAR(TransfusionMenu_Selected_Inventory) == 2) then {
    _vehicle addItemCargoGlobal [_itemClassname, -1];
} else {
    [_target, _itemClassname] call ACME_fnc_itemTake;
};

private _itemClassNameString = getText (configFile >> "CfgWeapons" >> _itemClassname >> "displayName");

[[_medic, _patient, _target, _itemClassname, _actionClassname, _vehicle, _yRefill], {
    params ["_medic", "_patient", "_target", "_itemClassname", "_actionClassname", "_vehicle", "_yRefill"];

    private _bodyPart = GVAR(TransfusionMenu_Selected_BodyPart);
    private _iv = GVAR(TransfusionMenu_SelectIV);
    private _site = GVAR(TransfusionMenu_Selected_AccessSite);
    private _yRequest = "";
    if (_yRefill isEqualType [] && {count _yRefill >= 11} && {(_yRefill select 0) isEqualTo _patient}
        && {(_yRefill select 9) == _itemClassname} && {(_yRefill select 10) == _actionClassname}) then {
        _yRefill params ["", "_yRequest", "_yMode", "_yPart", "_yIV", "_ySite", "_yEpoch", "_yCooler", "_yWarmer"];
        _bodyPart = _yPart;
        _iv = _yIV;
        _site = _ySite;
    };

    [_medic, _patient, _bodyPart, _actionClassname, objNull, _itemClassname, _iv, _site] call ACEFUNC(medical_treatment,ivBag);
    if (_yRequest != "") then {
        [_patient,"yRefill",[_patient,_medic,"finalize",_yRequest,_yMode,_bodyPart,_iv,_site,_yEpoch,_yCooler,_yWarmer]] call ACME_fnc_ownerDispatch;
        private _active = uiNamespace getVariable ["ACME_yRefillActive",[]];
        if (_active isEqualType [] && {(_active param [1,""]) == _yRequest}) then {uiNamespace setVariable ["ACME_yRefillActive",[]];};
    };
    closeDialog 0;

    [{
        params ["_medic", "_patient", "_bodyPart"];
        [_medic, _patient, _bodyPart] call FUNC(openTransfusionMenu);
    }, [_medic, _patient, _bodyPart], 0.05] call CBA_fnc_waitAndExecute;
}, {
    params ["_medic", "_patient", "_target", "_itemClassname", "", "_vehicle", "_yRefill"];

    if (GVAR(TransfusionMenu_Selected_Inventory) == 2) then {
        _vehicle addItemCargoGlobal [_itemClassname, 1];
    } else {
        [_target, _itemClassname] call ACEFUNC(common,addToInventory);
    };
    private _bodyPart = GVAR(TransfusionMenu_Selected_BodyPart);
    if (_yRefill isEqualType [] && {count _yRefill >= 9} && {(_yRefill select 0) isEqualTo _patient}) then {
        _yRefill params ["", "_yRequest", "_yMode", "_yPart", "_yIV", "_ySite", "_yEpoch", "_yCooler", "_yWarmer"];
        _bodyPart = _yPart;
        [_patient,"yRefill",[_patient,_medic,"cancel",_yRequest,_yMode,_yPart,_yIV,_ySite,_yEpoch,_yCooler,_yWarmer]] call ACME_fnc_ownerDispatch;
        private _active = uiNamespace getVariable ["ACME_yRefillActive",[]];
        if (_active isEqualType [] && {(_active param [1,""]) == _yRequest}) then {uiNamespace setVariable ["ACME_yRefillActive",[]];};
    };
    closeDialog 0;

    [_medic, _patient, _bodyPart] call FUNC(openTransfusionMenu);
}, (format [LLSTRING(TransfusionMenu_AddBag_Progress), _itemClassNameString]), 5] call EFUNC(core,progressBarAction);
