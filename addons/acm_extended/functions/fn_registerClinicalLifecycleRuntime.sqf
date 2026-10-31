// A true FullHeal is a hard clinical reset. Death is deliberately different: the corpse keeps all physical
// injury/intervention evidence, while fn_deathFreeze stops only owner-local physiology workers.
["ace_medical_FullHeal", {_this call ACME_fnc_clearAllAilments}] call CBA_fnc_addEventHandler;
// AN IV PLACED BY ANY PATH GETS A HUB ON THE LIMB.
// ACM raises this event for every placement, so a second handler on the same name catches the auto heal
// facility path, a mission script, and anything else that calls setIV without knowing our mark list exists.
// without a hub there is nothing on the limb art to grab, so the line could not be seen and could not be pulled.
// fn_ivSeedHub defers its check by a beat and skips a site that already carries a hub, so the mini-game and the
// Zeus module, which write their own marks, never produce a duplicate.
["ACM_circulation_setIVLocal", {_this call ACME_fnc_ivSeedHub}] call CBA_fnc_addEventHandler;
// Death preserves medical evidence/interventions so the menu cannot disclose death through disappearing care.
addMissionEventHandler ["EntityKilled", { params ["_unit"]; if (local _unit) then { [_unit, "reset"] call ACME_fnc_aiProtectionSync; [_unit] call ACME_fnc_deathFreeze; [_unit] call ACME_fnc_recoveryDeathSlump; }; }];
// Respawn resets only the NEW life; the old corpse remains an evidentiary snapshot until the engine deletes it.

// y-saline owner-side setup. this fires through CBA_fnc_targetEvent at the casualty, so the ACME_SalineY retag
// and the ACME_YLines registration happen on the machine that owns IV_Bags and runs the bag drainer. that
// defeats the race between the medic and the owner.
["ACME_ySalineSetup", {_this call ACME_fnc_ySalineSetup}] call CBA_fnc_addEventHandler;

// B224: transferred wake clips are never restarted, and cannot leave the training AI keeper paused.
["CAManBase", "Local", {
    params ["_patient","_local"];
    if (!_local || {(_patient getVariable ["ACME_wakeVisualToken",[]]) isEqualTo []}) exitWith {};
    _patient setVariable ["ACME_wakeVisual",[],false];
    _patient setVariable ["ACME_wakeVisualToken",[],true];
    if (alive _patient && {!(_patient getVariable ["ACE_isUnconscious",false])}
        && {_patient getVariable ["ACM_core_Lying_State",false]}
        && {isNull objectParent _patient} && {isNull attachedTo _patient}
        && {((_patient getVariable ["ACME_patientAnimLock",[]]) param [4,-1]) <= serverTime}
        && {!(_patient getVariable ["ACME_headElevated",false])}
        && {!(_patient getVariable ["ACM_airway_RecoveryPosition_State",false])}
        && {((toLowerANSI animationState _patient) find "acme_wake") == 0}) then {
        _patient playMoveNow "ACM_LyingState";
    };
}, true, [], true] call CBA_fnc_addClassEventHandler;
