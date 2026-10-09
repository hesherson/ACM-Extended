#include "..\script_component.hpp"
/* B268: explicit completed replacement boundaries only. Do not hook every CBA player
 * loadout update or Arsenal close: looting, browsing and partial-mag changes
 * must not invalidate equipment or medication custody.
 * CBA extended-loadout events include the actual unit (including owner-local
 * AI on a server/HC); a raw ten-slot setter does not emit these CBA hooks.
 * ACE saved/imported kits use this same extended setter. Their later UI
 * events must not run this coordinator again or stand in for completion.
 */
if (isNil "ACME_equipmentKitRuntimeEH") then {
    ACME_equipmentKitRuntimeEH = [];
    {
        private _id = [_x, {
            params [["_unit", objNull, [objNull]]];
            if (isNull _unit || {!local _unit} || {is3DEN}) exitWith {};
            [_unit] call ACM_core_fnc_equipmentKitChanged;
            [_unit] call ACME_fnc_resetPersonalMedicationKit;
        }] call CBA_fnc_addEventHandler;
        ACME_equipmentKitRuntimeEH pushBack [_x, _id];
    } forEach ["CBA_loadoutSet", "ACME_equipmentKitReplaced"];
};
