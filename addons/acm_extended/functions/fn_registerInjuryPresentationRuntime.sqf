// Junctional auto-spawn must use ACE's supported woundReceived event. The old ACME path depended on overriding
// ace_medical_damage_fnc_woundsHandlerBase, which ACE declares final; Arma can reject that override entirely.
// ACE registers its own medical-damage woundReceived handler during preInit, while this ACME runtime registers in
// postInit, so by the time this handler runs the native wound map already contains the wound created by this hit.
if (isNil "ACME_junctionalWoundReceivedEH") then {
    ACME_junctionalWoundReceivedEH = ["ace_medical_woundReceived", {
        params ["_unit", ["_allDamages", []], ["_source", objNull], ["_ammo", ""]];
        [_unit, _allDamages, _ammo] call ACME_fnc_junctionalRollSpawn;
        // Remember significant torso injury for the next wake even if treated before consciousness returns.
        if (local _unit && {((_unit getVariable ["ace_medical_bodyPartDamage",[]]) param [1,0]) >= 0.5}
            && {!(_unit getVariable ["ACME_wakeHadTorsoDamage",false])}) then {
            _unit setVariable ["ACME_wakeHadTorsoDamage",true,true];
        };
    }] call CBA_fnc_addEventHandler;
};

// NA3: junctionalRollSpawn receives only new wound records from the native wounds handler.

// color-coded "Junctional Wound" row in the injury list. it hooks ACM's pre-render event and adds to the
// _woundEntries passed by reference, so it needs no override.
["ace_medical_gui_updateInjuryListWounds", {_this call ACME_fnc_junctionalInjuryEntry}] call CBA_fnc_addEventHandler;
// the chest tube output figure and the surgical flag, on the same pre-render event.
["ace_medical_gui_updateInjuryListWounds", {_this call ACME_fnc_thoraOutputEntry}] call CBA_fnc_addEventHandler;
["ace_medical_gui_updateInjuryListWounds", {_this call ACME_fnc_aajtInjuryEntry}] call CBA_fnc_addEventHandler;
["ace_medical_gui_updateInjuryListWounds", {_this call ACME_fnc_seizureInjuryEntry}] call CBA_fnc_addEventHandler;

// Airway adjunct seizure eligibility now lives in ACM_airway_fnc_insertAirwayItem.

// always-on, color-coded skin pallor row. it is an outward perfusion and temperature sign in every state.
ACME_skin_showRow = false;  // the skin description shows on the "Feel Skin" action only, not on the always-on overview row.
["ace_medical_gui_updateInjuryListWounds", {_this call ACME_fnc_skinInjuryEntry}] call CBA_fnc_addEventHandler;
// AAJT-s. drop the redundant "Tourniquet" injury-list entry on an AAJT-tourniqueted leg, because the AAJT-s
// row stands in for it.
// NA3: real tourniquets remain visible independently of the AAJT.
// ACM reports "Slight Cyanosis" on any part once its cyanosis row is pushed, because the last branch of its grading
// switch is a plain default. a casualty at 95 percent is not cyanotic, so the row is removed above a saturation
// floor. see fn_cyanosishideinjury for the threshold and why a tourniqueted limb is left alone.
["ace_medical_gui_updateInjuryListPart", {_this call ACME_fnc_cyanosisHideInjury}] call CBA_fnc_addEventHandler;
