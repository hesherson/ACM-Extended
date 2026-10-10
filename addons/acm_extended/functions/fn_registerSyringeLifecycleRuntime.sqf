// B191: prepared/tagged syringes are current-life state; fresh kits also invalidate opened-vial remainder.
if (hasInterface) then {
    player addEventHandler ["Killed", {
        params ["_unit"];
        [_unit, []] call ACME_fnc_narcStoreCommit;
        uiNamespace setVariable ["ACME_SK_SelectedSyringeId", ""];
        uiNamespace setVariable ["ACME_SK_CarouselIdx", -1];
        uiNamespace setVariable ["ACME_SK_SelDrawn", -1];
    }];

    player addEventHandler ["Respawn", {
        params ["_unit"];
        if (isNull _unit || {!local _unit}) exitWith {};
        [_unit] call ACM_core_fnc_equipmentKitChanged;
        [_unit] call ACME_fnc_resetPersonalMedicationKit;
    }];

    // B268: saved-load and clipboard-import buttons both use CBA's extended
    // setter. The owner-local CBA_loadoutSet completion hook in core is the
    // single kit-reset boundary for those operations. ACE's later button
    // notifications are UI events: loadoutImported also fires for parsed
    // arrays that never call the setter. Do not treat them as new equipment.
};
