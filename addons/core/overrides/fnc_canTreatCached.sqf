// an override of ace_medical_treatment_fnc_cantreatcached.
// when a casualty is fully wrapped in an HPMK, only head-part treatments stay available. the pupil check, the
// response, the airway adjuncts, the BVM and BVM with o2, the non-rebreather and managing head injuries are all
// head-selection, plus "Unwrap HPMK" and the responsiveness check. everything on the body and limbs is gated off,
// so the menu grays or hides it. once unwrapped, the gate clears and everything returns.
// Menu visibility, immediate clicks and delayed treatment starts share this live policy. Living patients use
// native canTreat after the HPMK/procedure gates; corpses retain the same config and native access checks.
// The historical ACE function name is retained, but this implementation never caches.
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
    && {alive _target}
    && {!(_target getVariable ["ACE_isUnconscious", false])}
    && {!_hpmkIsLying}
) exitWith {false};

private _state = _target getVariable ["ACME_hpmk_state", ""];
private _part = toLower _bodyPart;
private _hpmkActions = ["CheckResponse", "ACME_UnwrapHPMK", "ACME_ExposeChestHPMK", "ACME_CoverChestHPMK"];

// B190: partially exposed HPMK is genuine chest access. CPR is a Body action even if the exposed overlay/menu
// leaves a stale selection context behind. Re-evaluate the exact ACE CPR treatment against the canonical Body
// selection. Fully wrapped HPMK never enters this branch and remains blocked below.
if (!isNull _target && {_state == "exposed"} && {(toLowerANSI _className) == "cpr"}) then {
    _bodyPart = "body";
    _part = "body";
};

// fully wrapped: only head-part care, plus the HPMK actions, stays available.
if (
    !isNull _target
    && {_state == "wrapped"}
    && {_part != "head"}
    && {!(_className in _hpmkActions)}
) exitWith { false };

// partially exposed: the head, the chest, meaning body, and the left arm are open, plus the HPMK actions. the right
// arm and both legs stay locked, because they are still wrapped. the ACE selection names are head, body, leftarm,
// rightarm, leftleg and rightleg.
if (
    !isNull _target
    && {_state == "exposed"}
    && {!(_part in ["head", "body", "leftarm"])}
    && {!(_className in _hpmkActions)}
) exitWith { false };

// A corpse is a valid treatment target. Keep provider/context checks here, then use ACE's actual config
// conditions and generic skill, item, location, self-treatment and underwater rules for both life states.
// Historical corpse exception tables duplicated those rules and could show actions their callbacks refused.
if (!isNull _target && {!alive _target}) then {
    private _sameVehicle = !isNull objectParent _caller && {objectParent _caller isEqualTo objectParent _target};
    private _exceptions = [["isNotInside", "isNotSwimming", "isNotInZeus"], ["isNotSwimming", "isNotInZeus"]] select _sameVehicle;
    private _zeus = _caller isEqualTo player && {!isNull findDisplay 312};
    private _allowed = !isNull _caller && {alive _caller}
        && {!(_caller getVariable ["ACE_isUnconscious", false])}
        && {[_caller, _target, _exceptions] call ace_common_fnc_canInteractWith}
        && {_zeus || {_sameVehicle || {([_caller, _target] call ACME_fnc_patientInteractionDistance) <= ace_medical_gui_maxDistance}}};
    if (!_allowed) then {_className = "";};
};
if (_className == "") exitWith {false};

[_caller, _target, toLowerANSI _bodyPart, _className] call ace_medical_treatment_fnc_canTreat
