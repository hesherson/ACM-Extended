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

private _sourcePatient = GVAR(SyringeDraw_Target);
if (isNull _sourcePatient) then {_sourcePatient = uiNamespace getVariable ["ACME_SK_Patient",objNull];};
if (isNull _sourcePatient) exitWith {};
// A staged component is still owned by its selected vial holder. Changing the
// inventory before Save would otherwise debit the same drug from another kit.
if (GVAR(SyringeDraw_DrawnAmount) > 0.0005
    || {!((uiNamespace getVariable ["ACME_SK_CompoundComponents",[]]) isEqualTo [])}) exitWith {};

private _targetInventory = GVAR(SyringeDraw_InventorySelection);

// Shared patient/vehicle vial stock is protected by a short owner-authoritative lease. Release the previous
// holder before switching panes so another medic is never blocked by a source this client is no longer using.
if (!isNil "ACME_fnc_vialLeaseRelease") then {[ACE_player] call ACME_fnc_vialLeaseRelease;};
_targetInventory = _targetInventory + 1;

private _vehicle = objectParent ACE_player;

switch (_targetInventory) do {
    case 1: {
        if (ACE_player == _sourcePatient || {!(_sourcePatient in ([ACE_player,_sourcePatient] call ACME_fnc_treatmentSupplyOrder))}) then {
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
if (!isNull _display) then {["clear","",0,_display] call ACME_fnc_vialSession;};
private _ctrlInventorySelectText = _display displayCtrl IDC_SYRINGEDRAW_MEDLIST_SELECTION_TEXT;

private _text = [LLSTRING(Common_Self), LLSTRING(Common_Patient), LLSTRING(Common_Vehicle)] select GVAR(SyringeDraw_InventorySelection);
private _target = [ACE_player, _sourcePatient, _vehicle] select GVAR(SyringeDraw_InventorySelection);

_ctrlInventorySelectText ctrlSetText (format [LLSTRING(Common_InventoryTarget), _text]);

// Prime the lease immediately; fn_vialHolder will keep it renewed while this inventory remains selected.
if (!isNil "ACME_fnc_vialHolder") then {[ACE_player] call ACME_fnc_vialHolder;};
[] call FUNC(Syringe_UpdateMedicationList);
