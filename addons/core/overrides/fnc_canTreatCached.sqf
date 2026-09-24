// an override of ace_medical_treatment_fnc_cantreatcached.
// when a casualty is fully wrapped in an HPMK, only head-part treatments stay available. the pupil check, the
// response, the airway adjuncts, the BVM and BVM with o2, the non-rebreather and managing head injuries are all
// head-selection, plus "Unwrap HPMK" and the responsiveness check. everything on the body and limbs is gated off,
// so the menu grays or hides it. once unwrapped, the gate clears and everything returns.
// the implementation gates first, giving an instant false for the blocked case, and otherwise passes straight
// through to the real cantreat. so the behavior is byte-identical to stock whenever the patient is not wrapped.
// the caching is skipped, because the medical menu only re-collects on refresh rather than per frame.
params [["_caller", objNull], ["_target", objNull], ["_bodyPart", ""], ["_className", ""]];
if !([_caller, _className] call ACME_fnc_procedureActionAllowed) exitWith {false};

// An HPMK is a down-casualty treatment. Manual prone is still fully mobile, so Prep/Wrap are unavailable unless
// the casualty is medically unconscious or explicitly in ACM's lying state. The callbacks repeat this guard to
// close the progress-bar race where a casualty becomes mobile after the menu was built.
private _hpmkLyingState = if (isNull _target) then {false} else {_target getVariable ["ACM_core_Lying_State", false]};
private _hpmkIsLying = if (_hpmkLyingState isEqualType true) then {_hpmkLyingState} else {_hpmkLyingState > 0};
if (
    !isNull _target
    && {_className in ["ACME_PrepHPMK", "ACME_WrapHPMK"]}
    && {!(_target getVariable ["ACE_isUnconscious", false])}
    && {!_hpmkIsLying}
) exitWith {false};

private _state = _target getVariable ["ACME_hpmk_state", ""];
private _part = toLower _bodyPart;
private _hpmkActions = ["CheckResponse", "ACME_UnwrapHPMK", "ACME_ExposeChestHPMK", "ACME_CoverChestHPMK"];

// fully wrapped: only head-part care, plus the HPMK actions, stays available.
if (
    !isNull _target
    && {_state == "wrapped"}
    && {_part != "head"}
    && {!(_className in _hpmkActions)}
) exitWith { false };

// the dead-casualty override for the ACME thoracic training procedures.
// ACE's stock cantreat path hides most treatment actions once the unit is truly dead. these procedures are
// intentionally allowed to remain visible for training and aar continuity.
// A corpse can still have a patent IV/IO line and a bag can still be attached to that line for training,
// equipment accounting and post-event reconstruction. Do not force the medic to infer death merely because the
// transfusion menu disappeared. Physiology still does not resume on a dead unit.
if (
    !isNull _caller
    && {!isNull _target}
    && {!alive _target}
    && {_target isKindOf "CAManBase"}
    && {_className == "OpenTransfusionMenu"}
) exitWith {
    ([_target, _bodyPart, 0, -1] call ACM_circulation_fnc_hasIV)
        || {[_target, _bodyPart, 0] call ACM_circulation_fnc_hasIO}
};

private _deadEvidenceActions = [
    "CheckAirway", "CheckBreathing", "UseStethoscope", "ACME_InspectChest",
    "RemoveOPA", "RemoveNPA", "RemoveIGel", "ACME_Extubate", "ACME_OpenAirwayView"
];
if (!isNull _caller && {!isNull _target} && {!alive _target} && {_target isKindOf "CAManBase"} && {_className in _deadEvidenceActions}) exitWith {
    switch (_className) do {
        case "RemoveOPA": {(_target getVariable ["ACM_airway_AirwayItem_Oral", ""]) == "OPA"};
        case "RemoveNPA": {(_target getVariable ["ACM_airway_AirwayItem_Nasal", ""]) == "NPA"};
        case "RemoveIGel": {(_target getVariable ["ACM_airway_AirwayItem_Oral", ""]) == "SGA"};
        case "ACME_Extubate";
        case "ACME_OpenAirwayView": {(_target getVariable ["ACME_ETT_Inserted", false]) && {[_caller, _className] call ACME_fnc_procedureActionAllowed}};
        default {true};
    };
};

// Persisted equipment must remain manageable after death.  These actions do not restart physiology; they only
// inspect, maintain, expose or recover equipment that is already physically on the casualty.  Keeping the same
// state-driven buttons on a corpse also prevents the medical menu from becoming an unintended death detector.
private _deadEquipmentActions = [
    "ACME_VentOpenPatient", "ACME_DisconnectETVent", "ACME_SwapVentBattery",
    "ACME_RemoveNRB",
    "ACME_UnwrapHPMK", "ACME_ExposeChestHPMK", "ACME_CoverChestHPMK", "ACME_RemoveHPMK"
];
if (
    !isNull _caller
    && {!isNull _target}
    && {!alive _target}
    && {_target isKindOf "CAManBase"}
    && {_className in _deadEquipmentActions}
) exitWith {
    private _hpmkState = _target getVariable ["ACME_hpmk_state", ""];
    switch (_className) do {
        case "ACME_VentOpenPatient": {
            (_target getVariable ["ACME_vent_onPatient", false])
                && {!(_target getVariable ["ACME_vent_recovering", false])}
                && {(_target getVariable ["ACME_vent_circuit", false]) || {_target getVariable ["ACME_vent_configured", false]}}
        };
        case "ACME_DisconnectETVent": {
            (_target getVariable ["ACME_vent_onPatient", false])
                && {!(_target getVariable ["ACME_vent_recovering", false])}
        };
        case "ACME_SwapVentBattery": {
            [_target] call ACME_fnc_canSwapVentBattery
                && {([_caller, "ACME_VentBattery"] call ACME_fnc_itemCount) > 0}
        };
        case "ACME_RemoveNRB": {_target getVariable ["ACME_nrb_on", false]};
        case "ACME_UnwrapHPMK": {_caller isNotEqualTo _target && {_hpmkState in ["wrapped", "exposed"]}};
        case "ACME_ExposeChestHPMK": {_caller isNotEqualTo _target && {_hpmkState == "wrapped"}};
        case "ACME_CoverChestHPMK": {_caller isNotEqualTo _target && {_hpmkState == "exposed"}};
        case "ACME_RemoveHPMK": {_caller isNotEqualTo _target && {_hpmkState == "prepped"}};
        default {false};
    };
};

private _deadThoracicActions = [
    "ACME_ApplyChestSeal",
    "ACME_PerformNARSPEAR",
    "ACME_PerformThoracostomy",
    "ACME_AdjustThoracostomy",
    "ACME_InsertChestTube",
    "ACME_DrainFluid_ACCUVAC",
    "ACME_DrainFluid_SuctionBag",
    "ACME_ResealChestTube",
    "ACME_CloseIncision"
];
if (
    !isNull _caller
    && {!isNull _target}
    && {!alive _target}
    && {_target isKindOf "CAManBase"}
    && {(toLower _bodyPart) == "body"}
    && {_className in _deadThoracicActions}
) exitWith {
    private _has = {
        params ["_item"];
        (([_caller, _item] call ACME_fnc_itemCount) > 0) || {([_caller, _target, [_item]] call ace_medical_treatment_fnc_hasItem)}
    };
    switch (_className) do {
        case "ACME_ApplyChestSeal": { ["ACM_ChestSeal"] call _has };
        case "ACME_PerformNARSPEAR": { ["ACME_NARSPEAR"] call _has };
        case "ACME_PerformThoracostomy": { (_target getVariable ["ACM_breathing_Thoracostomy_State", 0]) < 1 && {([_caller, _target] call ACME_fnc_thoraKitItem) != ""} };
        case "ACME_AdjustThoracostomy": {[_caller, _target, true] call ACME_fnc_thoraCanOpen};
        case "ACME_InsertChestTube": { ((_target getVariable ["ACM_breathing_Thoracostomy_State", 0]) == 1) && {["ACM_ChestTubeKit"] call _has} };
        case "ACME_DrainFluid_ACCUVAC": { ((_target getVariable ["ACM_breathing_Thoracostomy_State", 0]) in [2,3]) && {["ACM_ACCUVAC"] call _has} };
        case "ACME_DrainFluid_SuctionBag": { ((_target getVariable ["ACM_breathing_Thoracostomy_State", 0]) in [2,3]) && {["ACM_SuctionBag"] call _has} };
        case "ACME_ResealChestTube": { ((_target getVariable ["ACM_breathing_Thoracostomy_State", 0]) == 3) };
        case "ACME_CloseIncision": { ((_target getVariable ["ACM_breathing_Thoracostomy_State", 0]) > 0) && {(["ACE_surgicalKit"] call _has) || {_target getVariable ["ACM_breathing_Thoracostomy_UsedKit", false]}} };
        default {false};
    };
};

// partially exposed: the head, the chest, meaning body, and the left arm are open, plus the HPMK actions. the right
// arm and both legs stay locked, because they are still wrapped. the ACE selection names are head, body, leftarm,
// rightarm, leftleg and rightleg.
if (
    !isNull _target
    && {_state == "exposed"}
    && {!(_part in ["head", "body", "leftarm"])}
    && {!(_className in _hpmkActions)}
) exitWith { false };

_this call ace_medical_treatment_fnc_canTreat
