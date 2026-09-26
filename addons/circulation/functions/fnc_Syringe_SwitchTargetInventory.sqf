#include "..\script_component.hpp"
#include "..\SyringeDraw_defines.hpp"
/*
 * Author: Blue
 * Handle switching inventory target.
 *
 * Arguments:
 * None
 *
 * Return Value:
 * None
 *
 * Example:
 * [] call ACM_circulation_fnc_Syringe_SwitchTargetInventory;
 *
 * Public: No
 */

if (isNull GVAR(SyringeDraw_Target)) exitWith {};

private _medic = missionNamespace getVariable [QGVAR(SyringeDraw_Medic), objNull];
if (isNull _medic) then {_medic = call ACME_fnc_controlledProvider;};
if (isNull _medic) exitWith {};

private _targetInventory = GVAR(SyringeDraw_InventorySelection);

// Shared patient/vehicle vial stock is protected by a short owner-authoritative lease. Release the previous
// holder before switching panes so another medic is never blocked by a source this client is no longer using.
if (!isNil "ACME_fnc_vialLeaseRelease") then {[_medic] call ACME_fnc_vialLeaseRelease;};
_targetInventory = _targetInventory + 1;

private _vehicle = objectParent _medic;

switch (_targetInventory) do {
    case 1: {
        if (_medic == GVAR(SyringeDraw_Target)) then {
            if !(isNull _vehicle) then {
                _targetInventory = 2;
            } else {
                _targetInventory = 0;
            };
        };
    };
    case 2: {
        if (isNull _vehicle) then {
            _targetInventory = 0;
        };
    };
    default {
        if (_targetInventory > 2) then {
            _targetInventory = 0;
        };
    };
};

GVAR(SyringeDraw_InventorySelection) = _targetInventory;

private _display = uiNamespace getVariable [QGVAR(SyringeDraw_DLG), displayNull];
private _ctrlInventorySelectText = _display displayCtrl IDC_SYRINGEDRAW_MEDLIST_SELECTION_TEXT;

private _text = [LLSTRING(Common_Self), LLSTRING(Common_Patient), LLSTRING(Common_Vehicle)] select GVAR(SyringeDraw_InventorySelection);
private _target = [_medic, GVAR(SyringeDraw_Target), _vehicle] select GVAR(SyringeDraw_InventorySelection);

_ctrlInventorySelectText ctrlSetText (format [LLSTRING(Common_InventoryTarget), _text]);

// Prime the lease immediately; fn_vialHolder will keep it renewed while this inventory remains selected.
if (!isNil "ACME_fnc_vialHolder") then {[_medic] call ACME_fnc_vialHolder;};
[] call FUNC(Syringe_UpdateMedicationList);
